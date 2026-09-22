"""并发压测的回归用例：用子进程跑 tools/loadtest.py（真 uvicorn + 真并发），不用 TestClient。

TestClient 在同一个事件循环里串行处理请求，验不了"同号码并发回调不丢更新、只发一张卡"。
这里起真服务、真并发，然后自己打开 --db 指定的 SQLite 核对：leads = 1（场景 A）+ n（场景 B）。
两个用例共用一次压测（module 级 fixture），总时长控制在 30 秒内。
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
LOADTEST = SERVICE_ROOT / "tools" / "loadtest.py"
N = 20
CONCURRENCY = 10
KEYS = {"n", "concurrency", "a_processed", "a_leads", "a_notifications", "b_leads", "b_notifications",
        "p50_ms", "p95_ms", "max_ms", "ok"}


@pytest.fixture(scope="module")
def loadtest_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    tmp = tmp_path_factory.mktemp("loadtest")
    db, out, js = tmp / "leads.db", tmp / "report.md", tmp / "summary.json"
    proc = subprocess.run(
        [sys.executable, str(LOADTEST), "--n", str(N), "--concurrency", str(CONCURRENCY),
         "--db", str(db), "--out", str(out), "--json", str(js)],
        cwd=SERVICE_ROOT, capture_output=True, text=True, timeout=120,
    )
    return {"proc": proc, "db": db, "out": out, "json": js}


def test_loadtest_invariants_hold(loadtest_run: dict) -> None:
    proc: subprocess.CompletedProcess[str] = loadtest_run["proc"]
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    tail = proc.stdout.strip().splitlines()[-1]
    assert tail.startswith(f"n={N} concurrency={CONCURRENCY} ") and tail.endswith("ok=true"), tail

    data = json.loads(loadtest_run["json"].read_text(encoding="utf-8"))
    assert KEYS <= set(data), sorted(KEYS - set(data))
    assert data["ok"] is True
    assert data["a_processed"] == N          # 每条回调都记了账
    assert data["a_leads"] == 1              # 同号码并发：只有一条线索，读改写没丢
    assert data["a_notifications"] == 1      # 同线索同原因同会话：只发一张卡
    assert data["b_leads"] == N              # 不同号码：各成一条线索
    assert data["b_notifications"] == N
    assert 0 < data["p95_ms"] <= data["max_ms"] < 60_000


def test_loadtest_db_holds_one_plus_n_leads(loadtest_run: dict) -> None:
    conn = sqlite3.connect(f"file:{loadtest_run['db']}?mode=ro", uri=True)
    try:
        leads = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        notifications = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
        processed = conn.execute("SELECT COUNT(*) FROM processed_events").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM notifications WHERE status = 'pending'").fetchone()[0]
    finally:
        conn.close()
    assert leads == 1 + N
    assert notifications == 1 + N
    assert processed == 2 * N
    assert pending == 0  # NOTIFIERS 为空：后台任务把每张卡记为 skipped，没有卡在 pending

    report = loadtest_run["out"].read_text(encoding="utf-8")
    for heading in ("# 压测报告", "## 1. 环境", "## 2. 场景 A", "## 3. 场景 B", "## 4. 时延", "## 5. 结论"):
        assert heading in report, heading
