"""Enumerations shared by the lead schema, prompts, eval tool and webhook service.

Single source of truth: every other artefact (JSON Schema, labeling CSV header,
prompt JSON block, tag taxonomy) is generated from or checked against this module.
"""
from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)

    @classmethod
    def values(cls) -> list[str]:
        return [m.value for m in cls]


class Segment(StrEnum):
    B2B = "B2B"
    B2C = "B2C"
    UNKNOWN = "unknown"


class B2BType(StrEnum):
    DEALER = "dealer"
    DISTRIBUTOR = "distributor"
    FLEET = "fleet"
    IMPORTER = "importer"
    OTHER = "other"


class B2CIntent(StrEnum):
    BUY = "buy"
    SUPPORT = "support"
    PARTS = "parts"
    WARRANTY = "warranty"
    TEST_RIDE = "test_ride"
    OTHER = "other"


class EscalationReason(StrEnum):
    """Why the conversation must be handed to a human (01-design/routing-rules.md)."""

    HUMAN_REQUESTED = "human_requested"
    B2B_QUALIFIED = "b2b_qualified"
    LOW_CONFIDENCE = "low_confidence"
    COMPLAINT_WARRANTY_LEGAL_SAFETY = "complaint_warranty_legal_safety"
    PRICE_NEGOTIATION = "price_negotiation"
    NOT_UNDERSTOOD_TWICE = "not_understood_twice"


class LeadStatus(StrEnum):
    NEW = "new"
    QUALIFIED = "qualified"
    HANDED_OFF = "handed_off"
    CONTACTED = "contacted"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    NURTURE = "nurture"
    INVALID = "invalid"


class SourceChannel(StrEnum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    WEBSITE = "website"
    CTWA_AD = "ctwa_ad"
    OFFLINE_QR = "offline_qr"
    OTHER = "other"
    UNKNOWN = "unknown"


# Short-code prefix (wa.me prefilled text, e.g. "Hi Tromox! [IG-2609]") -> channel.
SOURCE_PREFIX_TO_CHANNEL: dict[str, SourceChannel] = {
    "IG": SourceChannel.INSTAGRAM,
    "FB": SourceChannel.FACEBOOK,
    "TT": SourceChannel.TIKTOK,
    "YT": SourceChannel.YOUTUBE,
    "WEB": SourceChannel.WEBSITE,
    "AD": SourceChannel.CTWA_AD,
    "QR": SourceChannel.OFFLINE_QR,
    "OT": SourceChannel.OTHER,
}

# Confidence below this value triggers EscalationReason.LOW_CONFIDENCE.
LOW_CONFIDENCE_THRESHOLD: float = 0.6

# ISO 639-1 codes the MVP bot is expected to handle. Final list is 【待客户确认】.
SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "es", "de", "fr", "pt", "it")
