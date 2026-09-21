"""Metrics for the lead classification eval. Primary metric: B2B recall.

Every prediction goes through tromox_lead.apply_routing_rules first - the same function
the webhook service runs - so what is measured here is the production behaviour.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

from tromox_lead import AIExtraction, EscalationReason, Segment, apply_routing_rules, effective_country

from .clients.base import Completion, Usage
from .data import Sample
from .parse import ParseResult

SEGMENTS: tuple[Segment, ...] = (Segment.B2B, Segment.B2C, Segment.UNKNOWN)
# Anthropic prompt-caching multipliers relative to the base input price (writes ~1.25x, reads ~0.1x).
CACHE_WRITE_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER = 0.10


def fallback_prediction() -> AIExtraction:
    """What production does when the model output is unusable: unknown + hand over to a human."""
    return AIExtraction(segment=Segment.UNKNOWN, ai_confidence=0.0, escalation_flag=True,
                        escalation_reason=EscalationReason.LOW_CONFIDENCE)


@dataclass(frozen=True)
class Outcome:
    sample: Sample
    completion: Completion | None
    parse: ParseResult
    prediction: AIExtraction
    client_error: str | None = None

    @property
    def predicted_country(self) -> str | None:
        return effective_country(self.prediction.country_stated, self.sample.country_by_phone)


def make_outcome(sample: Sample, completion: Completion | None, parse: ParseResult,
                 client_error: str | None = None) -> Outcome:
    base = parse.extraction if parse.extraction is not None else fallback_prediction()
    prediction = apply_routing_rules(base, sample.country_by_phone)
    return Outcome(sample, completion, parse, prediction, client_error)


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


@dataclass(frozen=True)
class LanguageRow:
    language: str
    n: int
    n_b2b: int
    b2b_recall: float | None
    segment_accuracy: float | None
    escalation_rate: float | None


@dataclass(frozen=True)
class ThresholdCheck:
    key: str
    label: str
    value: float | None
    threshold: float
    comparator: str  # ">=" or "<="
    passed: bool
    note: str = ""


@dataclass
class EvalResult:
    n_total: int = 0
    n_real: int = 0
    n_real_b2b: int = 0
    n_gold_b2b: int = 0
    parse_ok: int = 0
    client_failures: int = 0
    refusals: int = 0
    served_by_fallback: int = 0
    missing_key_outputs: int = 0
    confusion: dict[tuple[str, str], int] = field(default_factory=dict)
    b2b_tp: int = 0
    b2b_fp: int = 0
    b2b_fn: int = 0
    b2b_misses: list[Outcome] = field(default_factory=list)
    b2b_false_positives: list[Outcome] = field(default_factory=list)
    parse_failures: list[Outcome] = field(default_factory=list)
    country_eligible: int = 0
    country_correct: int = 0
    country_errors: list[Outcome] = field(default_factory=list)
    product_eligible: int = 0
    product_exact: int = 0
    product_tp: int = 0
    product_fp: int = 0
    product_fn: int = 0
    escalation_pred: int = 0
    escalation_gold: int = 0
    escalation_tp: int = 0
    escalation_reason_match: int = 0
    escalation_by_reason: dict[str, int] = field(default_factory=dict)
    b2b_type_eligible: int = 0
    b2b_type_correct: int = 0
    b2c_intent_eligible: int = 0
    b2c_intent_correct: int = 0
    language_correct: int = 0
    per_language: list[LanguageRow] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    latencies: list[float] = field(default_factory=list)

    # --- headline numbers -------------------------------------------------------------
    @property
    def b2b_recall(self) -> float | None:
        return ratio(self.b2b_tp, self.b2b_tp + self.b2b_fn)

    @property
    def b2b_precision(self) -> float | None:
        return ratio(self.b2b_tp, self.b2b_tp + self.b2b_fp)

    @property
    def b2b_f1(self) -> float | None:
        p, r = self.b2b_precision, self.b2b_recall
        if p is None or r is None or p + r == 0:
            return None
        return 2 * p * r / (p + r)

    @property
    def parse_success(self) -> float | None:
        return ratio(self.parse_ok, self.n_total)

    @property
    def country_accuracy(self) -> float | None:
        return ratio(self.country_correct, self.country_eligible)

    @property
    def product_recognition(self) -> float | None:
        return ratio(self.product_exact, self.product_eligible)

    @property
    def escalation_rate(self) -> float | None:
        return ratio(self.escalation_pred, self.n_total)

    @property
    def escalation_recall(self) -> float | None:
        return ratio(self.escalation_tp, self.escalation_gold)

    @property
    def escalation_precision(self) -> float | None:
        return ratio(self.escalation_tp, self.escalation_pred)

    @property
    def latency_p50(self) -> float | None:
        return median(self.latencies) if self.latencies else None

    @property
    def latency_p95(self) -> float | None:
        if not self.latencies:
            return None
        ordered = sorted(self.latencies)
        return ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]


def evaluate(outcomes: list[Outcome]) -> EvalResult:
    result = EvalResult(n_total=len(outcomes))
    for gold in SEGMENTS:
        for pred in SEGMENTS:
            result.confusion[(gold.value, pred.value)] = 0
    by_language: dict[str, list[Outcome]] = {}
    totals = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}

    for outcome in outcomes:
        sample, pred = outcome.sample, outcome.prediction
        by_language.setdefault(sample.language, []).append(outcome)
        if sample.data_origin == "real":
            result.n_real += 1
            if sample.segment is Segment.B2B:
                result.n_real_b2b += 1

        if outcome.parse.ok:
            result.parse_ok += 1
            if outcome.parse.missing_keys:
                result.missing_key_outputs += 1
        else:
            result.parse_failures.append(outcome)
        if outcome.client_error:
            result.client_failures += 1
        completion = outcome.completion
        if completion is not None:
            if completion.stop_reason == "refusal":
                result.refusals += 1
            if completion.served_by_fallback:
                result.served_by_fallback += 1
            totals["input"] += completion.usage.input_tokens
            totals["output"] += completion.usage.output_tokens
            totals["cache_write"] += completion.usage.cache_write_tokens
            totals["cache_read"] += completion.usage.cache_read_tokens
            result.latencies.append(completion.latency_s)

        # segment
        result.confusion[(sample.segment.value, pred.segment.value)] += 1
        gold_b2b, pred_b2b = sample.segment is Segment.B2B, pred.segment is Segment.B2B
        if gold_b2b:
            result.n_gold_b2b += 1
        if gold_b2b and pred_b2b:
            result.b2b_tp += 1
            result.b2b_type_eligible += 1
            result.b2b_type_correct += int(pred.b2b_type == sample.b2b_type)
        elif gold_b2b:
            result.b2b_fn += 1
            result.b2b_misses.append(outcome)
        elif pred_b2b:
            result.b2b_fp += 1
            result.b2b_false_positives.append(outcome)
        if sample.segment is Segment.B2C and pred.segment is Segment.B2C:
            result.b2c_intent_eligible += 1
            result.b2c_intent_correct += int(pred.b2c_intent == sample.b2c_intent)

        # country: only rows where the phone prefix rule can apply
        if sample.country_by_phone and sample.country_gold:
            result.country_eligible += 1
            if outcome.predicted_country == sample.country_gold:
                result.country_correct += 1
            else:
                result.country_errors.append(outcome)

        # products: exact set match on rows that have gold products
        gold_products, pred_products = set(sample.product_interest), set(pred.product_interest)
        if gold_products:
            result.product_eligible += 1
            result.product_exact += int(gold_products == pred_products)
        result.product_tp += len(gold_products & pred_products)
        result.product_fp += len(pred_products - gold_products)
        result.product_fn += len(gold_products - pred_products)

        # escalation (after routing rules)
        if pred.escalation_flag:
            result.escalation_pred += 1
            reason = pred.escalation_reason.value if pred.escalation_reason else "unspecified"
            result.escalation_by_reason[reason] = result.escalation_by_reason.get(reason, 0) + 1
        if sample.escalation_flag:
            result.escalation_gold += 1
            if pred.escalation_flag:
                result.escalation_tp += 1
                result.escalation_reason_match += int(pred.escalation_reason == sample.escalation_reason)

        result.language_correct += int(pred.language == sample.language)

    for language in sorted(by_language, key=lambda k: (-len(by_language[k]), k)):
        rows = by_language[language]
        b2b_rows = [o for o in rows if o.sample.segment is Segment.B2B]
        result.per_language.append(LanguageRow(
            language=language,
            n=len(rows),
            n_b2b=len(b2b_rows),
            b2b_recall=ratio(sum(o.prediction.segment is Segment.B2B for o in b2b_rows), len(b2b_rows)),
            segment_accuracy=ratio(sum(o.prediction.segment is o.sample.segment for o in rows), len(rows)),
            escalation_rate=ratio(sum(o.prediction.escalation_flag for o in rows), len(rows)),
        ))
    result.usage = Usage(totals["input"], totals["output"], totals["cache_write"], totals["cache_read"])
    return result


# --- cost ---------------------------------------------------------------------------------
def price_from_env() -> tuple[float, float] | None:
    """(input, output) USD per 1M tokens from EVAL_PRICE_*_PER_1M, or None when unset."""
    try:
        return float(os.environ["EVAL_PRICE_INPUT_PER_1M"]), float(os.environ["EVAL_PRICE_OUTPUT_PER_1M"])
    except (KeyError, ValueError):
        return None


def cost_per_100(result: EvalResult, prices: tuple[float, float] | None) -> float | None:
    if prices is None or result.n_total == 0:
        return None
    price_in, price_out = prices
    usage = result.usage
    billable_input = (usage.input_tokens + usage.cache_write_tokens * CACHE_WRITE_MULTIPLIER
                      + usage.cache_read_tokens * CACHE_READ_MULTIPLIER)
    total = billable_input / 1_000_000 * price_in + usage.output_tokens / 1_000_000 * price_out
    return total / result.n_total * 100


# --- thresholds ---------------------------------------------------------------------------
def default_thresholds_path() -> Path:
    return Path(__file__).resolve().parents[2] / "06-acceptance" / "thresholds.json"


def load_thresholds(path: str | Path | None = None) -> dict[str, float]:
    source = Path(path) if path else default_thresholds_path()
    data = json.loads(source.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}


def check_thresholds(result: EvalResult, thresholds: dict[str, float]) -> list[ThresholdCheck]:
    specs: list[tuple[str, str, float | None, str, str]] = [
        ("offline_min_samples", "真实样本数", float(result.n_real), ">=", "只统计 data_origin=real；合成数据不计入验收"),
        ("offline_min_b2b_samples", "真实 B 端样本数", float(result.n_real_b2b), ">=", "只统计 data_origin=real"),
        ("b2b_recall_min", "B 端召回率（主指标）", result.b2b_recall, ">=", ""),
        ("b2b_precision_min", "B 端精确率", result.b2b_precision, ">=", ""),
        ("country_accuracy_min", "国家准确率（有号码前缀）", result.country_accuracy, ">=", ""),
        ("product_recognition_min", "产品识别率（集合完全一致）", result.product_recognition, ">=", ""),
        ("escalation_rate_max", "升级率", result.escalation_rate, "<=", "含 B 端字段收集完成后的正常交接"),
        ("json_parse_success_min", "JSON 解析成功率", result.parse_success, ">=", ""),
    ]
    checks: list[ThresholdCheck] = []
    for key, label, value, comparator, note in specs:
        if key not in thresholds:
            continue
        limit = float(thresholds[key])
        if value is None:
            passed = False
            note = (note + "；" if note else "") + "无可统计样本"
        else:
            passed = value >= limit if comparator == ">=" else value <= limit
        checks.append(ThresholdCheck(key, label, value, limit, comparator, passed, note))
    return checks
