"""Trial sample kit generator: CSV loadable by eval.data, xlsx with three sheets, plan md untouched."""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl", reason="needs the cost extra: uv pip install -e '.[cost]'")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gen_trial_kit.py"
PLAN = ROOT / "02-botmaker" / "trial-test-plan.md"
if str(ROOT / "04-eval") not in sys.path:
    sys.path.insert(0, str(ROOT / "04-eval"))
from tromox_lead import LABEL_COLUMNS  # noqa: E402

spec = importlib.util.spec_from_file_location("gen_trial_kit", SCRIPT)
gen = importlib.util.module_from_spec(spec)
sys.modules["gen_trial_kit"] = gen
spec.loader.exec_module(gen)  # type: ignore[union-attr]


@pytest.fixture(scope="module")
def kit(tmp_path_factory):
    out = tmp_path_factory.mktemp("trial") / "nested" / "kit"
    before = PLAN.read_bytes()
    rc = gen.main(["--out-dir", str(out), "--date", "2026-10-12"])
    assert rc == 0
    assert PLAN.read_bytes() == before, "the plan md is the requirement source and must not be written back"
    return out


@pytest.fixture(scope="module")
def rows(kit):
    with (kit / "trial-samples.csv").open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def test_csv_header_and_twenty_rows(rows):
    header, body = rows
    assert header == list(LABEL_COLUMNS)
    assert [r["sample_id"] for r in body] == [f"S-{i:02d}" for i in range(1, 21)]
    assert {r["data_origin"] for r in body} == {"example"}
    assert {r["annotator"] for r in body} == {"trial-plan"}
    assert all(r["phone"] == "" and r["is_valid_lead"] == "" for r in body)


def test_csv_values_follow_the_plan(rows):
    by = {r["sample_id"]: r for r in rows[1]}
    assert by["S-01"]["language"] == "en" and by["S-01"]["country_gold"] == "GB" and by["S-01"]["b2b_type"] == "dealer"
    # 多轮：去掉"第 n 条："前缀，用 " / " 连接
    assert by["S-02"]["conversation_text"].startswith("Hello, I'd like to distribute") and " / Company is Fjordline" in by["S-02"]["conversation_text"]
    assert "第 1 条" not in by["S-02"]["conversation_text"]
    # 只说城市 -> country_gold 空；产品代码
    assert by["S-03"]["country_gold"] == "" and by["S-03"]["product_interest"] == "UKKO" and by["S-03"]["b2c_intent"] == "buy"
    assert by["S-07"]["product_interest"] == "MC10;PESGO"
    # escalation 拆分
    assert by["S-04"]["segment"] == "unknown" and by["S-04"]["escalation_flag"] == "true" and by["S-04"]["escalation_reason"] == "human_requested"
    assert by["S-08"]["escalation_flag"] == "false" and by["S-08"]["escalation_reason"] == ""
    # 多值期望：取第一个具名值，原文进 label_notes
    assert by["S-05"]["b2c_intent"] == "support" and "期望取值:support 或 warranty 均可→support" in by["S-05"]["label_notes"]
    assert by["S-20"]["b2b_type"] == "other" and "期望取值:任意或空→other" in by["S-20"]["label_notes"]
    assert by["S-10"]["label_notes"] == "进入方式:按钮 Rider or Customer，再按 Test ride;备注:只说城市"
    # b2b_type / b2c_intent 按 segment 分列
    assert all((r["b2b_type"] == "") == (r["segment"] != "B2B") for r in rows[1])
    assert all((r["b2c_intent"] == "") == (r["segment"] != "B2C") for r in rows[1])


def test_csv_loads_through_eval_data_with_examples(kit):
    from eval.data import load_dataset

    dataset = load_dataset(kit / "trial-samples.csv", include_examples=True)
    assert len(dataset.samples) == 20
    assert dataset.origins == {"example": 20}
    s03 = next(s for s in dataset.samples if s.sample_id == "S-03")
    assert s03.country_gold is None and s03.product_interest == ("UKKO",)


def test_xlsx_three_sheets_fixed_header_site_columns_blank(kit):
    wb = openpyxl.load_workbook(kit / "trial-scoring.xlsx")
    assert wb.sheetnames == ["样例", "平台验证项", "说明"]
    ws = wb["样例"]
    assert [c.value for c in ws[1]] == gen.SAMPLE_HEADER
    assert ws.freeze_panes == "A2"
    body = [[c.value for c in row] for row in ws.iter_rows(min_row=2) if row[0].value]
    assert [r[0] for r in body] == [f"S-{i:02d}" for i in range(1, 21)]
    assert all(v in (None, "") for r in body for v in r[9:17])
    by = {r[0]: r for r in body}
    assert by["S-05"][5] == "support 或 warranty 均可" and by["S-03"][6] == "空" and by["S-04"][8] == "true / human_requested"
    assert by["S-02"][3].startswith("第 1 条：") and "\n第 2 条：" in by["S-02"][3]
    assert ws["D2"].alignment.wrap_text is True
    checks = wb["平台验证项"]
    assert [c.value for c in checks[1]] == ["编号", "验证内容", "步骤要点", "通过标准", "结果回填到", "结果"]
    ids = [row[0].value for row in checks.iter_rows(min_row=2) if row[0].value]
    assert ids == [f"T-{i}" for i in range(1, 13)]
    assert all(row[5].value in (None, "") for row in checks.iter_rows(min_row=2))
    notes = [row[0].value for row in wb["说明"].iter_rows()]
    assert notes[0].startswith("生成自：02-botmaker/trial-test-plan.md")
    assert notes[1].startswith("生成日期：2026-10-12　命令：python scripts/gen_trial_kit.py --out-dir ")
    assert any("7 个计分字段" in n and "escalation_reason" in n for n in notes)


def test_markdown_cell_semantics_and_multi_turn():
    assert gen.split_row("| S-99 | a<br>b | `code` x | left \\| right |") == ["S-99", "a\nb", "code x", "left | right"]
    assert gen.conversation_text("第 1 条：Hi there. 第 2 条：Company X.") == "Hi there. / Company X."
    assert gen.conversation_text("single line") == "single line"
    assert gen.type_or_intent("空", "unknown") == ("", None)
    assert gen.type_or_intent("dealer", "B2B") == ("dealer", None)
    assert gen.type_or_intent("dealer 或 other 均可", "B2B") == ("dealer", "期望取值:dealer 或 other 均可→dealer")
    assert gen.type_or_intent("任意或空", "B2C") == ("other", "期望取值:任意或空→other")
    assert gen.type_or_intent("任意或空", "unknown") == ("", "期望取值:任意或空→空")
    assert gen.products("MC10;PESGO") == "MC10;PESGO" and gen.products("空") == ""
    assert gen.escalation("false / 空") == ("false", "") and gen.escalation("true / b2b_qualified") == ("true", "b2b_qualified")


def test_data_origin_synthetic_is_consumable_by_eval_run(tmp_path):
    from eval.data import load_dataset

    out = tmp_path / "kit"
    assert gen.main(["--out-dir", str(out), "--date", "2026-10-12", "--data-origin", "synthetic"]) == 0
    dataset = load_dataset(out / "trial-samples.csv")  # eval.run loads without include_examples
    assert dataset.origins == {"synthetic": 20}


def test_exit_2_when_sample_count_is_off(tmp_path, capsys):
    text = PLAN.read_text(encoding="utf-8")
    short = tmp_path / "plan.md"
    short.write_text(text.replace("| S-20 |", "| X-20 |"), encoding="utf-8")
    assert gen.main(["--out-dir", str(tmp_path / "kit"), "--plan", str(short)]) == 2
    assert "expected 20 samples" in capsys.readouterr().err
