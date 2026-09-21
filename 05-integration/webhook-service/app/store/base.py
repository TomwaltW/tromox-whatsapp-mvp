"""Storage interfaces."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from tromox_lead import Lead


class RawEventState(str, Enum):
    NEW = "new"                                    # first time we see this event
    DUPLICATE_PROCESSED = "duplicate_processed"    # redelivery of something already handled
    DUPLICATE_UNPROCESSED = "duplicate_unprocessed"  # seen before but processing never finished


@dataclass(frozen=True)
class NotificationRow:
    id: int
    lead_id: str
    escalation_reason: str
    session_key: str
    customer_id: str | None
    status: str          # pending | sent | partial | failed | skipped
    attempts: int
    last_error: str | None


@runtime_checkable
class LeadSink(Protocol):
    """Secondary destination that mirrors lead upserts (CSV, Feishu Bitable, Google Sheets)."""

    name: str

    def upsert_lead(self, lead: Lead) -> None:  # pragma: no cover - protocol
        ...
