"""STUB - Google Sheets sink. NOT implemented in the MVP.

Reserved so the interface is stable. Selecting `gsheets` in STORAGE_BACKENDS fails fast at
start-up instead of silently dropping leads.

Planned mapping: one row per lead, columns in `tromox_lead.LEAD_FIELDS` order (same layout
as the CSV export, see `csv_export.lead_to_row`): lists joined with ';', referral as a JSON
string, booleans as true/false, datetimes as ISO 8601 UTC. Column A (lead_id) is the upsert
key. Implementation notes for phase 2: service-account credentials via env, batch updates,
keep SQLite as the ledger and treat the sheet as a mirror only.
"""
from __future__ import annotations

from tromox_lead import Lead


class GoogleSheetsSink:
    name = "gsheets"
    remote = True   # the Sheets API is a network hop: it would go through mirror_outbox as well

    def __init__(self) -> None:
        raise NotImplementedError(
            "gsheets storage is a documented stub (phase 2). Use STORAGE_BACKENDS=sqlite,csv."
        )

    def upsert_lead(self, lead: Lead) -> None:  # pragma: no cover - unreachable
        raise NotImplementedError
