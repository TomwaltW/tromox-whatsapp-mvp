"""Pydantic models: the lead record and the AI extraction block.

`Lead` is the full record stored by the webhook service (01-design/lead-schema.md).
`AIExtraction` is the subset the model returns as JSON - identical for the Botmaker AI
Agent (route A), the external classify call (route B) and the offline eval tool.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import phonenumbers
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import B2BType, B2CIntent, EscalationReason, LeadStatus, Segment, SourceChannel
from .products import normalize_products

_NULLISH = {"", "null", "none", "n/a", "na", "unknown", "undefined", "-"}


def _clean_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return None if text.lower() in _NULLISH else text


# Common non-ISO answers the model gives for a country / market.
_COUNTRY_ALIASES = {"UK": "GB"}
_LANGUAGE_RE = re.compile(r"[a-z]{2}")


def _clean_country(value: Any) -> str | None:
    """ISO 3166-1 alpha-2 of a stated country, or None.

    `UK` is mapped to `GB` (the ISO code, and what `country_from_phone` yields for +44), so a
    lead cannot end up with `country_uk` next to `country_gb`. Anything else must be a region
    phonenumbers knows (`phonenumbers.SUPPORTED_REGIONS`); `EU`, `XX` and similar are dropped.

    Trade-off: `NA` stays an empty value (it is in `_NULLISH`) although it is also Namibia's
    code - a model writing `n/a` / `NA` for "not stated" is far more likely than a Namibian
    market; a Namibian lead still gets its country from the phone prefix.
    """
    text = _clean_optional_str(value)
    if text is None:
        return None
    text = text.upper()
    text = _COUNTRY_ALIASES.get(text, text)
    return text if text in phonenumbers.SUPPORTED_REGIONS else None


def _clean_enum(value: Any) -> Any:
    """Treat nullish strings as None so '"b2b_type": "null"' does not fail validation."""
    if isinstance(value, str):
        cleaned = _clean_optional_str(value)
        return cleaned.lower() if cleaned is not None else None
    return value


class Referral(BaseModel):
    """Click-to-WhatsApp ad referral. Whether Botmaker passes it through is 【待核实】."""

    model_config = ConfigDict(extra="ignore")

    source_type: str | None = None
    source_id: str | None = None
    source_url: str | None = None
    headline: str | None = None
    body: str | None = None
    ctwa_clid: str | None = None


class AIExtraction(BaseModel):
    """JSON block returned by the model. Field order here is the order in the prompt."""

    model_config = ConfigDict(extra="ignore")

    language: str = "und"
    segment: Segment = Segment.UNKNOWN
    b2b_type: B2BType | None = None
    b2c_intent: B2CIntent | None = None
    country_stated: str | None = None
    city_region: str | None = None
    contact_name: str | None = None
    company: str | None = None
    role: str | None = None
    product_interest: list[str] = Field(default_factory=list)
    volume: str | None = None
    existing_dealer_relationship: str | None = None
    ai_summary: str = ""
    ai_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    escalation_flag: bool = False
    escalation_reason: EscalationReason | None = None

    @field_validator("language", mode="before")
    @classmethod
    def _v_language(cls, v: Any) -> str:
        """ISO 639-1 primary subtag, or "und".

        `en-US` -> `en`, `pt_BR` -> `pt`; `und`, full names (`German`), single letters and
        empty values -> `und`. Never truncate: `"und"[:2]` would store `un`.
        """
        text = _clean_optional_str(v)
        if not text:
            return "und"
        primary = text.lower().replace("_", "-").split("-", 1)[0]
        return primary if _LANGUAGE_RE.fullmatch(primary) else "und"

    @field_validator("segment", mode="before")
    @classmethod
    def _v_segment(cls, v: Any) -> Any:
        text = _clean_optional_str(v)
        if text is None:
            return Segment.UNKNOWN
        upper = text.upper()
        return upper if upper in ("B2B", "B2C") else Segment.UNKNOWN

    @field_validator("b2b_type", "b2c_intent", "escalation_reason", mode="before")
    @classmethod
    def _v_enum(cls, v: Any) -> Any:
        return _clean_enum(v)

    @field_validator("country_stated", mode="before")
    @classmethod
    def _v_country(cls, v: Any) -> str | None:
        return _clean_country(v)

    @field_validator(
        "city_region", "contact_name", "company", "role", "volume",
        "existing_dealer_relationship", mode="before",
    )
    @classmethod
    def _v_optional_str(cls, v: Any) -> str | None:
        return _clean_optional_str(v)

    @field_validator("product_interest", mode="before")
    @classmethod
    def _v_products(cls, v: Any) -> list[str]:
        return normalize_products(v)

    @field_validator("ai_summary", mode="before")
    @classmethod
    def _v_summary(cls, v: Any) -> str:
        return "" if v is None else str(v).strip()

    @field_validator("ai_confidence", mode="before")
    @classmethod
    def _v_confidence(cls, v: Any) -> float:
        try:
            return min(1.0, max(0.0, float(v)))
        except (TypeError, ValueError):
            return 0.0

    @field_validator("escalation_flag", mode="before")
    @classmethod
    def _v_flag(cls, v: Any) -> bool:
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "y")
        return bool(v)

    @model_validator(mode="after")
    def _consistency(self) -> "AIExtraction":
        if self.segment is not Segment.B2B:
            self.b2b_type = None
        if self.segment is not Segment.B2C:
            self.b2c_intent = None
        if not self.escalation_flag:
            self.escalation_reason = None
        return self


class Lead(BaseModel):
    """Full lead record. One lead per contact.

    The dedupe key is the E.164 phone number. When the platform delivers no phone number
    (a customer reaching the business through a WhatsApp username only exposes a
    business-scoped user id), `phone` is None and the lead is keyed by the platform's
    customer id instead - see `tromox_lead.ids.contact_key`.
    """

    model_config = ConfigDict(extra="ignore")

    lead_id: str
    phone: str | None = None
    country_by_phone: str | None = None
    country_stated: str | None = None
    language: str = "und"
    contact_name: str | None = None
    profile_name: str | None = None  # WhatsApp profile name (firstName + lastName): display fallback only
    company: str | None = None
    role: str | None = None
    segment: Segment = Segment.UNKNOWN
    b2b_type: B2BType | None = None
    b2c_intent: B2CIntent | None = None
    product_interest: list[str] = Field(default_factory=list)
    volume: str | None = None
    city_region: str | None = None
    existing_dealer_relationship: str | None = None
    source_channel: SourceChannel = SourceChannel.UNKNOWN
    source_code: str | None = None
    referral: Referral | None = None
    first_message_ts: datetime | None = None
    last_message_ts: datetime | None = None
    ai_summary: str = ""
    ai_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    escalation_flag: bool = False
    escalation_reason: EscalationReason | None = None
    assigned_to: str | None = None
    status: LeadStatus = LeadStatus.NEW
    tags: list[str] = Field(default_factory=list)
    consent_marketing: bool | None = None
    notes: str | None = None

    def apply_extraction(self, extraction: AIExtraction) -> "Lead":
        """Merge an AI extraction into the lead.

        * Only fields explicitly present in the extraction are considered, so a partial
          update (one variable changed) cannot reset the others to their defaults.
        * Empty values (None, "", [], "und") never overwrite a known value.
        * A known B2B / B2C segment is never downgraded to unknown.
        * Segment-specific fields are cleared when the segment changes, and the reason is
          cleared when the flag is off, so no stale combination survives a merge.
        An explicit `escalation_flag: false` does clear the flag: the conversation flow resets
        it at the start of a new session (see 01-design/conversation-flow.md).
        """
        data = extraction.model_dump(exclude_unset=True)
        for key, value in data.items():
            if value is None or (isinstance(value, (str, list)) and value in ("", [], "und")):
                continue
            if key == "segment" and value == Segment.UNKNOWN and self.segment is not Segment.UNKNOWN:
                continue
            setattr(self, key, value)
        if self.segment is not Segment.B2B:
            self.b2b_type = None
        if self.segment is not Segment.B2C:
            self.b2c_intent = None
        if not self.escalation_flag:
            self.escalation_reason = None
        return self
