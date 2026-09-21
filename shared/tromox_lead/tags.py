"""Tag generation per 01-design/tag-taxonomy.md.

Tag format: <dimension>_<value>, lower-case ASCII, digits and underscores only, so it is
safe on any BSP. `TIER_LITE_DIMENSIONS` is the reduced scope of the lite package.
"""
from __future__ import annotations

import re

from .country import effective_country
from .enums import B2BType, EscalationReason, Segment
from .schema import Lead

TAG_DIMENSIONS: tuple[str, ...] = (
    "country", "seg", "b2b", "prod", "intent", "stage", "src", "lang", "prio",
)
TIER_LITE_DIMENSIONS: tuple[str, ...] = ("country", "seg")
TIER_FULL_DIMENSIONS: tuple[str, ...] = TAG_DIMENSIONS

_SAFE_RE = re.compile(r"[^a-z0-9]+")
_HIGH_PRIORITY_B2B = {B2BType.DISTRIBUTOR, B2BType.IMPORTER, B2BType.FLEET}


def _tag(dimension: str, value: str) -> str:
    return f"{dimension}_{_SAFE_RE.sub('_', value.lower()).strip('_')}"


def build_tags(lead: Lead, dimensions: tuple[str, ...] = TIER_FULL_DIMENSIONS) -> list[str]:
    tags: list[str] = []

    def add(dimension: str, value: str | None) -> None:
        if value and dimension in dimensions:
            tags.append(_tag(dimension, value))

    add("country", effective_country(lead.country_stated, lead.country_by_phone))
    add("seg", lead.segment.value)
    add("b2b", lead.b2b_type.value if lead.b2b_type else None)
    for product in lead.product_interest:
        add("prod", product)
    add("intent", lead.b2c_intent.value if lead.b2c_intent else None)
    add("stage", lead.status.value)
    add("src", lead.source_channel.value if lead.source_channel.value != "unknown" else None)
    add("lang", lead.language if lead.language != "und" else None)
    if lead.segment is Segment.B2B:
        high = lead.b2b_type in _HIGH_PRIORITY_B2B
        add("prio", "high" if high else "normal")
    elif lead.escalation_reason is EscalationReason.COMPLAINT_WARRANTY_LEGAL_SAFETY:
        add("prio", "high")
    return sorted(set(tags))
