"""Helpers shared by the eval tests (kept out of conftest.py so the module name is unique)."""
from __future__ import annotations

from pathlib import Path

from tromox_lead import LABEL_COLUMNS


def make_row(**overrides: str) -> dict[str, str]:
    row = {
        "sample_id": "T-001", "data_origin": "real", "phone": "+4917604069031",
        "conversation_text": "Hallo, wir möchten Händler werden.", "language": "de", "segment": "B2B",
        "b2b_type": "dealer", "b2c_intent": "", "country_gold": "DE", "product_interest": "",
        "escalation_flag": "false", "escalation_reason": "", "is_valid_lead": "yes",
        "annotator": "tester", "label_notes": "",
    }
    row.update(overrides)
    assert tuple(row) == LABEL_COLUMNS
    return row


def write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    import csv

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(LABEL_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    return path
