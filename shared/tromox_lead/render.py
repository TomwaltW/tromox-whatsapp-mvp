"""Render generated artefacts from the single source of truth (see scripts/gen_schema_artifacts.py)."""
from __future__ import annotations

import json

from .enums import B2BType, B2CIntent, EscalationReason
from .fields import AI_EXTRACTION_FIELDS, FIELD_SPECS, LABEL_COLUMNS
from .products import PRODUCT_CATALOG
from .schema import Lead


def lead_json_schema() -> dict:
    schema = Lead.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "TromoxLead"
    return schema


def extraction_json_block() -> str:
    """The JSON block embedded verbatim in both prompts (keys + allowed values)."""
    hints: dict[str, object] = {
        "language": "<ISO 639-1 code of the customer's language, e.g. en, es, de, fr, pt, it>",
        "segment": "B2B | B2C | unknown",
        "b2b_type": " | ".join(B2BType.values()) + " | null",
        "b2c_intent": " | ".join(B2CIntent.values()) + " | null",
        "country_stated": "<ISO 3166-1 alpha-2 ONLY if the customer states their country/market, else null>",
        "city_region": "<string or null>",
        "contact_name": "<string or null>",
        "company": "<string or null>",
        "role": "<string or null>",
        "product_interest": [f"<zero or more of: {', '.join(PRODUCT_CATALOG)}>"],
        "volume": "<short quote of stated quantity/frequency, or null>",
        "existing_dealer_relationship": "<short text or null>",
        "ai_summary": "<1-2 sentences for the sales team, in Simplified Chinese>",
        "ai_confidence": "<number between 0 and 1 for the segment decision>",
        "escalation_flag": "true | false",
        "escalation_reason": " | ".join(EscalationReason.values()) + " | null",
    }
    assert tuple(hints) == AI_EXTRACTION_FIELDS, "extraction block out of sync with AI_EXTRACTION_FIELDS"
    return json.dumps(hints, ensure_ascii=False, indent=2)


def labeling_header() -> str:
    return ",".join(LABEL_COLUMNS)


def fields_markdown_table() -> str:
    lines = ["| # | 字段 | 类型 | 来源 | 说明 | AI 抽取块 | 标注列 |", "|---|---|---|---|---|---|---|"]
    for index, spec in enumerate(FIELD_SPECS, start=1):
        type_label = spec.type_label.replace("|", "\\|")  # escape pipes inside a markdown table cell
        ai_mark = "是" if spec.ai_extracted else ""
        label_mark = "是" if spec.label_column else ""
        lines.append(
            f"| {index} | `{spec.name}` | {type_label} | {spec.source} | {spec.description} | {ai_mark} | {label_mark} |"
        )
    return "\n".join(lines)
