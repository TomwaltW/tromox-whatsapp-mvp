"""Deletion request: erase one contact everywhere this service keeps personal data.

    python -m app.forget (--phone +E164 | --lead-id L-…) [--dry-run] [--yes]

What one run removes, in this order:
    1. ledger (SQLite): the `leads` row, its `notifications` rows, and every stored raw callback
       (`raw_events.payload_json`, kept only while KEEP_RAW_PAYLOADS=true) that contains the phone
       digits or the platform customer id. `processed_events` stays: event keys carry no personal
       data and keep a redelivered callback idempotent.
    2. CSV export: rewritten from the ledger when `csv` is in STORAGE_BACKENDS.
    3. every other sink from STORAGE_BACKENDS that offers `delete_lead` (Feishu Bitable today).

Exit codes:  0 done (or --dry-run)   1 a sink failed / configuration error   2 lead not found
             3 neither --dry-run nor --yes: the preview was printed, nothing changed.
A sink failure never rolls the ledger back: the row is gone, the failure is logged, rerun the command
to retry the mirror. Backups are outside this command (they expire on their own retention).

Output rule: neither stdout nor the log ever contains the phone number; only the `lead_id`.
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Sequence

from tromox_lead import Lead, normalize_e164

from .config import Settings, get_settings
from .logging_setup import setup_logging
from .store import CsvExportSink, LeadSink, SqliteStore, build_sinks

log = logging.getLogger("app.forget")

EXIT_OK, EXIT_SINK_FAILED, EXIT_NOT_FOUND, EXIT_NEEDS_YES = 0, 1, 2, 3


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m app.forget", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    who = parser.add_mutually_exclusive_group(required=True)
    who.add_argument("--phone", help="E.164 phone number of the contact, e.g. +4915112345678")
    who.add_argument("--lead-id", help="lead id (L-…) as shown in cards, CSV and logs")
    parser.add_argument("--dry-run", action="store_true", help="only print what would be deleted")
    parser.add_argument("--yes", action="store_true", help="actually delete")
    return parser.parse_args(argv)


def _find_lead(store: SqliteStore, phone: str | None, lead_id: str | None) -> Lead | None:
    if lead_id:
        return store.get_lead(lead_id.strip())
    normalized = normalize_e164(phone)
    return store.get_lead_by_phone(normalized) if normalized else None


def _print_preview(lead_id: str, counts: dict[str, int], csv_enabled: bool, csv_path, sink_names: list[str]) -> None:
    print(f"lead_id={lead_id}")
    print(f"  leads:         {counts['leads']}")
    print(f"  notifications: {counts['notifications']}")
    print(f"  raw_events:    {counts['raw_events']}")
    print(f"  csv:           {'rewrite ' + str(csv_path) if csv_enabled else 'skipped (csv not in STORAGE_BACKENDS)'}")
    print(f"  sinks:         {', '.join(sink_names) if sink_names else 'none'}")


def run(settings: Settings, argv: Sequence[str] | None = None) -> int:
    """The command with an injected `Settings` (tests call this directly). Returns the exit code."""
    args = _parse_args(argv)
    store = SqliteStore(settings.database_path)
    backends = settings.storage_backend_list
    try:  # a half-configured sink is a configuration error: stop before touching anything
        sinks: list[LeadSink] = build_sinks(backends, store, settings.csv_export_path, settings=settings)
    except ValueError as exc:
        print(f"configuration error: {exc}")
        return EXIT_SINK_FAILED
    deletable = [sink for sink in sinks if callable(getattr(sink, "delete_lead", None))]

    lead = _find_lead(store, args.phone, args.lead_id)
    if lead is None:
        print("not found")
        return EXIT_NOT_FOUND
    lead_id = lead.lead_id
    phone_digits = "".join(ch for ch in (lead.phone or "") if ch.isdigit()) or None
    customer_id = store.get_customer_id(lead_id)
    csv_enabled = "csv" in backends

    if not args.yes:
        counts = store.lead_footprint(lead_id, phone_digits, customer_id)
        _print_preview(lead_id, counts, csv_enabled, settings.csv_export_path, [s.name for s in deletable])
        if args.dry_run:
            print("dry run: nothing changed")
            return EXIT_OK
        print("add --yes to execute")
        return EXIT_NEEDS_YES

    counts = store.delete_lead(lead_id, phone_digits, customer_id)
    csv_state = "skipped"
    if csv_enabled:
        CsvExportSink(store, settings.csv_export_path).export()
        csv_state = "rewritten"
    sink_states: list[str] = []
    failed = False
    for sink in deletable:
        try:
            deleted = bool(sink.delete_lead(lead_id))  # type: ignore[attr-defined]
        except Exception as exc:  # the ledger row is already gone; report and continue with the next mirror
            failed = True
            sink_states.append(f"{sink.name}=failed")
            log.error("sink delete failed: %s", exc,
                      extra={"channel": sink.name, "lead_id": lead_id, "error_type": type(exc).__name__})
        else:
            sink_states.append(f"{sink.name}={'deleted' if deleted else 'absent'}")
    log.info("lead forgotten: leads=%d notifications=%d raw_events=%d", counts["leads"], counts["notifications"],
             counts["raw_events"], extra={"lead_id": lead_id, **counts})
    print(f"forgotten lead_id={lead_id} leads={counts['leads']} notifications={counts['notifications']} "
          f"raw_events={counts['raw_events']} csv={csv_state} sinks={','.join(sink_states) if sink_states else 'none'}")
    return EXIT_SINK_FAILED if failed else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    settings = get_settings()
    setup_logging(settings.log_level)
    return run(settings, argv)


if __name__ == "__main__":
    sys.exit(main())
