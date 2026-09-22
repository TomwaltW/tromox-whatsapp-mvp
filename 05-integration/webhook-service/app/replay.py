"""Operations helper: re-run what did not finish.

    python -m app.replay            # reprocess stored-but-unprocessed callbacks, retry failed notifications
    python -m app.replay --export   # additionally rewrite the CSV export

Safe to run at any time (everything is idempotent); suitable for a cron job.
"""
from __future__ import annotations

import argparse
import json
import logging

from .config import get_settings
from .logging_setup import setup_logging
from .notify import build_notifiers
from .pipeline import Pipeline
from .store import CsvExportSink, SqliteStore, build_sinks

log = logging.getLogger("app.replay")


def replay(pipeline: Pipeline, max_attempts: int = 10) -> dict[str, int]:
    counts = {"events": 0, "notifications": 0}
    for event_key, payload_json in pipeline.store.unprocessed_events():
        result = pipeline.handle(json.loads(payload_json))
        counts["events"] += 1
        if result.notification_id is not None:
            pipeline.deliver(result.notification_id)
    for row in pipeline.store.retryable_notifications(max_attempts):
        pipeline.deliver(row.id)
        counts["notifications"] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export", action="store_true", help="rewrite the CSV export afterwards")
    parser.add_argument("--max-attempts", type=int, default=10)
    args = parser.parse_args()

    settings = get_settings()
    setup_logging(settings.log_level)
    store = SqliteStore(settings.database_path)
    pipeline = Pipeline(settings, store,
                        build_sinks(settings.storage_backend_list, store, settings.csv_export_path, settings=settings),
                        build_notifiers(settings))
    counts = replay(pipeline, args.max_attempts)
    for sink in pipeline.sinks:  # the CSV mirror coalesces a burst: write what replaying left pending
        flush = getattr(sink, "flush", None)
        if callable(flush):
            flush()
    if args.export:
        CsvExportSink(store, settings.csv_export_path).export()
    log.info("replay finished: %s", counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
