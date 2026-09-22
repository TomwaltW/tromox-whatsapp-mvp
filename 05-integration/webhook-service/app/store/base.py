"""Storage interfaces."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from tromox_lead import Lead


class MirrorError(RuntimeError):
    """A sink's own failure, raised with a message that carries neither a secret nor a URL.

    `pipeline.mirror` keeps the text of these in `mirror_outbox.last_error`; anything else is
    recorded by type name only (same rule as `NotifyError` in the notification path)."""


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


@dataclass(frozen=True)
class MirrorRow:
    """One pending / sent entry of `mirror_outbox`: this lead still has to reach this sink."""

    id: int
    lead_id: str
    sink: str
    status: str          # pending | sent
    attempts: int
    last_error: str | None


@runtime_checkable
class LeadSink(Protocol):
    """Secondary destination that mirrors lead upserts (CSV, Feishu Bitable, Google Sheets).

    `remote` says whether reaching this sink costs network round trips. A remote sink is NEVER
    called from the request path: `pipeline._process` only writes a `mirror_outbox` row, and the
    send happens after the HTTP response (`pipeline.mirror`, a background task) with whatever is
    left retried by `python -m app.replay`. A slow or dead mirror therefore cannot delay the reply
    to Botmaker (README §1, "先落盘"). A local sink (the CSV export) stays synchronous.

    The attribute is read structurally (`getattr(sink, "remote", False)`), so a sink that does not
    declare it counts as local.

    Optional method (not part of the protocol, looked up with `getattr(sink, "delete_lead", None)`):
        delete_lead(lead_id: str) -> bool
    Removes the mirror's copy of one lead for a deletion request (`python -m app.forget`); True when
    a record was deleted, False when the mirror had none. A sink without it, such as the CSV export,
    is handled by the command itself (the CSV is rewritten from the ledger).
    """

    name: str
    remote: bool = False

    def upsert_lead(self, lead: Lead) -> None:  # pragma: no cover - protocol
        ...
