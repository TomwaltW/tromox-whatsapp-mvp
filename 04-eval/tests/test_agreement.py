"""python -m eval.agreement: two labelling files -> per-column agreement, Cohen's κ, disagreements, threshold exit code.

Fixtures under tests/fixtures/agreement-*.csv are fictional (names, numbers, e-mails all made up).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from eval.agreement import EXIT_INPUT_ERROR, EXIT_LOW, EXIT_OK, cohen_kappa, main, normalize
from tromox_lead import LABEL_COLUMNS

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FILE_A = FIXTURES / "agreement-a.csv"
FILE_B = FIXTURES / "agreement-b.csv"


def write(path: Path, rows: list[dict[str, str]], header: list[str] | None = None) -> Path:
    fields = header or list(LABEL_COLUMNS)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    return path


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def last_line(capsys: pytest.CaptureFixture[str]) -> str:
    return capsys.readouterr().out.strip().splitlines()[-1]


def test_identical_files_pass_with_kappa_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rows = [r for r in read(FILE_A) if r["data_origin"] == "real"]
    copy = write(tmp_path / "copy.csv", rows)
    summary = tmp_path / "s.json"
    assert main(["--a", str(FILE_A), "--b", str(copy), "--json", str(summary)]) == EXIT_OK
    tail = last_line(capsys)
    assert tail == "common=10 segment=1.00 escalation_flag=1.00 kappa_segment=1.00 result=OK"
    data = json.loads(summary.read_text(encoding="utf-8"))
    assert data["result"] == "OK" and data["common"] == 10 and data["disagreements"] == []
    assert data["columns"]["segment"] == {"n": 10, "agree": 10, "agreement": 1.0, "kappa": 1.0}
    assert data["columns"]["escalation_flag"]["kappa"] == 1.0


def test_disagreements_below_threshold_exit_3_and_are_listed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report, summary = tmp_path / "r.md", tmp_path / "s.json"
    rc = main(["--a", str(FILE_A), "--b", str(FILE_B), "--out", str(report), "--json", str(summary)])
    assert rc == EXIT_LOW
    assert last_line(capsys) == "common=7 segment=0.86 escalation_flag=0.86 kappa_segment=0.75 result=LOW"
    data = json.loads(summary.read_text(encoding="utf-8"))
    assert data["min_agreement"] == 0.9 and data["result"] == "LOW"
    assert [(d["sample_id"], d["column"], d["a"], d["b"]) for d in data["disagreements"]] == [
        ("AG-05", "escalation_flag", "true", "false"),
        ("AG-05", "escalation_reason", "complaint", "other"),
        ("AG-08", "segment", "unknown", "b2c"),
    ]
    text = report.read_text(encoding="utf-8")
    for heading in ("# 标注一致性", "## 1. 概览", "## 2. 逐列一致率", "## 3. 分歧清单"):
        assert heading in text
    assert "| AG-08 | `segment` | unknown | b2c |" in text
    assert "@example.com" not in text and "跳过模板示例行 1 行" in text   # example row in A is ignored
    # the same pair passes once the threshold is lowered; the summary line is still the last stdout line
    assert main(["--a", str(FILE_A), "--b", str(FILE_B), "--min-agreement", "0.8"]) == EXIT_OK
    assert last_line(capsys).endswith("result=OK")


def test_header_mismatch_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = write(tmp_path / "bad.csv", [{"sample_id": "AG-01", "segment": "B2B"}], header=["sample_id", "segment"])
    assert main(["--a", str(FILE_A), "--b", str(bad)]) == EXIT_INPUT_ERROR
    err = capsys.readouterr().err
    assert "LABEL_COLUMNS" in err and "expected:" in err
    # unknown --columns entry is an input error too
    assert main(["--a", str(FILE_A), "--b", str(FILE_B), "--columns", "segment,nope"]) == EXIT_INPUT_ERROR
    assert "nope" in capsys.readouterr().err


def test_empty_intersection_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rows = [dict(r, sample_id=f"X-{i}") for i, r in enumerate(read(FILE_A)) if r["data_origin"] == "real"]
    disjoint = write(tmp_path / "disjoint.csv", rows)
    assert main(["--a", str(FILE_A), "--b", str(disjoint)]) == EXIT_INPUT_ERROR
    assert "no common sample_id" in capsys.readouterr().err


def test_boolean_and_case_normalisation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert normalize("escalation_flag", "是") == normalize("escalation_flag", " TRUE ") == "true"
    assert normalize("is_valid_lead", "否") == normalize("is_valid_lead", "") == normalize("is_valid_lead", "no") == "false"
    assert normalize("segment", " B2B ") == "b2b" and normalize("segment", "") == ""
    rows_a = [r for r in read(FILE_A) if r["data_origin"] == "real"][:4]
    rows_b = [dict(r, escalation_flag="是" if r["escalation_flag"] == "true" else "否",
                   is_valid_lead="1" if r["is_valid_lead"] == "yes" else "0",
                   segment=r["segment"].lower() + " ") for r in rows_a]
    a, b = write(tmp_path / "a.csv", rows_a), write(tmp_path / "b.csv", rows_b)
    summary = tmp_path / "s.json"
    assert main(["--a", str(a), "--b", str(b), "--json", str(summary)]) == EXIT_OK
    assert last_line(capsys) == "common=4 segment=1.00 escalation_flag=1.00 kappa_segment=1.00 result=OK"
    cols = json.loads(summary.read_text(encoding="utf-8"))["columns"]
    assert cols["is_valid_lead"]["agree"] == 4 and cols["escalation_flag"]["agree"] == 4


def test_cohen_kappa_edge_cases() -> None:
    assert cohen_kappa([]) is None
    assert cohen_kappa([("b2b", "b2b"), ("b2b", "b2b")]) is None            # single category -> undefined
    assert cohen_kappa([("b2b", "b2b"), ("b2c", "b2c")]) == pytest.approx(1.0)
    assert cohen_kappa([("b2b", "b2c"), ("b2c", "b2b")]) == pytest.approx(-1.0)
    # textbook example: po = 0.7, pe = 0.5 -> kappa 0.4
    pairs = [("x", "x")] * 35 + [("y", "y")] * 35 + [("x", "y")] * 15 + [("y", "x")] * 15
    assert cohen_kappa(pairs) == pytest.approx(0.4)
