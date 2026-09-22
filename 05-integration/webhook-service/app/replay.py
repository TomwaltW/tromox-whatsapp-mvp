"""Operations helper: re-run what did not finish.

    python -m app.replay            # reprocess stored-but-unprocessed callbacks, retry failed notifications,
                                    # retry the mirrors that never reached a remote sink
    python -m app.replay --export   # additionally rewrite the CSV export
    python -m app.replay --reset-mirrors   # first give up-to-attempts mirrors a fresh retry budget

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


def replay(pipeline: Pipeline, max_attempts: int = 10, reset_mirrors: bool = False) -> dict[str, int]:
    counts = {"events": 0, "notifications": 0, "mirrors": 0, "mirrors_reset": 0}
    for event_key, payload_json in pipeline.store.unprocessed_events():
        result = pipeline.handle(json.loads(payload_json))
        counts["events"] += 1
        if result.notification_id is not None:
            pipeline.deliver(result.notification_id)
    for row in pipeline.store.retryable_notifications(max_attempts):
        pipeline.deliver(row.id)
        counts["notifications"] += 1
    if reset_mirrors:  # manual: the rows below used up their retry budget, give them a fresh one first
        counts["mirrors_reset"] = pipeline.store.reset_exhausted_mirrors(max_attempts)
    # `mirror()` takes a lead and sends every pending row it has, so visit each lead once
    for lead_id in dict.fromkeys(row.lead_id for row in pipeline.store.pending_mirrors(max_attempts=max_attempts)):
        pipeline.mirror(lead_id)
        counts["mirrors"] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export", action="store_true", help="rewrite the CSV export afterwards")
    parser.add_argument("--max-attempts", type=int, default=10)
    parser.add_argument("--reset-mirrors", action="store_true",
                        help="把用满 --max-attempts 次重试、已不再自动重试的镜像行 attempts 归零后再重试；"
                             "先看过 last_error、原因已排除再用，否则只会再白烧一轮重试预算")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging(settings.log_level)
    store = SqliteStore(settings.database_path)
    pipeline = Pipeline(settings, store,
                        build_sinks(settings.storage_backend_list, store, settings.csv_export_path, settings=settings),
                        build_notifiers(settings))
    counts = replay(pipeline, args.max_attempts, reset_mirrors=args.reset_mirrors)
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
