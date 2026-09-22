"""Webhook pipeline.

handle():  persist raw event -> idempotency check -> parse -> normalise -> upsert by contact key (phone)
           -> write local mirrors / queue the remote ones -> claim a notification (once per lead +
           reason + session).
deliver(): runs AFTER the HTTP response (FastAPI BackgroundTasks): render the card, send to
           every configured channel with bounded retries, record the outcome. A delivery
           failure is stored for `python -m app.replay`; it never affects the webhook reply.
mirror():  the same shape for remote storage sinks (Feishu Bitable): the request path only writes
           a `mirror_outbox` row, and this sends it after the response. Whatever fails stays
           pending for `python -m app.replay`. Neither call ever raises.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import ValidationError

from tromox_lead import Lead

from .config import Settings
from .models import BotmakerWebhook
from .normalize import collect_message_facts, merge_events, merge_message, notification_suppressed, resolve_contact
from .notify import Notifier, NotifyError, build_card
from .retry import RetryError, RetryPolicy, retry_call
from .store import LeadSink, MirrorError, RawEventState, SqliteStore

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class HandleResult:
    outcome: str
    kind: str
    event_key: str
    lead_id: str | None = None
    notification_id: int | None = None
    mirror_queued: bool = False   # a remote sink is waiting in mirror_outbox: run `mirror(lead_id)` after the response


def compute_event_key(payload: dict[str, Any], parsed: BotmakerWebhook | None) -> str:
    """Stable identity of a callback, so that a redelivery is recognised."""
    if parsed is not None:
        ids = [m.id for m in parsed.messages if m.id]
        if parsed.kind == "message" and ids and len(ids) == len(parsed.messages):
            return "msg:" + "+".join(sorted(ids))
        if parsed.kind == "status" and parsed.message_id:
            return f"st:{parsed.message_id}:{parsed.status}"
    body = {k: v for k, v in payload.items() if k != "_note"}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()
    return f"hash:{digest[:32]}"


class Pipeline:
    def __init__(self, settings: Settings, store: SqliteStore, sinks: list[LeadSink],
                 notifiers: list[Notifier], *, retry_policy: RetryPolicy = RetryPolicy(),
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self.settings = settings
        self.store = store
        self.sinks = sinks
        self.notifiers = notifiers
        self.retry_policy = retry_policy
        self._sleep = sleep
        self._clock = clock

    # ------------------------------------------------------------------ inbound
    def handle(self, payload: dict[str, Any]) -> HandleResult:
        try:
            parsed: BotmakerWebhook | None = BotmakerWebhook.model_validate(payload)
        except ValidationError:
            parsed = None
        kind = parsed.kind if parsed else "unknown"
        event_key = compute_event_key(payload, parsed)

        raw_json = json.dumps(payload, ensure_ascii=False, default=str)
        state = self.store.record_raw_event(event_key, kind, raw_json)  # durable BEFORE any processing
        if state is RawEventState.DUPLICATE_PROCESSED:
            log.info("duplicate callback ignored", extra={"event_key": event_key, "kind": kind, "outcome": "duplicate"})
            return HandleResult("duplicate", kind, event_key)

        try:
            result = self._process(payload, parsed, kind, event_key)
        except Exception as exc:  # stays in raw_events for `python -m app.replay`
            self.store.mark_failed(event_key, f"{type(exc).__name__}: {exc}")
            log.exception("processing failed; event kept for replay",
                          extra={"event_key": event_key, "kind": kind, "outcome": "stored_unprocessed",
                                 "error_type": type(exc).__name__})
            return HandleResult("stored_unprocessed", kind, event_key)

        self.store.mark_processed(event_key, result.outcome, keep_payload=self.settings.keep_raw_payloads)
        log.info("callback processed", extra={"event_key": event_key, "kind": kind, "outcome": result.outcome,
                                              "lead_id": result.lead_id, "notification_id": result.notification_id})
        return result

    def _process(self, payload: dict[str, Any], parsed: BotmakerWebhook | None, kind: str, event_key: str) -> HandleResult:
        if parsed is None:
            return HandleResult("invalid_payload", kind, event_key)
        if kind == "status":
            if parsed.error:
                log.warning("message status reported an error",
                            extra={"event_key": event_key, "kind": kind, "reason": str(parsed.error[0].get("code", ""))})
            return HandleResult("ignored_status", kind, event_key)
        if kind == "unknown":
            return HandleResult("ignored_unknown", kind, event_key)

        phone, key = resolve_contact(parsed)
        if key is None:  # another channel, or neither a phone number nor a platform customer id
            log.warning("callback without a usable contact identity; lead not recorded",
                        extra={"event_key": event_key, "kind": kind, "outcome": "skipped_no_contact"})
            return HandleResult("skipped_no_contact", kind, event_key)
        if phone is None:  # recorded anyway, keyed by the platform customer id; country must be asked
            log.warning("contact without a phone number; lead keyed by platform customer id",
                        extra={"event_key": event_key, "kind": kind})

        tier = self.settings.tag_tier
        if kind == "message":
            facts = collect_message_facts(parsed)
            lead = self.store.update_lead(key, lambda existing: merge_message(existing, phone, facts, tier, key),
                                          customer_id=parsed.customer_id)
        else:
            unmapped: list[str] = []

            def mutate(existing: Lead | None) -> Lead:
                merged, missing = merge_events(existing, phone, parsed.events, tier, key)
                unmapped.extend(missing)
                return merged

            lead = self.store.update_lead(key, mutate, customer_id=parsed.customer_id)
            for typification in unmapped:
                log.warning("typification has no status mapping",
                            extra={"event_key": event_key, "lead_id": lead.lead_id, "typification": typification})

        mirror_queued = False
        for sink in self.sinks:
            try:
                if getattr(sink, "remote", False):
                    # network hop: only record the intent here, `mirror()` sends it after the response
                    self.store.enqueue_mirror(lead.lead_id, sink.name)
                    mirror_queued = True
                else:
                    sink.upsert_lead(lead)
            except Exception as exc:  # a mirror must never block the ledger
                log.error("storage sink failed", extra={"channel": sink.name, "lead_id": lead.lead_id,
                                                        "error_type": type(exc).__name__})

        notification_id = None
        if kind == "message" and lead.escalation_flag and lead.escalation_reason is not None:
            suppressed = notification_suppressed(lead, facts)
            if suppressed:  # decided BEFORE the claim, so no row is written for a withheld card
                log.info("notification withheld", extra={"event_key": event_key, "lead_id": lead.lead_id,
                                                         "reason": suppressed})
            else:
                session_key = parsed.session_id or self._clock().strftime("%Y-%m-%d")
                notification_id = self.store.claim_notification(
                    lead.lead_id, lead.escalation_reason.value, session_key, parsed.customer_id)
        return HandleResult("lead_upserted", kind, event_key, lead.lead_id, notification_id, mirror_queued)

    # ------------------------------------------------------------------ outbound
    def mirror(self, lead_id: str) -> dict[str, str]:
        """Send this lead's pending remote mirrors. Returns {sink name: "sent"|"failed"}; never raises.

        Runs after the HTTP response (background task) and again from `python -m app.replay`. What
        is sent is the lead as the ledger holds it *now*, not a snapshot taken at callback time, so
        a row that waited through several callbacks still ends up correct."""
        try:
            return self._mirror(lead_id)
        except Exception as exc:  # last line of defence: a background task must not crash the worker
            log.exception("mirror run crashed", extra={"lead_id": lead_id, "error_type": type(exc).__name__})
            return {}

    def _mirror(self, lead_id: str) -> dict[str, str]:
        rows = self.store.pending_mirrors(lead_id)
        if not rows:
            return {}
        by_name = {sink.name: sink for sink in self.sinks}
        lead = self.store.get_lead(lead_id)
        results: dict[str, str] = {}
        for row in rows:
            sink = by_name.get(row.sink)
            if sink is None:  # STORAGE_BACKENDS changed while the row was waiting
                self.store.finish_mirror(row.id, False, f"{row.sink}: sink not configured")
                results[row.sink] = "failed"
                log.error("mirror sink not configured", extra={"lead_id": lead_id, "sink": row.sink,
                                                               "attempts": row.attempts + 1,
                                                               "error_type": "SinkNotConfigured"})
                continue
            if lead is None:  # erased between the callback and the send: nothing left to mirror
                self.store.finish_mirror(row.id, False, "lead not found")
                results[row.sink] = "failed"
                log.error("mirror skipped: lead not found", extra={"lead_id": lead_id, "sink": row.sink,
                                                                   "attempts": row.attempts + 1,
                                                                   "error_type": "LeadNotFound"})
                continue
            try:
                _, attempts = retry_call(lambda s=sink: s.upsert_lead(lead), self.retry_policy, self._sleep)
            except RetryError as exc:
                # keep the text only for the sink's own error type (URL- and secret-free by construction)
                detail = str(exc.last) if isinstance(exc.last, MirrorError) else type(exc.last).__name__
                self.store.finish_mirror(row.id, False, detail)
                results[row.sink] = "failed"
                log.error("mirror failed", extra={"lead_id": lead_id, "sink": row.sink,
                                                  "attempts": row.attempts + 1, "error_type": type(exc.last).__name__})
            else:
                self.store.finish_mirror(row.id, True, None)
                results[row.sink] = "sent"
                log.info("mirror sent", extra={"lead_id": lead_id, "sink": row.sink, "attempts": attempts})
        return results

    def deliver(self, notification_id: int) -> str:
        """Send one claimed notification. Returns the final status; never raises."""
        try:
            return self._deliver(notification_id)
        except Exception as exc:  # last line of defence: background task must not crash the worker
            log.exception("notification delivery crashed",
                          extra={"notification_id": notification_id, "error_type": type(exc).__name__})
            self.store.finish_notification(notification_id, "failed", 1, [], f"{type(exc).__name__}")
            return "failed"

    def _deliver(self, notification_id: int) -> str:
        row = self.store.get_notification(notification_id)
        if row is None:
            return "missing"
        lead = self.store.get_lead(row.lead_id)
        if lead is None:
            self.store.finish_notification(notification_id, "failed", 1, [], "lead not found")
            return "failed"
        if not self.notifiers:
            log.warning("escalation without any notifier configured (set NOTIFIERS)",
                        extra={"notification_id": notification_id, "lead_id": lead.lead_id})
            self.store.finish_notification(notification_id, "skipped", 0, [], "no notifier configured")
            return "skipped"

        card = build_card(
            lead, customer_id=row.customer_id or self.store.get_customer_id(lead.lead_id),
            mask=self.settings.notify_mask_phone, chat_url_template=self.settings.botmaker_chat_url_template,
            display_timezone=self.settings.display_timezone, now=self._clock(),
        )
        succeeded: list[str] = []
        errors: list[str] = []
        attempts_total = 0
        for notifier in self.notifiers:
            try:
                _, attempts = retry_call(lambda n=notifier: n.send(card), self.retry_policy, self._sleep)
                attempts_total += attempts
                succeeded.append(notifier.name)
                log.info("notification sent", extra={"notification_id": notification_id, "lead_id": lead.lead_id,
                                                     "channel": notifier.name, "attempts": attempts})
            except RetryError as exc:
                attempts_total += exc.attempts
                # NotifyError texts are URL-free by construction; for anything else keep the type only
                detail = str(exc.last) if isinstance(exc.last, NotifyError) else type(exc.last).__name__
                errors.append(detail if detail.startswith(f"{notifier.name}:") else f"{notifier.name}: {detail}")
                log.error("notification failed", extra={"notification_id": notification_id, "lead_id": lead.lead_id,
                                                        "channel": notifier.name, "attempts": exc.attempts,
                                                        "error_type": type(exc.last).__name__})
        status = "sent" if not errors else ("partial" if succeeded else "failed")
        self.store.finish_notification(notification_id, status, attempts_total, succeeded, "; ".join(errors) or None)
        return status
