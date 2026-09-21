#!/usr/bin/env python3
"""Generate every artefact derived from the shared lead schema.

Single source of truth: shared/tromox_lead (pydantic models + field registry) and
shared/prompt_blocks/. This script writes / injects:

  01-design/lead.schema.json                 JSON Schema of the lead record
  04-eval/labeling-template.csv              header + example rows
  <!-- BEGIN GENERATED: name --> blocks in   01-design/lead-schema.md,
                                             04-eval/prompts/classify-v1.md,
                                             02-botmaker/ai-agent-system-prompt.md

Usage:
  python scripts/gen_schema_artifacts.py          # write
  python scripts/gen_schema_artifacts.py --check  # exit 1 if anything is stale
  python scripts/gen_schema_artifacts.py --only 04-eval/prompts/classify-v1.md   # touch one target only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared"))

from tromox_lead import render  # noqa: E402

PROMPT_BLOCKS = ROOT / "shared" / "prompt_blocks"

LABEL_EXAMPLE_ROWS = [
    "EX-001,example,+4917604069001,\"Hallo, wir sind ein Motorradhändler in Hamburg und möchten Tromox verkaufen. [IG-2609]\",de,B2B,dealer,,DE,,false,,yes,示例,示例行：填写前请删除",
    "EX-002,example,+12025550101,\"Hi, how much is the MC10 and where can I test ride it?\",en,B2C,,test_ride,US,MC10,false,,no,示例,示例行：填写前请删除",
    "EX-003,example,+34600000001,\"Quiero hablar con una persona, mi batería echa humo\",es,B2C,,warranty,ES,,true,complaint_warranty_legal_safety,no,示例,示例行：填写前请删除",
]


def generated_blocks() -> dict[str, str]:
    rules = (PROMPT_BLOCKS / "extraction-rules.md").read_text(encoding="utf-8").strip()
    return {
        "lead-fields-table": render.fields_markdown_table(),
        "extraction-rules": rules,
        "extraction-json": "```json\n" + render.extraction_json_block() + "\n```",
    }


INJECT_TARGETS = {
    "01-design/lead-schema.md": ["lead-fields-table", "extraction-json"],
    "04-eval/prompts/classify-v1.md": ["extraction-rules", "extraction-json"],
    "02-botmaker/ai-agent-system-prompt.md": ["extraction-rules", "extraction-json"],
}


def inject(text: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!-- BEGIN GENERATED: {re.escape(name)} -->)(.*?)(<!-- END GENERATED: {re.escape(name)} -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"marker pair for '{name}' not found")
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="do not write; exit 1 if stale")
    parser.add_argument("--only", action="append", default=[], metavar="REL_PATH",
                        help="limit to these repo-relative output paths (repeatable)")
    args = parser.parse_args()

    outputs: dict[Path, str] = {
        ROOT / "01-design" / "lead.schema.json": json.dumps(render.lead_json_schema(), ensure_ascii=False, indent=2) + "\n",
        ROOT / "04-eval" / "labeling-template.csv": "\n".join([render.labeling_header(), *LABEL_EXAMPLE_ROWS]) + "\n",
    }
    blocks = generated_blocks()
    missing: list[str] = []
    for rel, names in INJECT_TARGETS.items():
        path = ROOT / rel
        if not path.exists():
            missing.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        for name in names:
            text = inject(text, name, blocks[name])
        outputs[path] = text

    if args.only:
        wanted = {(ROOT / rel).resolve() for rel in args.only}
        outputs = {p: c for p, c in outputs.items() if p.resolve() in wanted}
        missing = [rel for rel in missing if (ROOT / rel).resolve() in wanted]
    stale = [p for p, content in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != content]
    if args.check:
        for p in stale:
            print(f"STALE: {p.relative_to(ROOT)}")
        for rel in missing:
            print(f"MISSING: {rel}")
        return 1 if (stale or missing) else 0
    for p in stale:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(outputs[p], encoding="utf-8")
        print(f"wrote {p.relative_to(ROOT)}")
    for rel in missing:
        print(f"skipped (file not present yet): {rel}")
    if not stale:
        print("all generated artefacts up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
