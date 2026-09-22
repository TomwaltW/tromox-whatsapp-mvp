"""Deletion request: erase one contact everywhere this service keeps personal data.

    python -m app.forget (--phone +E164 | --lead-id L-…) [--dry-run] [--yes]

What one run removes, in this order:
    1. ledger (SQLite): the `leads` row, its `notifications` rows, and every stored raw callback
       (`raw_events.payload_json`, kept only while KEEP_RAW_PAYLOADS=true) that contains the phone
       digits or the platform customer id. `processed_events` stays: event keys carry no personal
       data and keep a redelivered callback idempotent.
    2. every other sink from STORAGE_BACKENDS that offers `delete_lead` (Feishu Bitable today).
    3. CSV export: rewritten from the ledger when `csv` is in STORAGE_BACKENDS.

Steps 1 and 2 are `forget_lead()`, which `app.retention` reuses for every expired lead; step 3 is a
full rewrite of the table, so each command does it once per run rather than once per lead.

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


def lead_phone_digits(lead: Lead) -> str | None:
    """The digits of the lead's phone (no '+'), as stored inside raw callback payloads."""
    return "".join(ch for ch in (lead.phone or "") if ch.isdigit()) or None


def forget_lead(store: SqliteStore, sinks: Sequence[LeadSink], lead: Lead) -> dict:
    """Erase one lead from the ledger and from every mirror that offers `delete_lead`.

    Shared by `app.forget` (one contact on request) and `app.retention` (every expired lead).
    The CSV mirror is deliberately *not* rewritten here - it is a full rewrite of the table, so
    the caller does it once per run instead of once per lead. A sink failure is logged and
    reported, never raised: the ledger row is already gone and the other mirrors must still be
    tried. Returns `{"counts": <rows removed per table>, "sink_states": [...], "failed": bool}`.
    """
    lead_id = lead.lead_id
    customer_id = store.get_customer_id(lead_id)  # read it before the row goes away
    counts = store.delete_lead(lead_id, lead_phone_digits(lead), customer_id)
    sink_states: list[str] = []
    failed = False
    for sink in sinks:
        try:
            deleted = bool(sink.delete_lead(lead_id))  # type: ignore[attr-defined]
        except Exception as exc:  # the ledger row is already gone; report and continue with the next mirror
            failed = True
            sink_states.append(f"{sink.name}=failed")
            log.error("sink delete failed: %s", exc,
                      extra={"channel": sink.name, "lead_id": lead_id, "error_type": type(exc).__name__})
        else:
            sink_states.append(f"{sink.name}={'deleted' if deleted else 'absent'}")
    return {"counts": counts, "sink_states": sink_states, "failed": failed}


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
    csv_enabled = "csv" in backends

    if not args.yes:
        counts = store.lead_footprint(lead_id, lead_phone_digits(lead), store.get_customer_id(lead_id))
        _print_preview(lead_id, counts, csv_enabled, settings.csv_export_path, [s.name for s in deletable])
        if args.dry_run:
            print("dry run: nothing changed")
            return EXIT_OK
        print("add --yes to execute")
        return EXIT_NEEDS_YES

    outcome = forget_lead(store, deletable, lead)
    counts, sink_states, failed = outcome["counts"], outcome["sink_states"], outcome["failed"]
    csv_state = "skipped"
    if csv_enabled:
        CsvExportSink(store, settings.csv_export_path).export()
        csv_state = "rewritten"
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
