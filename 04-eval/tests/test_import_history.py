"""python -m eval.import_history: client export (any column names) -> labelling CSV. Fixtures are fictional."""
from __future__ import annotations

import csv
import datetime
import re
from pathlib import Path

import openpyxl
import pytest

from eval.import_history import (
    EXIT_NO_TEXT_COLUMN,
    EXIT_OK,
    ColumnMap,
    ImportError_,
    convert,
    detect_columns,
    main,
    scrub_text,
)
from tromox_lead import LABEL_COLUMNS

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CN_CSV = FIXTURES / "history-export-cn.csv"
EN_CSV = FIXTURES / "history-export-en.csv"
LABEL_ONLY = ("segment", "b2b_type", "b2c_intent", "country_gold", "product_interest",
              "escalation_flag", "escalation_reason", "is_valid_lead", "annotator")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
DIGITS_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")


def read_out(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def summary_of(stdout: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in stdout.strip().splitlines())


def make_xlsx(path: Path, header: list[str], rows: list[list[object]], *, sheet: str | None = None,
              extra_first_sheet: bool = False) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    if extra_first_sheet:                       # a decoy first sheet, so --sheet must pick the right one
        ws.title = "Summary"
        ws.append(["nothing", "here"])
        ws = wb.create_sheet(sheet or "Export")
    elif sheet:
        ws.title = sheet
    ws.append(header)
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def test_chinese_csv_autodetect_header_ids_phones_language(tmp_path, capsys):
    out = tmp_path / "batch.csv"
    assert main(["--input", str(CN_CSV), "--out", str(out)]) == EXIT_OK
    header, rows = read_out(out)
    assert header == list(LABEL_COLUMNS)
    assert len(rows) == 5                                      # 7 data rows - 1 empty - 1 duplicate
    ids = [r["sample_id"] for r in rows]
    assert len(set(ids)) == 5 and all(re.fullmatch(r"H-[0-9a-f]{8}", i) for i in ids)
    assert all(r["data_origin"] == "real" for r in rows)
    assert [r["phone"] for r in rows] == ["+4915123456789", "+34612345678", "+61412345678", "", "+5511912345678"]
    assert [r["language"] for r in rows] == ["de", "es", "en", "fr", "pt"]
    assert all(r[c] == "" for r in rows for c in LABEL_ONLY)
    assert rows[0]["label_notes"] == "来源:Instagram;日期:2026-08-01 10:00"
    assert rows[3]["label_notes"] == "日期:2026-08-05 09:00"       # no channel -> only the date
    assert "[IG-2609]" in rows[4]["conversation_text"]             # short source codes survive scrubbing
    summary = summary_of(capsys.readouterr().out)
    assert summary == {"rows_in": "7", "rows_out": "5", "dropped_empty": "1", "dropped_duplicate": "1",
                       "languages": "de:1,en:1,es:1,fr:1,pt:1", "countries": "AU:1,BR:1,DE:1,ES:1,unknown:1"}


def test_scrubbing_masks_email_and_long_digits_and_collapses_whitespace(tmp_path):
    out = tmp_path / "batch.csv"
    assert main(["--input", str(CN_CSV), "--out", str(out)]) == EXIT_OK
    _, rows = read_out(out)
    joined = " ".join(r["conversation_text"] for r in rows)
    assert not EMAIL_RE.search(joined) and not DIGITS_RE.search(joined)
    assert rows[0]["conversation_text"].endswith("Schreiben Sie an <email> oder rufen Sie <number> an.")
    assert "Order <number> was late." in rows[2]["conversation_text"]
    assert rows[1]["conversation_text"] == "Hola, quiero comprar una moto eléctrica para mí."   # double spaces gone
    assert scrub_text("  a\t\tb \n c ") == "a b c"
    assert scrub_text("MC10 costs 1200 EUR") == "MC10 costs 1200 EUR"                          # short numbers stay


def test_dedupe_is_stable_and_ignores_whitespace_differences():
    rows = [{"t": "Hallo  Welt", "p": "+49 151 2345 6789"}, {"t": "Hallo Welt", "p": "4915123456789"},
            {"t": "Hallo Welt", "p": "+34612345678"}]
    columns = ColumnMap(text="t", phone="p", date=None, channel=None)
    out, summary = convert(rows, columns)
    assert [r["conversation_text"] for r in out] == ["Hallo Welt", "Hallo Welt"]
    assert summary.dropped_duplicate == 1 and summary.rows_out == 2
    again, _ = convert(rows, columns)
    assert [r["sample_id"] for r in again] == [r["sample_id"] for r in out]   # same input -> same ids
    assert out[0]["sample_id"] != out[1]["sample_id"]                          # same text, other number


def test_explicit_columns_override_autodetect(tmp_path, capsys):
    src = tmp_path / "odd.csv"
    src.write_text("a,b,c,d\n"
                   "+34612345678,\"Hola, quiero una moto\",2026-08-01,instagram\n"
                   "+4915123456789,\"Hallo, ich bin Händler\",2026-08-02,facebook\n", encoding="utf-8")
    out = tmp_path / "batch.csv"
    assert main(["--input", str(src), "--out", str(out), "--text-col", "b", "--phone-col", "a",
                 "--date-col", "c", "--channel-col", "d", "--data-origin", "synthetic"]) == EXIT_OK
    _, rows = read_out(out)
    assert [r["phone"] for r in rows] == ["+34612345678", "+4915123456789"]
    assert rows[0]["label_notes"] == "来源:instagram;日期:2026-08-01"
    assert all(r["data_origin"] == "synthetic" for r in rows)
    assert summary_of(capsys.readouterr().out)["rows_out"] == "2"
    with pytest.raises(ImportError_, match="not a column"):
        detect_columns(["a", "b"], text="zzz")


def test_autodetect_claims_columns_in_order_and_skips_reply_column():
    columns = detect_columns(["Date", "Customer Phone", "Message Text", "Channel", "Agent Reply"])
    assert columns == ColumnMap(text="Message Text", phone="Customer Phone", date="Date", channel="Channel")
    columns = detect_columns(["序号", "时间", "WhatsApp 号码", "客户消息", "来源", "备注"])
    assert columns == ColumnMap(text="客户消息", phone="WhatsApp 号码", date="时间", channel="来源")
    columns = detect_columns(["conversation"])
    assert columns == ColumnMap(text="conversation", phone=None, date=None, channel=None)


def test_missing_text_column_exits_2_and_lists_header(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    bad.write_text("id,score\n1,2\n", encoding="utf-8")
    out = tmp_path / "never.csv"
    assert main(["--input", str(bad), "--out", str(out)]) == EXIT_NO_TEXT_COLUMN
    err = capsys.readouterr().err
    assert "id, score" in err and "--text-col" in err
    assert not out.exists()


def test_english_xlsx_with_sheet_and_limit(tmp_path, capsys):
    header, rows = read_out(EN_CSV)
    data = [[r[h] for h in header] for r in rows]
    data[0][1] = 4915123456789                                    # numeric phone cell, as Excel often stores it
    data[0][0] = datetime.datetime(2026, 8, 10, 9, 30)            # real date cell -> "2026-08-10 09:30:00"
    data[1][4] = datetime.time(9, 31)                             # time-only cell in an unclaimed column must not crash
    src = make_xlsx(tmp_path / "export.xlsx", header, data, sheet="Export", extra_first_sheet=True)
    out = tmp_path / "batch.csv"
    assert main(["--input", str(src), "--out", str(out), "--sheet", "Export", "--limit", "2"]) == EXIT_OK
    got_header, got = read_out(out)
    assert got_header == list(LABEL_COLUMNS) and len(got) == 2
    assert got[0]["phone"] == "+4915123456789" and got[0]["language"] == "de"
    assert got[0]["label_notes"] == "来源:instagram;日期:2026-08-10 09:30:00"
    assert got[1]["phone"] == "+393331234567" and got[1]["language"] == "it"
    summary = summary_of(capsys.readouterr().out)
    assert summary["rows_in"] == "4" and summary["rows_out"] == "2" and summary["countries"] == "DE:1,IT:1"
    # without --sheet the decoy first sheet has no text column -> exit 2
    assert main(["--input", str(src), "--out", str(tmp_path / "x.csv")]) == EXIT_NO_TEXT_COLUMN
    assert "nothing, here" in capsys.readouterr().err


def test_english_csv_and_bom_are_read(tmp_path):
    src = tmp_path / "bom.csv"
    src.write_bytes(b"\xef\xbb\xbf" + EN_CSV.read_bytes())
    out = tmp_path / "batch.csv"
    assert main(["--input", str(src), "--out", str(out)]) == EXIT_OK
    _, rows = read_out(out)
    assert len(rows) == 4
    # the shared digits mask starts at the first digit, so a leading "(" survives - same as report.excerpt()
    assert rows[2]["conversation_text"] == "Do you ship to New York? Contact me at <email> or (<number>."
    assert [r["phone"] for r in rows] == ["+4915123456789", "+393331234567", "+17185550123", "+12025550101"]


def test_check_only_validates_template_header(tmp_path, capsys):
    out = tmp_path / "not-written.csv"
    assert main(["--input", str(CN_CSV), "--out", str(out), "--check"]) == EXIT_OK
    assert "header=OK" in capsys.readouterr().out
    assert not out.exists()
