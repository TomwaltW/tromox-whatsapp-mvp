"""SQLite primary store: leads, raw_events, processed_events, notifications.

One short-lived connection per operation (thread-safe with FastAPI's thread pool). The
lead read-modify-write runs inside BEGIN IMMEDIATE, so two callbacks for the same phone
cannot lose each other's update, even with several worker processes.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

from tromox_lead import Lead, effective_country

from .base import NotificationRow, RawEventState

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    lead_id      TEXT PRIMARY KEY,
    contact_key  TEXT NOT NULL UNIQUE,  -- E.164 phone, or "bm:<customer id>" when the platform gives no number
    phone        TEXT,
    customer_id  TEXT,
    status       TEXT,
    segment      TEXT,
    country      TEXT,
    data_json    TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key    TEXT NOT NULL UNIQUE,
    kind         TEXT,
    received_at  TEXT NOT NULL,
    payload_json TEXT,
    processed    INTEGER NOT NULL DEFAULT 0,
    error        TEXT
);
CREATE TABLE IF NOT EXISTS processed_events (
    event_key    TEXT PRIMARY KEY,
    processed_at TEXT NOT NULL,
    outcome      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id           TEXT NOT NULL,
    escalation_reason TEXT NOT NULL,
    session_key       TEXT NOT NULL,
    customer_id       TEXT,
    status            TEXT NOT NULL DEFAULT 'pending',
    attempts          INTEGER NOT NULL DEFAULT 0,
    channels_ok       TEXT,
    last_error        TEXT,
    created_at        TEXT NOT NULL,
    sent_at           TEXT,
    UNIQUE (lead_id, escalation_reason, session_key)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class SqliteStore:
    name = "sqlite"

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)  # explicit transactions
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------ raw events / idempotency
    def record_raw_event(self, event_key: str, kind: str, payload_json: str) -> RawEventState:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO raw_events (event_key, kind, received_at, payload_json) VALUES (?, ?, ?, ?)",
                (event_key, kind, _now(), payload_json),
            )
            if cursor.rowcount == 1:
                return RawEventState.NEW
            done = conn.execute("SELECT 1 FROM processed_events WHERE event_key = ?", (event_key,)).fetchone()
            if done:
                return RawEventState.DUPLICATE_PROCESSED
            # keep the freshest payload for the retry
            conn.execute("UPDATE raw_events SET payload_json = ? WHERE event_key = ?", (payload_json, event_key))
            return RawEventState.DUPLICATE_UNPROCESSED

    def mark_processed(self, event_key: str, outcome: str, keep_payload: bool = False) -> None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT OR REPLACE INTO processed_events (event_key, processed_at, outcome) VALUES (?, ?, ?)",
                (event_key, _now(), outcome),
            )
            if keep_payload:
                conn.execute("UPDATE raw_events SET processed = 1, error = NULL WHERE event_key = ?", (event_key,))
            else:  # data minimisation: chat content does not stay in the lead store
                conn.execute(
                    "UPDATE raw_events SET processed = 1, error = NULL, payload_json = NULL WHERE event_key = ?",
                    (event_key,),
                )
            conn.execute("COMMIT")

    def mark_failed(self, event_key: str, error: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE raw_events SET error = ? WHERE event_key = ?", (error[:500], event_key))

    def unprocessed_events(self) -> list[tuple[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event_key, payload_json FROM raw_events WHERE processed = 0 AND payload_json IS NOT NULL ORDER BY id"
            ).fetchall()
        return [(row["event_key"], row["payload_json"]) for row in rows]

    # ------------------------------------------------------------------ leads
    def update_lead(self, key: str, mutate: Callable[[Lead | None], Lead], customer_id: str | None = None) -> Lead:
        """Atomic read-modify-write of the lead identified by its contact key (normally the phone)."""
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT data_json FROM leads WHERE contact_key = ?", (key,)).fetchone()
                existing = Lead.model_validate_json(row["data_json"]) if row else None
                lead = mutate(existing)
                now = _now()
                conn.execute(
                    """
                    INSERT INTO leads (lead_id, contact_key, phone, customer_id, status, segment, country, data_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(contact_key) DO UPDATE SET
                        phone = COALESCE(excluded.phone, leads.phone),
                        customer_id = COALESCE(excluded.customer_id, leads.customer_id),
                        status = excluded.status, segment = excluded.segment, country = excluded.country,
                        data_json = excluded.data_json, updated_at = excluded.updated_at
                    """,
                    (lead.lead_id, key, lead.phone, customer_id, lead.status.value, lead.segment.value,
                     effective_country(lead.country_stated, lead.country_by_phone),
                     lead.model_dump_json(), now, now),
                )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return lead

    def get_lead(self, lead_id: str) -> Lead | None:
        with self._connect() as conn:
            row = conn.execute("SELECT data_json FROM leads WHERE lead_id = ?", (lead_id,)).fetchone()
        return Lead.model_validate_json(row["data_json"]) if row else None

    def get_lead_by_phone(self, phone: str) -> Lead | None:
        with self._connect() as conn:
            row = conn.execute("SELECT data_json FROM leads WHERE phone = ?", (phone,)).fetchone()
        return Lead.model_validate_json(row["data_json"]) if row else None

    def get_customer_id(self, lead_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT customer_id FROM leads WHERE lead_id = ?", (lead_id,)).fetchone()
        return row["customer_id"] if row else None

    def list_leads(self) -> list[Lead]:
        with self._connect() as conn:
            rows = conn.execute("SELECT data_json FROM leads ORDER BY created_at, lead_id").fetchall()
        return [Lead.model_validate_json(row["data_json"]) for row in rows]

    # ------------------------------------------------------------------ notifications
    def claim_notification(self, lead_id: str, reason: str, session_key: str, customer_id: str | None) -> int | None:
        """Insert the (lead, reason, session) row; None when it already exists (= already notified)."""
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO notifications (lead_id, escalation_reason, session_key, customer_id, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (lead_id, reason, session_key, customer_id, _now()),
            )
            return int(cursor.lastrowid) if cursor.rowcount == 1 else None

    def get_notification(self, notification_id: int) -> NotificationRow | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
        return self._notification(row) if row else None

    def finish_notification(self, notification_id: int, status: str, attempts: int,
                            channels_ok: list[str], last_error: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE notifications SET status = ?, attempts = attempts + ?, channels_ok = ?, last_error = ?, "
                "sent_at = CASE WHEN ? IN ('sent', 'partial') THEN ? ELSE sent_at END WHERE id = ?",
                (status, attempts, ",".join(channels_ok), (last_error or "")[:500] or None, status, _now(), notification_id),
            )

    def retryable_notifications(self, max_attempts: int = 10) -> list[NotificationRow]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM notifications WHERE status IN ('pending', 'failed', 'partial') AND attempts < ? ORDER BY id",
                (max_attempts,),
            ).fetchall()
        return [self._notification(row) for row in rows]

    @staticmethod
    def _notification(row: sqlite3.Row) -> NotificationRow:
        return NotificationRow(
            id=row["id"], lead_id=row["lead_id"], escalation_reason=row["escalation_reason"],
            session_key=row["session_key"], customer_id=row["customer_id"], status=row["status"],
            attempts=row["attempts"], last_error=row["last_error"],
        )

    # ------------------------------------------------------------------ health
    def ping(self) -> bool:
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False
