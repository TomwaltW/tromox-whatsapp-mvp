"""`python -m app.demo`: the UAT cases replayed offline into the cards sales would receive."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

from app import demo
from tromox_lead import LEAD_FIELDS

from webhook_test_helpers import FIXTURES

UAT = FIXTURES / "uat"
MANIFEST = json.loads((UAT / "manifest.json").read_text(encoding="utf-8"))["cases"]


def expected_cards(case: dict) -> int:
    """Cards the manifest says the case sends: `expect.notifications`, or - when a case only states
    the notification-table total (U18) - the last `after` checkpoint's `notifications`."""
    expect = case["expect"]
    if "notifications" in expect:
        return int(expect["notifications"])
    checkpoints = case.get("after", {})
    if checkpoints:
        return int(checkpoints[max(checkpoints, key=int)].get("notifications", 0))
    return int(expect.get("notifications_total", 0))


EXPECTED_CARDS = sum(expected_cards(case) for case in MANIFEST.values())
FULL_PHONES = sorted({
    str(json.loads(path.read_text(encoding="utf-8")).get("contactId", "")).lstrip("+")
    for path in UAT.glob("U*.json")
} - {""})
NOW = "2026-11-10T12:00:00Z"


def _run(tmp_path: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> tuple[int, str, Path]:
    out = tmp_path / "demo"
    code = demo.main(["--out", str(out), "--now", NOW, *extra])
    return code, capsys.readouterr().out, out


def test_full_replay_writes_every_artifact(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, stdout, out = _run(tmp_path, capsys)
    assert code == 0
    assert stdout.strip().splitlines()[-1] == f"cases={len(MANIFEST)} cards={EXPECTED_CARDS} out={out}"

    cards_md = (out / "cards.md").read_text(encoding="utf-8")
    assert cards_md.startswith("# 演示卡片（UAT 回放）")
    assert len(re.findall(r"^### U\d\d 第 \d+ 张：", cards_md, re.M)) == EXPECTED_CARDS
    for case_id, case in MANIFEST.items():  # each case's card count matches the manifest
        assert len(re.findall(rf"^### {case_id} 第 \d+ 张：", cards_md, re.M)) == expected_cards(case), case_id

    html = (out / "cards.html").read_text(encoding="utf-8")
    assert html.count("<article") == EXPECTED_CARDS
    assert html.count('href="#"') == EXPECTED_CARDS       # the button is decoration, not a live link
    assert 'data-case="U01"' in html and "<dl>" in html
    assert "<script" not in html and 'src="http' not in html and 'href="http' not in html  # self-contained

    payloads = sorted((out / "payloads").glob("*.feishu.json"))
    assert len(payloads) == EXPECTED_CARDS
    for path in payloads:
        body = json.loads(path.read_text(encoding="utf-8"))
        assert body["msg_type"] == "interactive" and body["card"]["header"]["title"]["content"]

    summary = (out / "summary.md").read_text(encoding="utf-8")
    assert "| 用例 | 场景 | 回调数 | 卡片数 | 接管原因 | 最终状态 |" in summary
    assert len(re.findall(r"^\| U\d\d \|", summary, re.M)) == len(MANIFEST)
    assert "| U01 | B 端经销商顺利路径 | 3 | 1 | B 端信息已收集完成 | qualified |" in summary

    with (out / "leads.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == list(LEAD_FIELDS)
    assert len(rows) - 1 >= len(MANIFEST)                 # U15 / U19 store several leads each


def test_cards_never_show_a_full_phone_number(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, _, out = _run(tmp_path, capsys)
    assert code == 0 and FULL_PHONES
    blob = (out / "cards.md").read_text(encoding="utf-8") + (out / "cards.html").read_text(encoding="utf-8")
    blob += "".join(p.read_text(encoding="utf-8") for p in (out / "payloads").glob("*.feishu.json"))
    assert "尾号" in blob
    assert [phone for phone in FULL_PHONES if phone in blob] == []
    leads_csv = (out / "leads.csv").read_text(encoding="utf-8")   # the lead export is not masked
    assert "+4917604069021" in leads_csv


def test_cases_filter_and_deterministic_window(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, stdout, out = _run(tmp_path, capsys, "--cases", "U03", "--timezone", "Europe/Berlin")
    assert code == 0
    assert stdout.strip().splitlines()[-1].startswith("cases=1 cards=1 ")
    cards_md = (out / "cards.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^### U03 第 \d+ 张：", cards_md, re.M)) == 1
    assert "### U01" not in cards_md
    assert "（Europe/Berlin）" in cards_md and "剩余约" in cards_md   # --now pins the countdown
    assert [p.name for p in (out / "payloads").glob("*.feishu.json")] == ["U03-1.feishu.json"]
    assert len(re.findall(r"^\| U\d\d \|", (out / "summary.md").read_text(encoding="utf-8"), re.M)) == 1


def test_unknown_case_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert demo.main(["--out", str(tmp_path / "x"), "--cases", "U03,U99"]) == 2
    assert "U99" in capsys.readouterr().err
    assert not (tmp_path / "x").exists()
