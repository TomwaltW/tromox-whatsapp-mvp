"""python -m app.report：回放几条 UAT 回调造库，再对该库出周报，逐键对照库里的真实计数。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import report
from webhook_test_helpers import HEADERS, load_fixture

# U01 B2B 合格（IG-2609）、U05 C 端不转人工、U09 unknown 要人工、U13 连续没听懂、U14 低置信度
CASES = ["U01a", "U01b", "U01c", "U05a", "U05b", "U05c", "U09", "U13a", "U13b", "U14"]
TOP_KEYS = {"window", "leads", "by_source_channel", "by_source_code", "escalation", "notifications", "status_funnel", "valid_lead_rate"}
NOTIFICATION_KEYS = {"rows", "sent", "partial", "failed", "pending", "skipped", "latency_p50_s", "latency_p95_s", "over_threshold", "threshold_s"}


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
    _, md = _run(settings.database_path, tmp_path, _window())
    for phone in phones:
        assert phone not in md and phone.lstrip("+") not in md
    section = md.split("## 6. 复盘清单", 1)[1]
    assert "not_understood_twice" in section and "low_confidence" in section
    assert "尾号 " in section  # 候选行只给尾号 4 位


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
