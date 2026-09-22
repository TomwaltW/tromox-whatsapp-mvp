"""UAT record sheet generator: three sheets, fixed header, 20 cases in md order, replay expectation column, md untouched."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl", reason="needs the cost extra: uv pip install -e '.[cost]'")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gen_uat_sheet.py"
MD = ROOT / "06-acceptance" / "uat-test-cases.md"
MANIFEST = ROOT / "05-integration" / "webhook-service" / "fixtures" / "uat" / "manifest.json"

spec = importlib.util.spec_from_file_location("gen_uat_sheet", SCRIPT)
gen = importlib.util.module_from_spec(spec)
sys.modules["gen_uat_sheet"] = gen
spec.loader.exec_module(gen)  # type: ignore[union-attr]


@pytest.fixture(scope="module")
def workbook(tmp_path_factory):
    out = tmp_path_factory.mktemp("uat") / "nested" / "uat-record.xlsx"
    before = MD.read_bytes()
    rc = gen.main(["--out", str(out), "--date", "2026-10-30"])
    assert rc == 0
    assert MD.read_bytes() == before, "the md requirement source must not be written back"
    return openpyxl.load_workbook(out)


def test_three_sheets_and_fixed_header(workbook):
    assert workbook.sheetnames == ["用例", "语种安排", "说明"]
    ws = workbook["用例"]
    assert [c.value for c in ws[1]] == gen.CASE_HEADER
    assert ws.freeze_panes == "A2"
    assert [dv.sqref for dv in ws.data_validations.dataValidation] and \
        str(ws.data_validations.dataValidation[0].sqref) == "J2:J21"


def test_twenty_cases_in_md_order_with_site_columns_blank(workbook):
    ws = workbook["用例"]
    rows = [[c.value for c in row] for row in ws.iter_rows(min_row=2) if row[0].value]
    assert [r[0] for r in rows] == [f"U{i:02d}" for i in range(1, 21)]
    md_rows = gen.parse_cases(MD.read_text(encoding="utf-8"))
    assert [r[:8] for r in rows] == md_rows
    assert all(v in (None, "") for r in rows for v in r[9:15])


def test_u03_replay_expectation_from_manifest(workbook):
    ws = workbook["用例"]
    svc = {row[0].value: row[8].value for row in ws.iter_rows(min_row=2) if row[0].value}
    assert "lead.escalation_reason=b2b_qualified" in svc["U03"]
    assert "notifications=1" in svc["U03"]
    expect = json.loads(MANIFEST.read_text(encoding="utf-8"))["cases"]["U03"]["expect"]
    assert svc["U03"] == gen.render_expect(expect)
    # list of objects is indexed, scalar list joined with commas
    assert "lead[0].source_code=TT-2610B" in svc["U15"]
    assert "lead.product_interest=MC10,UKKO" in svc["U01"]


def test_language_and_notes_sheets(workbook):
    lang = [[c.value for c in row] for row in workbook["语种安排"].iter_rows()]
    assert lang[0] == ["语种", "完整版用例", "精简版"]
    assert len(lang) == 7 and lang[-1][0] == "系统"
    notes = [row[0].value for row in workbook["说明"].iter_rows()]
    assert notes[0].startswith("1. ") and notes[4].startswith("5. ")
    assert notes[-2] == "生成自：06-acceptance/uat-test-cases.md + fixtures/uat/manifest.json"
    assert notes[-1].startswith("生成日期：2026-10-30　命令：python scripts/gen_uat_sheet.py --out ")


def test_markdown_cell_semantics():
    row = gen.split_row("| U99 | a<br>b | `code` x | left \\| right |")
    assert row == ["U99", "a\nb", "code x", "left | right"]


def test_render_expect_scalars():
    assert gen.render_expect({"lead": {"flag": True, "x": None}, "tags": [], "priority": ""}) == \
        "lead.flag=true; lead.x=null; tags=; priority="


def test_exit_2_when_case_count_or_manifest_is_off(tmp_path):
    text = MD.read_text(encoding="utf-8")
    short_md = tmp_path / "cases.md"
    short_md.write_text(text.replace("| U20 |", "| X20 |"), encoding="utf-8")
    assert gen.main(["--out", str(tmp_path / "a.xlsx"), "--cases-md", str(short_md)]) == 2
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    del manifest["cases"]["U07"]
    thin = tmp_path / "manifest.json"
    thin.write_text(json.dumps(manifest), encoding="utf-8")
    assert gen.main(["--out", str(tmp_path / "b.xlsx"), "--manifest", str(thin)]) == 2
