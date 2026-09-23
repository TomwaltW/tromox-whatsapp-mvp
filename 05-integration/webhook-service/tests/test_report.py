"""python -m app.report：回放几条 UAT 回调造库，再对该库出周报，逐键对照库里的真实计数。"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app import report
from app.notify import GenericWebhookNotifier
from tromox_lead import EscalationReason, Lead
from webhook_test_helpers import HEADERS, load_fixture

# U01 B2B 合格（IG-2609）、U05 C 端不转人工、U09 unknown 要人工、U13 连续没听懂、U14 低置信度
CASES = ["U01a", "U01b", "U01c", "U05a", "U05b", "U05c", "U09", "U13a", "U13b", "U14"]
TOP_KEYS = {"window", "leads", "by_source_channel", "by_source_code", "escalation", "notifications", "status_funnel", "valid_lead_rate"}
NOTIFICATION_KEYS = {"rows", "sent", "partial", "failed", "pending", "skipped", "latency_p50_s", "latency_p95_s", "over_threshold", "threshold_s"}
CANDIDATE_KEYS = {"lead_id", "reason", "ai_summary"}
_LEAD_ID_RE = re.compile(r"L-[0-9a-f]{12}")


def _section6_rows(md: str) -> list[str]:
    """第 6 节表格里的数据行（以 `| L-` 开头）。"""
    section = md.split("## 6. 复盘清单", 1)[1].split("\n## ", 1)[0]
    return [line for line in section.splitlines() if line.startswith("| L-")]


def _leaks_phone(row: str) -> bool:
    """lead_id 能算回号码，所以同一行里不能再有尾号：去掉 lead_id 之后不许有「尾号」或 4 位以上的连续数字。"""
    rest = _LEAD_ID_RE.sub("", row)
    return "尾号" in rest or re.search(r"\d{4,}", rest) is not None


def _replay(client: TestClient, names: list[str]) -> list[str]:
    phones: list[str] = []
    for name in names:
        payload = load_fixture(f"uat/{name}.json")
        phones.append("+" + str(payload["contactId"]).lstrip("+"))
        assert client.post("/webhooks/botmaker", json=payload, headers=HEADERS).status_code == 200, name
    return sorted(set(phones))


def _window() -> list[str]:
    today = datetime.now(timezone.utc).date()
    return ["--since", (today - timedelta(days=1)).isoformat(), "--until", (today + timedelta(days=1)).isoformat()]


def _run(db: Path, tmp_path: Path, extra: list[str]) -> tuple[dict, str]:
    out, js = tmp_path / "report.md", tmp_path / "report.json"
    assert report.main(["--db", str(db), "--out", str(out), "--json", str(js), *extra]) == 0
    return json.loads(js.read_text(encoding="utf-8")), out.read_text(encoding="utf-8")


def test_counts_match_the_database(client, settings, tmp_path):
    _replay(client, CASES)
    data, md = _run(settings.database_path, tmp_path, _window())
    assert set(data) == TOP_KEYS
    assert set(data["notifications"]) == NOTIFICATION_KEYS

    conn = sqlite3.connect(settings.database_path)
    try:
        leads_total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        b2b = conn.execute("SELECT COUNT(*) FROM leads WHERE segment = 'B2B'").fetchone()[0]
        notif_rows = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
        sent = conn.execute("SELECT COUNT(*) FROM notifications WHERE status = 'sent'").fetchone()[0]
    finally:
        conn.close()
    assert leads_total == 5 and data["leads"]["total"] == 5
    assert data["leads"]["b2b"] == b2b == 2
    assert data["leads"]["b2c"] == 1 and data["leads"]["unknown"] == 2
    assert data["leads"]["b2b_share"] == pytest.approx(2 / 5)
    assert data["by_source_channel"]["instagram"] == 1 and data["by_source_code"] == {"IG-2609": 1}
    assert data["escalation"]["flagged"] == 4 and data["escalation"]["rate"] == pytest.approx(4 / 5)
    assert data["escalation"]["by_reason"] == {"b2b_qualified": 1, "human_requested": 1, "not_understood_twice": 1, "low_confidence": 1}
    assert sum(data["status_funnel"].values()) == 5 and data["status_funnel"]["qualified"] == 1
    assert data["notifications"]["rows"] == notif_rows == 4 and data["notifications"]["sent"] == sent == 4
    assert data["notifications"]["latency_p50_s"] is not None and data["notifications"]["latency_p95_s"] >= data["notifications"]["latency_p50_s"]
    assert data["notifications"]["over_threshold"] == 0 and data["notifications"]["threshold_s"] == 60
    assert data["valid_lead_rate"] == 0.0  # 两条 B 端都停在 qualified，代理口径下无一"有效"
    assert md.startswith(f"# 调优期周报 {data['window']['since']} 至 {data['window']['until']}")
    for heading in ("## 1. 线索", "## 2. 来源", "## 3. 转人工", "## 4. 通知", "## 5. 状态漏斗", "## 6. 复盘清单"):
        assert heading in md
    assert "notify_latency_max_seconds" in md


def test_empty_window_is_all_zero(client, settings, tmp_path):
    _replay(client, CASES)
    data, md = _run(settings.database_path, tmp_path, ["--since", "2030-01-01", "--until", "2030-01-08"])
    assert data["window"] == {"since": "2030-01-01", "until": "2030-01-08"}
    assert data["leads"] == {"total": 0, "b2b": 0, "b2c": 0, "unknown": 0, "b2b_share": 0.0}
    assert all(v == 0 for v in data["by_source_channel"].values()) and data["by_source_code"] == {}
    assert data["escalation"] == {"flagged": 0, "rate": 0.0, "by_reason": {}}
    assert data["notifications"]["rows"] == 0 and data["notifications"]["latency_p50_s"] is None
    assert sum(data["status_funnel"].values()) == 0 and data["valid_lead_rate"] is None
    assert "# 调优期周报 2030-01-01 至 2030-01-08" in md and "本窗口没有候选" in md


def test_markdown_masks_every_phone_number(client, settings, tmp_path):
    phones = _replay(client, CASES)
    data, md = _run(settings.database_path, tmp_path, _window())
    for phone in phones:
        assert phone not in md and phone.lstrip("+") not in md
    section = md.split("## 6. 复盘清单", 1)[1]
    assert "not_understood_twice" in section and "low_confidence" in section
    assert "| lead_id | 原因 | AI 摘要 |" in section and "尾号" not in section  # 不列号码，也不列尾号
    rows = _section6_rows(md)
    assert len(rows) == 2 and not [row for row in rows if _leaks_phone(row)]
    # --json 里没有复盘候选的号码 / 尾号字段（逐条候选只在 Markdown 里）
    blob = json.dumps(data, ensure_ascii=False)
    assert "尾号" not in blob and '"phone"' not in blob
    assert all(set(c) == CANDIDATE_KEYS for c in data.get("review_candidates", []))


def test_review_rows_never_carry_the_phone_or_its_tail(tmp_path):
    """摘要里写了号码也一样：第 6 节整串打码、不留尾号，候选字典里没有号码字段。"""
    leads = [
        Lead(lead_id="L-0123456789ab", phone="+4917604069011", escalation_flag=True,
             escalation_reason=EscalationReason.LOW_CONFIDENCE, ai_summary="客户说回拨 +49 17604069011 或 017604069011。"),
        Lead(lead_id="L-ba9876543210", phone="+14155550123", escalation_flag=True,
             escalation_reason=EscalationReason.NOT_UNDERSTOOD_TWICE, ai_summary=""),
    ]
    candidates = report.review_candidates(leads)
    assert [set(c) for c in candidates] == [CANDIDATE_KEYS, CANDIDATE_KEYS]
    assert candidates[0]["ai_summary"] == "客户说回拨 +49 *** 或 ***。" and candidates[1]["ai_summary"] == "（无摘要）"
    data = report.summarize(leads, [], *report.parse_window("2026-11-09", "2026-11-16"), 60)
    rows = _section6_rows(report.render_markdown(data, candidates, tmp_path / "leads.db"))
    assert len(rows) == 2 and not [row for row in rows if _leaks_phone(row)]
    assert "9011" not in "".join(rows)  # 号码的尾号不出现在第 6 节


def test_window_excludes_until_day(client, settings, tmp_path):
    _replay(client, CASES)
    today = datetime.now(timezone.utc).date().isoformat()
    data, _ = _run(settings.database_path, tmp_path, ["--since", (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat(), "--until", today])
    assert data["leads"]["total"] == 0 and data["notifications"]["rows"] == 0


def test_bad_window_and_missing_db_fail_cleanly(tmp_path):
    with pytest.raises(SystemExit) as exc:
        report.main(["--db", str(tmp_path / "x.db"), "--since", "2026-01-08", "--until", "2026-01-01", "--out", str(tmp_path / "r.md")])
    assert exc.value.code == 2
    assert report.main(["--db", str(tmp_path / "missing.db"), "--out", str(tmp_path / "r.md")]) == 2
    assert not (tmp_path / "r.md").exists()
    with pytest.raises(SystemExit) as exc:  # 既不落盘也不推送 -> 没事可做
        report.main(["--db", str(tmp_path / "x.db")])
    assert exc.value.code == 2


# ------------------------------------------------------------------ --post
def _post_notifier(monkeypatch, response: httpx.Response) -> list[dict]:
    """把 --post 的渠道换成一个走 MockTransport 的 generic webhook，不碰环境变量、不联网。"""
    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return response

    notifier = GenericWebhookNotifier("https://hooks.example.com/SECRET-TOKEN-VALUE",
                                      client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(report, "_configured_notifiers", lambda: [notifier])
    return sent


def test_post_sends_the_six_metric_summary(client, settings, tmp_path, monkeypatch, capsys):
    phones = _replay(client, CASES)
    sent = _post_notifier(monkeypatch, httpx.Response(200, json={"ok": True}))
    out = tmp_path / "report.md"
    assert report.main(["--db", str(settings.database_path), "--out", str(out), *_window(), "--post"]) == 0

    assert "posted=generic" in capsys.readouterr().out
    assert len(sent) == 1 and sent[0]["type"] == "text"
    title, text = sent[0]["title"], sent[0]["text"]
    assert title.startswith("调优期周报") and title.endswith(_window()[3])
    lines = text.split("\n")
    assert len(lines) <= 20
    for item in ("线索 5 条", "来源前 3", "转人工率", "通知 4 条", "状态漏斗", "复盘清单 2 条"):
        assert item in text
    assert "sent 4 / partial 0 / failed 0" in text and "阈值 60 秒" in text
    for phone in phones:  # 摘要只有汇总数，号码与线索明细都不出现
        assert phone not in text and phone.lstrip("+") not in text
    assert "lead_id" not in text and "尾号" not in text
    assert out.read_text(encoding="utf-8").startswith("# 调优期周报")  # 不带 --post 的产物照旧


def test_post_failure_exits_1_and_keeps_the_report(client, settings, tmp_path, monkeypatch, capsys):
    _replay(client, CASES)
    _post_notifier(monkeypatch, httpx.Response(500, text="oops"))
    out = tmp_path / "report.md"
    assert report.main(["--db", str(settings.database_path), "--out", str(out), *_window(), "--post"]) == 1
    captured = capsys.readouterr()
    assert "SECRET-TOKEN-VALUE" not in captured.out + captured.err
    assert "generic" in captured.err and out.exists()


def test_post_without_configured_channels_is_not_a_failure(client, settings, tmp_path, monkeypatch, capsys):
    _replay(client, CASES)
    monkeypatch.setattr(report, "_configured_notifiers", lambda: [])
    assert report.main(["--db", str(settings.database_path), "--out", str(tmp_path / "r.md"), *_window(), "--post"]) == 0
    assert "posted=none" in capsys.readouterr().out


def test_summary_of_an_empty_window_still_has_all_six_items(client, settings, tmp_path, monkeypatch, capsys):
    sent = _post_notifier(monkeypatch, httpx.Response(200, json={"ok": True}))
    assert report.main(["--db", str(settings.database_path), "--out", str(tmp_path / "r.md"),
                        "--since", "2030-01-01", "--until", "2030-01-08", "--post"]) == 0
    assert "posted=generic" in capsys.readouterr().out
    text = sent[0]["text"]
    assert sent[0]["title"] == "调优期周报 2030-01-01 至 2030-01-08"
    assert "线索 0 条（B 端占比 0.0%）" in text and "来源前 3：无" in text
    assert "p95 — 秒" in text and "复盘清单 0 条" in text
