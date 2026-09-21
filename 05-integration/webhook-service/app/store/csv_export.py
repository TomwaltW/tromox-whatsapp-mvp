"""CSV mirror of the lead table - the "light lead library" the sales team can open directly.

The whole file is rewritten from SQLite on every change and swapped in atomically, so a
reader never sees a half-written file. Fine for MVP volumes (thousands of leads).
"""
from __future__ import annotations

import csv
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from tromox_lead import LEAD_FIELDS, Lead

from .sqlite_store import SqliteStore


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

    def __init__(self, store: SqliteStore, path: Path | str) -> None:
        self.store = store
        self.path = Path(path)
        self._lock = threading.Lock()

    def upsert_lead(self, lead: Lead) -> None:  # the argument is unused: we always export the full table
        self.export()

    def export(self) -> int:
        leads = self.store.list_leads()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
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
        return len(leads)
