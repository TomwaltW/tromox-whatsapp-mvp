"""CLI: python -m eval.run --input <csv> --prompt <md> --model <spec> --out <report.md>"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .clients import DEFAULT_ERROR_RATE, DEFAULT_SEED, FatalClientError, ModelClient, TransientClientError, build_client
from .data import DataError, Sample, load_dataset
from .metrics import (
    Outcome,
    check_thresholds,
    cost_per_100,
    default_thresholds_path,
    evaluate,
    load_thresholds,
    make_outcome,
    price_from_env,
)
from .parse import ParseResult, parse_extraction
from .prompt import PromptSpec, build_user_message, load_prompt
from .report import RunInfo, pct, render_report

EXIT_OK, EXIT_THRESHOLD, EXIT_DATA, EXIT_CLIENT = 0, 1, 2, 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m eval.run", description=__doc__)
    parser.add_argument("--input", required=True, help="labelled CSV (columns = tromox_lead.LABEL_COLUMNS)")
    parser.add_argument("--prompt", required=True, help="prompt file, e.g. prompts/classify-v1.md")
    parser.add_argument("--model", required=True, help="mock | openai:<model> | anthropic:<model>")
    parser.add_argument("--out", required=True, help="Markdown report to write")
    parser.add_argument("--thresholds", default=None, help="default: ../06-acceptance/thresholds.json")
    parser.add_argument("--fail-under", action="store_true", help="exit 1 when any threshold is not met")
    parser.add_argument("--limit", type=int, default=None, help="only evaluate the first N samples")
    parser.add_argument("--include-examples", action="store_true",
                        help="also evaluate data_origin=example rows (trial sample kit); skipped by default")
    parser.add_argument("--predictions-out", default=None,
                        help="optional JSONL with raw model outputs (may contain personal data - keep it out of git)")
    parser.add_argument("--mock-seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--mock-error-rate", type=float, default=DEFAULT_ERROR_RATE)
    parser.add_argument("--max-tokens", type=int, default=None,
                        help="anthropic: default 16000; openai: not sent unless given")
    parser.add_argument("--temperature", type=float, default=None,
                        help="openai-compatible only; never sent to Claude models, which reject sampling parameters")
    parser.add_argument("--json-mode", action="store_true", help="openai-compatible only: response_format=json_object")
    parser.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default=None,
                        help="anthropic only: output_config.effort (not accepted by every model)")
    parser.add_argument("--anthropic-fallbacks", choices=["auto", "on", "off"], default="auto",
                        help="server-side refusal fallbacks; auto = on for the models Anthropic recommends it for")
    return parser


def run_eval(samples: list[Sample], prompt: PromptSpec, client: ModelClient, *, progress: bool = True) -> list[Outcome]:
    outcomes: list[Outcome] = []
    for index, sample in enumerate(samples, start=1):
        user_message = build_user_message(sample.conversation_text)
        try:
            completion = client.complete(prompt.text, user_message, sample=sample)
        except TransientClientError as exc:
            outcomes.append(make_outcome(sample, None, ParseResult(None, error="request failed"), client_error=str(exc)))
        else:
            parse = ParseResult(None, error=completion.error) if completion.stop_reason == "refusal" \
                else parse_extraction(completion.text)
            outcomes.append(make_outcome(sample, completion, parse))
        if progress and (index % 10 == 0 or index == len(samples)):
            print(f"  {index}/{len(samples)}", file=sys.stderr)
    return outcomes


def write_predictions(path: Path, outcomes: list[Outcome]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for o in outcomes:
            fh.write(json.dumps({
                "sample_id": o.sample.sample_id,
                "raw_text": o.completion.text if o.completion else None,
                "model": o.completion.model if o.completion else None,
                "stop_reason": o.completion.stop_reason if o.completion else None,
                "parse_error": o.parse.error,
                "client_error": o.client_error,
                "prediction_after_routing": o.prediction.model_dump(mode="json"),
            }, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        dataset = load_dataset(args.input, include_examples=args.include_examples)
    except (DataError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_DATA
    try:
        prompt = load_prompt(args.prompt)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_DATA
    samples = list(dataset.samples[: args.limit] if args.limit else dataset.samples)

    try:
        client = build_client(
            args.model, seed=args.mock_seed, error_rate=args.mock_error_rate, max_tokens=args.max_tokens,
            temperature=args.temperature, json_mode=args.json_mode or None, effort=args.effort,
            fallbacks=args.anthropic_fallbacks,
        )
        print(f"evaluating {len(samples)} samples with {client.name} / {prompt.version}", file=sys.stderr)
        outcomes = run_eval(samples, prompt, client)
    except (FatalClientError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_CLIENT

    result = evaluate(outcomes)
    thresholds_path = Path(args.thresholds) if args.thresholds else default_thresholds_path()
    checks = check_thresholds(result, load_thresholds(thresholds_path))
    prices = price_from_env()
    info = RunInfo(model=client.name, input_path=args.input,
                   thresholds_path=args.thresholds or "06-acceptance/thresholds.json",
                   cost_per_100_usd=cost_per_100(result, prices), prices=prices)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_report(dataset.model_copy(update={"samples": tuple(samples)}), prompt, result, checks, info),
                        encoding="utf-8")
    if args.predictions_out:
        write_predictions(Path(args.predictions_out), outcomes)

    failed = [c for c in checks if not c.passed]
    print(f"B2B recall {pct(result.b2b_recall)} | precision {pct(result.b2b_precision)} | "
          f"country {pct(result.country_accuracy)} | product {pct(result.product_recognition)} | "
          f"escalation {pct(result.escalation_rate)} | JSON {pct(result.parse_success)}")
    print(f"report written to {out_path}")
    if failed:
        print(f"RESULT: FAIL ({len(failed)} of {len(checks)} checks not met: {', '.join(c.key for c in failed)})")
    else:
        print(f"RESULT: PASS ({len(checks)} checks)")
    return EXIT_THRESHOLD if (failed and args.fail_under) else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
