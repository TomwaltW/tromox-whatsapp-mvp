"""CSV mirror of the lead table - the "light lead library" the sales team can open directly.

The whole file is rewritten from SQLite and swapped in atomically, so a reader never sees a
half-written file. Rewriting on *every* callback costs O(leads) each time, so a burst of n new
leads costs O(n^2) (the load test measured p95 2.3 s at n=500 / concurrency 100). Hence
write-behind: a single callback is still written immediately, a burst inside
`min_interval_s` is coalesced into one rewrite, and whatever is still pending is written by
`flush()` (the service calls it on shutdown, `app.replay` after replaying).
"""
from __future__ import annotations

import csv
import json
import logging
import os
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tromox_lead import LEAD_FIELDS, Lead

from .sqlite_store import SqliteStore

log = logging.getLogger(__name__)

DEFAULT_MIN_INTERVAL_S = 5.0


def lead_to_row(lead: Lead) -> dict[str, str]:
    data: dict[str, Any] = lead.model_dump(mode="json")
    row: dict[str, str] = {}
    for name in LEAD_FIELDS:
        value = data.get(name)
        if value is None:
            row[name] = ""
        elif isinstance(value, list):
            row[name] = ";".join(str(item) for item in value)
        elif isinstance(value, dict):
            row[name] = json.dumps(value, ensure_ascii=False, sort_keys=True)
        elif isinstance(value, bool):
            row[name] = "true" if value else "false"
        else:
            row[name] = str(value)
    return row


class CsvExportSink:
    name = "csv"
    remote = False   # a local file: writing it stays in the request path

    def __init__(self, store: SqliteStore, path: Path | str, *,
                 min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.store = store
        self.path = Path(path)
        self.min_interval_s = float(min_interval_s)
        self._clock = clock
        # re-entrant: upsert_lead / flush / the timer decide *and* export while holding it, so that
        # a burst of concurrent callbacks cannot all pass the "due" check and all rewrite the table.
        self._lock = threading.RLock()
        self._last_export: float | None = None
        self._dirty = False
        self._timer: threading.Timer | None = None

    def upsert_lead(self, lead: Lead) -> None:  # the argument is unused: we always export the full table
        with self._lock:
            now = self._clock()
            last = self._last_export
            if self.min_interval_s <= 0 or last is None or now - last >= self.min_interval_s:
                self.export()
                return
            # inside the interval: remember that the file is stale and make sure somebody writes it
            self._dirty = True
            if self._timer is None:
                timer = threading.Timer(max(0.0, self.min_interval_s - (now - last)), self._on_timer)
                timer.daemon = True  # never hold up interpreter shutdown; flush() is what guarantees the write
                self._timer = timer
                timer.start()

    def export(self) -> int:
        """Rewrite the whole file from SQLite, atomically. Always writes, whatever the interval says."""
        with self._lock:
            self._cancel_timer()
            self._dirty = False
            leads = self.store.list_leads()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle, tmp_name = tempfile.mkstemp(prefix=".leads-", suffix=".csv.tmp", dir=self.path.parent)
            try:
                # utf-8-sig so Excel opens Chinese summaries correctly
                with os.fdopen(handle, "w", encoding="utf-8-sig", newline="") as fh:
                    writer = csv.DictWriter(fh, fieldnames=list(LEAD_FIELDS))
                    writer.writeheader()
                    for lead in leads:
                        writer.writerow(lead_to_row(lead))
                os.replace(tmp_name, self.path)
            except BaseException:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
                raise
            self._last_export = self._clock()
        return len(leads)

    def flush(self) -> int:
        """Write what a burst left pending and drop the timer. Returns the rows written (0 if nothing was due)."""
        with self._lock:
            if self._dirty:
                return self.export()
            self._cancel_timer()
            return 0

    def close(self) -> int:
        return self.flush()

    def _cancel_timer(self) -> None:
        timer, self._timer = self._timer, None
        if timer is not None:
            timer.cancel()

    def _on_timer(self) -> None:
        with self._lock:
            if self._timer is threading.current_thread():  # a threading.Timer *is* the thread that runs this
                self._timer = None
            if not self._dirty:
                return
            try:
                self.export()
            except Exception:  # a background thread must not die silently, and must not kill the process
                log.exception("deferred CSV export failed; the mirror stays stale until the next callback")
