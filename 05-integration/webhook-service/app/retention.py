"""Retention job: delete what the retention policy says is past its keep-until date.

    python -m app.retention [--older-than-days 730] [--raw-events-days 90] [--dry-run] [--yes] [--now YYYY-MM-DD]

`03-whatsapp/compliance.md` section 4 promises a lead record is deleted 24 months after the last
contact and a raw callback event 90 days after it arrived. `app.forget` erases one contact on
request; this command is the scheduled half of the same promise - a monthly cron job.

What one run removes:
    1. expired leads: every `leads` row whose reference time is older than `--older-than-days`.
       The reference time is the lead's `last_message_ts`, or the row's `updated_at` when the lead
       never recorded a message. The status is irrelevant: `handed_off` and `contacted` leads are
       deleted on the same clock as the rest - a retention period is a retention period. Each lead
       goes through `app.forget`'s `forget_lead()`, so the ledger rows, the raw callbacks that still
       carry the number, and the Bitable mirror all go the same way they do for a single request.
    2. expired raw events: `raw_events` rows that are `processed = 1` and older than
       `--raw-events-days`. The row is deleted whether or not its payload was already blanked -
       the timestamp and the event key are the last thing left of that callback. Unprocessed rows
       stay: they are still work to do, and `app.replay` owns them.
    3. orphan notifications: `notifications` rows whose `lead_id` no longer exists (a lead deleted
       before this command existed, or by an interrupted run).
    4. the CSV mirror, rewritten once for the whole batch when at least one lead was deleted.

Exit codes:  0 done (or --dry-run)   1 a sink failed / configuration error
             3 neither --dry-run nor --yes: the preview was printed, nothing changed.
A sink failure never rolls the ledger back: the rows are gone, the failure is logged, rerun the
command to retry the mirror.

Output rule: neither stdout nor the log ever contains a phone number - counts only, not even the
lead ids (one run can touch thousands of them).
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

from tromox_lead import Lead

from .config import Settings, get_settings
from .forget import forget_lead, lead_phone_digits
from .logging_setup import setup_logging
from .store import CsvExportSink, LeadSink, SqliteStore, build_sinks

log = logging.getLogger("app.retention")

EXIT_OK, EXIT_SINK_FAILED, EXIT_NEEDS_YES = 0, 1, 3

DEFAULT_LEAD_DAYS = 730          # compliance.md section 4: 24 months after the last contact
DEFAULT_RAW_EVENT_DAYS = 90      # compliance.md section 4: raw callbacks


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m app.retention", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--older-than-days", type=int, default=DEFAULT_LEAD_DAYS,
                        help=f"delete leads not contacted for this many days (default {DEFAULT_LEAD_DAYS})")
    parser.add_argument("--raw-events-days", type=int, default=DEFAULT_RAW_EVENT_DAYS,
                        help=f"delete processed raw callbacks older than this (default {DEFAULT_RAW_EVENT_DAYS})")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="only print what would be deleted")
    mode.add_argument("--yes", action="store_true", help="actually delete")
    parser.add_argument("--now", metavar="YYYY-MM-DD",
                        help="treat this UTC date as today (tests and rehearsals; default: today)")
    return parser.parse_args(argv)


def _as_datetime(value: object) -> datetime | None:
    """Parse a stored ISO timestamp. A naive one is read as UTC (everything here is written in UTC)."""
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _reference_time(data_json: str, updated_at: str) -> datetime | None:
    """When this lead was last in touch: its `last_message_ts`, else the row's `updated_at`."""
    try:
        last_message = json.loads(data_json).get("last_message_ts")
    except (TypeError, ValueError):
        last_message = None
    return _as_datetime(last_message) or _as_datetime(updated_at)


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)  # explicit transactions, like SqliteStore
    conn.row_factory = sqlite3.Row
    return conn


def expired_leads(db_path: Path, cutoff: datetime) -> list[tuple[Lead, str]]:
    """Every lead whose reference time is before `cutoff`, as (lead, segment) pairs.

    A row whose timestamps are both unreadable is kept: retention deletes what is provably
    expired, never what merely looks odd."""
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT lead_id, segment, data_json, updated_at FROM leads ORDER BY lead_id").fetchall()
    finally:
        conn.close()
    due: list[tuple[Lead, str]] = []
    for row in rows:
        reference = _reference_time(row["data_json"], row["updated_at"])
        if reference is not None and reference < cutoff:
            due.append((Lead.model_validate_json(row["data_json"]), row["segment"] or "unknown"))
    return due


def count_expired_raw_events(db_path: Path, cutoff: datetime) -> int:
    conn = _connect(db_path)
    try:
        return int(conn.execute("SELECT count(*) FROM raw_events WHERE processed = 1 AND received_at < ?",
                                (_sql_time(cutoff),)).fetchone()[0])
    finally:
        conn.close()


def delete_expired_raw_events(db_path: Path, cutoff: datetime) -> int:
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            deleted = conn.execute("DELETE FROM raw_events WHERE processed = 1 AND received_at < ?",
                                   (_sql_time(cutoff),)).rowcount
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return int(deleted)


_ORPHANS = "notifications WHERE lead_id NOT IN (SELECT lead_id FROM leads)"


def count_orphan_notifications(db_path: Path) -> int:
    conn = _connect(db_path)
    try:
        return int(conn.execute(f"SELECT count(*) FROM {_ORPHANS}").fetchone()[0])
    finally:
        conn.close()


def delete_orphan_notifications(db_path: Path) -> int:
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            deleted = conn.execute(f"DELETE FROM {_ORPHANS}").rowcount
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return int(deleted)


def _sql_time(moment: datetime) -> str:
    """Timestamps are stored as UTC ISO strings, so comparing them as text is comparing them as time."""
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def _resolve_now(raw: str | None) -> datetime:
    if raw:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _print_preview(now: datetime, lead_days: int, raw_days: int, segments: dict[str, int],
                   leads: int, raw_events: int, notifications: int) -> None:
    print(f"retention preview  now={now.date().isoformat()} leads>{lead_days}d raw_events>{raw_days}d")
    print(f"  leads:         {leads}")
    for segment in sorted(segments):
        print(f"    {segment + ':':<13}{segments[segment]}")
    print(f"  raw_events:    {raw_events}")
    print(f"  notifications: {notifications}   (orphans; a deleted lead's own rows go with the lead)")


def run(settings: Settings, argv: Sequence[str] | None = None) -> int:
    """The command with an injected `Settings` (tests call this directly). Returns the exit code."""
    args = _parse_args(argv)
    try:
        now = _resolve_now(args.now)
    except ValueError:
        print("--now must be a date like 2026-12-01")
        return EXIT_SINK_FAILED
    lead_cutoff = now - timedelta(days=args.older_than_days)
    raw_cutoff = now - timedelta(days=args.raw_events_days)

    db_path = Path(settings.database_path)
    store = SqliteStore(db_path)
    backends = settings.storage_backend_list
    try:  # a half-configured sink is a configuration error: stop before touching anything
        sinks: list[LeadSink] = build_sinks(backends, store, settings.csv_export_path, settings=settings)
    except ValueError as exc:
        print(f"configuration error: {exc}")
        return EXIT_SINK_FAILED
    deletable = [sink for sink in sinks if callable(getattr(sink, "delete_lead", None))]
    csv_enabled = "csv" in backends

    due = expired_leads(db_path, lead_cutoff)
    segments: dict[str, int] = {}
    for _lead, segment in due:
        segments[segment] = segments.get(segment, 0) + 1

    if not args.yes:
        # A raw callback that is both expired and still carrying an expired lead's number is counted
        # in both places here; `--yes` deletes it once. Only possible while KEEP_RAW_PAYLOADS=true.
        raw_events = count_expired_raw_events(db_path, raw_cutoff)
        notifications = count_orphan_notifications(db_path)
        for lead, _segment in due:
            footprint = store.lead_footprint(lead.lead_id, lead_phone_digits(lead),
                                             store.get_customer_id(lead.lead_id))
            raw_events += footprint["raw_events"]
            notifications += footprint["notifications"]
        counts = {"leads": len(due), "raw_events": raw_events, "notifications": notifications}
        _print_preview(now, args.older_than_days, args.raw_events_days, segments, **counts)
        print("dry run: nothing changed" if args.dry_run else "add --yes to execute")
        _finish(counts, csv_state="rewritten" if csv_enabled and due else "skipped",
                sinks_state=",".join(sink.name for sink in deletable) or "none")
        return EXIT_OK if args.dry_run else EXIT_NEEDS_YES

    leads = raw_events = notifications = 0
    sink_ok: dict[str, int] = {sink.name: 0 for sink in deletable}
    sink_failed: dict[str, int] = {sink.name: 0 for sink in deletable}
    failed = False
    for lead, _segment in due:
        outcome = forget_lead(store, deletable, lead)
        leads += outcome["counts"]["leads"]
        raw_events += outcome["counts"]["raw_events"]
        notifications += outcome["counts"]["notifications"]
        for state in outcome["sink_states"]:
            name, _, result = state.partition("=")
            tally = sink_failed if result == "failed" else sink_ok
            tally[name] = tally.get(name, 0) + 1
        failed = failed or outcome["failed"]
    raw_events += delete_expired_raw_events(db_path, raw_cutoff)
    notifications += delete_orphan_notifications(db_path)  # after the leads, so nothing is counted twice
    csv_state = "skipped"
    if csv_enabled and leads:
        CsvExportSink(store, settings.csv_export_path).export()  # one rewrite for the whole batch
        csv_state = "rewritten"
    sinks_state = ",".join(f"{name}=ok{sink_ok[name]}/failed{sink_failed[name]}" for name in sink_ok) or "none"
    _finish({"leads": leads, "raw_events": raw_events, "notifications": notifications},
            csv_state=csv_state, sinks_state=sinks_state)
    return EXIT_SINK_FAILED if failed else EXIT_OK


def _finish(counts: dict[str, int], *, csv_state: str, sinks_state: str) -> None:
    """The one log line and the fixed last line of stdout. Counts only - no lead id, no number."""
    log.info("retention finished", extra=dict(counts))
    print(f"retention leads={counts['leads']} raw_events={counts['raw_events']} "
          f"notifications={counts['notifications']} csv={csv_state} sinks={sinks_state}")


def main(argv: Sequence[str] | None = None) -> int:
    settings = get_settings()
    setup_logging(settings.log_level)
    return run(settings, argv)


if __name__ == "__main__":
    sys.exit(main())
