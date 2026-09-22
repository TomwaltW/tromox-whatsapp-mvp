#!/usr/bin/env python3
"""并发与时延压测：真起一个 uvicorn 子进程，真并发地打回调，然后打开 SQLite 核对不变量。

    python tools/loadtest.py [--n 50] [--concurrency 20] [--db PATH] [--out report.md] [--json summary.json] [--keep]

验的是 README 第 1 节的两句话，单元测试（TestClient 串行）验不了的那部分：
  场景 A  同号码 / 同会话的 n 条回调并发到达 → processed_events = n、leads = 1、notifications = 1
          （读改写在 BEGIN IMMEDIATE 事务里不丢更新；同一线索同一原因同一会话只发一张卡）
  场景 B  n 个不同号码各一条回调 → leads = n、notifications = n（去重没有把不该合的合掉）
  时延    每个请求的 HTTP 往返毫秒 p50 / p95 / max，对照 06-acceptance/thresholds.json 的
          notify_latency_max_seconds（60 秒）。注意这只是应答时延，不是端到端通知时延。

不联网：NOTIFIERS 为空，通知记为 skipped。不改 app/ 下任何文件；不用 TestClient。
不变量全部成立退出 0，否则 1。号码、公司名全部虚构。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
THRESHOLDS = REPO_ROOT / "06-acceptance" / "thresholds.json"
TOKEN = "loadtest"
TOKEN_HEADER = "auth-bm-token"
HEALTH_TIMEOUT_S = 30.0
REQUEST_TIMEOUT_S = 30.0
SETTLE_TIMEOUT_S = 10.0  # wait for the background deliver() tasks to mark notifications skipped

# 场景 A 的固定客户（虚构：德国手机号段 +49 176）
A_PHONE = "4917600001001"
A_CUSTOMER = "TRXLOADTESTCUSTOMER00A"
A_SESSION = f"{A_CUSTOMER}_2026-11-04T19:12:03.000Z"
A_COMPANY = "Loadtest Zweirad GmbH"

# 场景 B 的号码前缀（虚构：德国手机号段 +49 151，后 8 位按序号生成）
B_PREFIX = "49151"


# ----------------------------------------------------------------------------- payloads
def make_payload(*, phone: str, customer_id: str, session_id: str, message_id: str, company: str,
                 contact_name: str, sent_at: str) -> dict[str, Any]:
    """照 fixtures/message_with_variables_b2b.json 的结构：B 端信息收集完成，变量齐全，触发升级。"""
    return {
        "v": "1.1",
        "type": "message",
        "chatPlatform": "whatsapp",
        "contactId": phone,
        "whatsappNumber": phone,
        "customerId": customer_id,
        "sessionId": session_id,
        "sessionCreationTime": sent_at,
        "customerCreationTime": sent_at,
        "firstName": contact_name.split(" ")[0],
        "lastName": contact_name.split(" ")[-1][:1],
        "chatChannelId": "tromox-whatsapp-000000000000",
        "messages": [
            {
                "_id_": message_id,
                "date": sent_at,
                "from": "user",
                "fromName": contact_name,
                "message": f"{company}, Germany. We are a dealer interested in MC10, about 20 units per year.",
                "operatorId": None,
                "clientPayload": "",
            }
        ],
        "variables": {
            "language": "en",
            "segment": "B2B",
            "b2b_type": "dealer",
            "b2c_intent": "",
            "country_stated": "DE",
            "city_region": "Hamburg",
            "contact_name": contact_name,
            "company": company,
            "role": "owner",
            "product_interest": "MC10",
            "volume": "about 20 units per year",
            "existing_dealer_relationship": "",
            "ai_summary": f"德国经销商 {company}，意向 MC10，每年约 20 台。",
            "ai_confidence": "0.95",
            "escalation_flag": "true",
            "escalation_reason": "b2b_qualified",
            "source_code": "",
        },
    }


A_BASE_TS = datetime(2026, 11, 4, 19, 16, 40, tzinfo=timezone.utc)


def a_message_ts(i: int) -> str:
    """场景 A 第 i 条消息的时间戳：逐条 +1 秒，好让合并后的 first/last_message_ts 能对上最早与最晚一条。"""
    return (A_BASE_TS + timedelta(seconds=i)).isoformat().replace("+00:00", ".000Z")


def scenario_a_payloads(n: int) -> list[dict[str, Any]]:
    out = []
    for i in range(n):
        sent_at = a_message_ts(i)
        out.append(make_payload(phone=A_PHONE, customer_id=A_CUSTOMER, session_id=A_SESSION,
                                message_id=f"TRXLOADTESTA{i:08d}", company=A_COMPANY,
                                contact_name="Lena Testmann", sent_at=sent_at))
    return out


def scenario_b_payloads(n: int) -> list[dict[str, Any]]:
    sent_at = "2026-11-04T19:20:00.000Z"
    out = []
    for i in range(n):
        phone = f"{B_PREFIX}{i:08d}"
        customer = f"TRXLOADTESTB{i:08d}"
        out.append(make_payload(phone=phone, customer_id=customer, session_id=f"{customer}_{sent_at}",
                                message_id=f"TRXLOADTESTB{i:08d}", company=f"Loadtest Handel {i:04d} GmbH",
                                contact_name=f"Kunde {i:04d} Test", sent_at=sent_at))
    return out


# ----------------------------------------------------------------------------- server
def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@dataclass
class Server:
    process: subprocess.Popen[bytes]
    base_url: str
    log_path: Path

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)


def start_server(db_path: Path, csv_path: Path, log_path: Path) -> Server:
    port = free_port()
    env = dict(os.environ)
    env.update({
        "DATABASE_PATH": str(db_path),
        "CSV_EXPORT_PATH": str(csv_path),
        "STORAGE_BACKENDS": "sqlite,csv",
        "BOTMAKER_WEBHOOK_TOKEN": TOKEN,
        "NOTIFIERS": "",
        "LOG_LEVEL": "WARNING",
        "ALLOWED_IPS": "",
    })
    cmd = [sys.executable, "-m", "uvicorn", "app.main:create_app", "--factory",
           "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"]
    log_handle = open(log_path, "ab")  # noqa: SIM115 - handed to the child, closed by the OS with it
    process = subprocess.Popen(cmd, cwd=SERVICE_ROOT, env=env, stdout=log_handle, stderr=subprocess.STDOUT)
    log_handle.close()
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + HEALTH_TIMEOUT_S
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"uvicorn exited early with code {process.returncode}; see {log_path}")
        try:
            response = httpx.get(f"{base_url}/health", timeout=2.0)
            if response.status_code == 200 and response.json().get("status") == "ok":
                return Server(process, base_url, log_path)
            last_error = f"health {response.status_code}: {response.text[:120]}"
        except httpx.HTTPError as exc:
            last_error = f"{type(exc).__name__}"
        time.sleep(0.1)
    process.terminate()
    raise RuntimeError(f"/health did not turn ok within {HEALTH_TIMEOUT_S:.0f}s ({last_error}); see {log_path}")


# ----------------------------------------------------------------------------- firing
@dataclass
class Shot:
    index: int
    status_code: int
    outcome: str
    latency_ms: float
    error: str = ""


def fire(base_url: str, payloads: list[dict[str, Any]], concurrency: int) -> list[Shot]:
    url = f"{base_url}/webhooks/botmaker"
    headers = {TOKEN_HEADER: TOKEN, "content-type": "application/json"}
    bodies = [json.dumps(p, ensure_ascii=False).encode("utf-8") for p in payloads]
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)

    with httpx.Client(timeout=REQUEST_TIMEOUT_S, limits=limits) as client:
        def one(index: int) -> Shot:
            started = time.perf_counter()
            try:
                response = client.post(url, content=bodies[index], headers=headers)
            except httpx.HTTPError as exc:
                return Shot(index, 0, "", (time.perf_counter() - started) * 1000.0, type(exc).__name__)
            elapsed = (time.perf_counter() - started) * 1000.0
            outcome = ""
            try:
                outcome = str(response.json().get("status", ""))
            except ValueError:
                pass
            return Shot(index, response.status_code, outcome, elapsed)

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            return list(pool.map(one, range(len(bodies))))


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    # nearest-rank on the sorted sample; n=1 handled above
    rank = max(1, int(round(pct / 100.0 * len(ordered) + 0.5)))
    return ordered[min(rank, len(ordered)) - 1]


# ----------------------------------------------------------------------------- database
@dataclass
class Counts:
    processed: int
    leads: int
    notifications: int
    raw_events: int
    notification_status: dict[str, int]
    lead_ids: list[str]


def read_counts(db_path: Path) -> Counts:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    try:
        processed = conn.execute("SELECT COUNT(*) FROM processed_events").fetchone()[0]
        leads = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        notifications = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
        raw_events = conn.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
        statuses = dict(conn.execute("SELECT status, COUNT(*) FROM notifications GROUP BY status").fetchall())
        lead_ids = [r[0] for r in conn.execute("SELECT lead_id FROM leads ORDER BY created_at, lead_id").fetchall()]
    finally:
        conn.close()
    return Counts(int(processed), int(leads), int(notifications), int(raw_events),
                  {str(k): int(v) for k, v in statuses.items()}, lead_ids)


def wait_for_settle(db_path: Path, expected_notifications: int) -> Counts:
    """deliver() runs after the HTTP reply; give it a moment so the status column is final."""
    deadline = time.monotonic() + SETTLE_TIMEOUT_S
    counts = read_counts(db_path)
    while time.monotonic() < deadline:
        pending = counts.notification_status.get("pending", 0)
        if pending == 0 and counts.notifications >= expected_notifications:
            break
        time.sleep(0.1)
        counts = read_counts(db_path)
    return counts


def lead_timestamps(db_path: Path, lead_id: str) -> tuple[str | None, str | None]:
    """The merged lead's first/last_message_ts. merge_message() takes min/max over every callback,
    so if the request carrying the earliest or the latest message lost its update, it shows here."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    try:
        row = conn.execute("SELECT data_json FROM leads WHERE lead_id = ?", (lead_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return None, None
    data = json.loads(row[0])
    return data.get("first_message_ts"), data.get("last_message_ts")


def same_instant(value: str | None, expected_iso_z: str) -> bool:
    if not value:
        return False
    try:
        got = datetime.fromisoformat(value.replace("Z", "+00:00"))
        want = datetime.fromisoformat(expected_iso_z.replace("Z", "+00:00"))
    except ValueError:
        return False
    return got == want


# ----------------------------------------------------------------------------- report
def load_threshold() -> int | None:
    try:
        return int(json.loads(THRESHOLDS.read_text(encoding="utf-8"))["notify_latency_max_seconds"])
    except (OSError, ValueError, KeyError):
        return None


def summarise_shots(shots: list[Shot], expected: str = "lead_upserted") -> tuple[int, int, list[str]]:
    ok_count = sum(1 for s in shots if s.status_code == 200 and s.outcome == expected)
    bad = [s for s in shots if not (s.status_code == 200 and s.outcome == expected)]
    detail = [f"#{s.index}: http={s.status_code} status={s.outcome or '-'} {s.error}".strip() for s in bad[:10]]
    return ok_count, len(bad), detail


def build_report(*, n: int, concurrency: int, python: str, uvicorn_version: str, httpx_version: str,
                 db_path: Path, a_shots: list[Shot], b_shots: list[Shot], a_counts: Counts, b_counts: Counts,
                 a_span: tuple[str | None, str | None], a_span_ok: bool, lat: dict[str, float], lat_a: dict[str, float], lat_b: dict[str, float],
                 threshold_s: int | None, checks: list[tuple[str, bool, str]], ok: bool, wall_a: float, wall_b: float) -> str:
    a_ok, a_bad, a_detail = summarise_shots(a_shots)
    b_ok, b_bad, b_detail = summarise_shots(b_shots)
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    lines = [
        "# 压测报告",
        "",
        f"生成时间：{now}　工具：`tools/loadtest.py`　结论：**{'通过' if ok else '未通过'}**",
        "",
        "## 1. 环境",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 服务 | `uvicorn app.main:create_app --factory`（独立子进程，127.0.0.1 随机端口） |",
        f"| Python / uvicorn / httpx | {python} / {uvicorn_version} / {httpx_version} |",
        "| 存储 | `STORAGE_BACKENDS=sqlite,csv`（WAL） |",
        "| 通知 | `NOTIFIERS=`（空：通知行记为 `skipped`，不联网） |",
        f"| 数据库 | `{db_path}` |",
        f"| 请求数 n / 并发 | {n} / {concurrency}（线程池，每线程一条长连接） |",
        "",
        "## 2. 场景 A 同号码",
        "",
        f"同一 `contactId` / `sessionId`，{n} 条回调各带不同的 `messages[0]._id_`，并发 {concurrency} 一起打。",
        "预期：`processed_events` = n、`leads` = 1、`notifications` = 1，所有响应 200 且 `status=lead_upserted`。",
        "",
        "| 指标 | 实测 | 预期 |",
        "|---|---|---|",
        f"| 响应 200 且 lead_upserted | {a_ok} | {n} |",
        f"| processed_events | {a_counts.processed} | {n} |",
        f"| leads | {a_counts.leads} | 1 |",
        f"| notifications | {a_counts.notifications} | 1 |",
        f"| notifications 状态 | {a_counts.notification_status or {}} | 全部 skipped（无通知渠道） |",
        f"| 合并后 first_message_ts / last_message_ts | {a_span[0]} / {a_span[1]} | 最早与最晚一条：{a_message_ts(0)} / {a_message_ts(n - 1)}（{'对上' if a_span_ok else '对不上'}） |",
        f"| 墙钟 | {wall_a:.2f} s | - |",
    ]
    if a_detail:
        lines += ["", f"异常响应（前 {len(a_detail)} 条）：", *[f"- {d}" for d in a_detail]]
    lines += [
        "",
        "## 3. 场景 B 不同号码",
        "",
        f"{n} 个不同的虚构德国号码（+49 151 …），各一条回调、各自会话，并发 {concurrency}。",
        "预期：新增 `leads` = n、新增 `notifications` = n（去重只合同一号码，不会把不同号码合掉）。",
        "",
        "| 指标 | 实测 | 预期 |",
        "|---|---|---|",
        f"| 响应 200 且 lead_upserted | {b_ok} | {n} |",
        f"| 新增 processed_events | {b_counts.processed - a_counts.processed} | {n} |",
        f"| 新增 leads | {b_counts.leads - a_counts.leads} | {n} |",
        f"| 新增 notifications | {b_counts.notifications - a_counts.notifications} | {n} |",
        f"| 库内累计 leads / notifications / processed_events | {b_counts.leads} / {b_counts.notifications} / {b_counts.processed} | {n + 1} / {n + 1} / {2 * n} |",
        f"| 墙钟 | {wall_b:.2f} s | - |",
    ]
    if b_detail:
        lines += ["", f"异常响应（前 {len(b_detail)} 条）：", *[f"- {d}" for d in b_detail]]
    threshold_text = f"{threshold_s} 秒" if threshold_s is not None else "（thresholds.json 不可读）"
    lines += [
        "",
        "## 4. 时延",
        "",
        "每个请求从发出到收到 HTTP 应答的往返毫秒（客户端计时，含本机回环）。",
        "",
        "| 样本 | p50 ms | p95 ms | max ms |",
        "|---|---|---|---|",
        f"| 全部（{2 * n} 条） | {lat['p50']:.1f} | {lat['p95']:.1f} | {lat['max']:.1f} |",
        f"| 场景 A 同号码 | {lat_a['p50']:.1f} | {lat_a['p95']:.1f} | {lat_a['max']:.1f} |",
        f"| 场景 B 不同号码 | {lat_b['p50']:.1f} | {lat_b['p95']:.1f} | {lat_b['max']:.1f} |",
        "",
        f"对照 `06-acceptance/thresholds.json` 的 `notify_latency_max_seconds` = {threshold_text}：",
        f"应答 max {lat['max']:.1f} ms ≈ {lat['max'] / 1000.0:.3f} s，远小于 60 秒。",
        "但要说清：这里量的是**回调应答时延**（收到回调到回 200），不是端到端通知时延"
        "（回调到达 → 卡片出现在飞书 / 企微群）。卡片是在应答之后由后台任务发出的，本压测 `NOTIFIERS` 为空、不联网，"
        "所以真正的端到端 60 秒指标要在试用期用真实渠道按 `06-acceptance/acceptance-criteria.md` 的方法测。"
        "应答快只说明服务自身不会成为那 60 秒里的瓶颈。",
        "",
        "## 5. 结论",
        "",
        "| 判据 | 结果 | 说明 |",
        "|---|---|---|",
        *[f"| {name} | {'PASS' if passed else 'FAIL'} | {detail} |" for name, passed, detail in checks],
        "",
        f"**总体：{'ok=true，不变量全部成立' if ok else 'ok=false，有不变量不成立（见上表 FAIL 行）'}。**",
        "",
        "本报告只覆盖服务在真并发下的正确性与应答时延；渠道侧（飞书 / 企微 / 邮件）的可达性与端到端时延不在其中。",
    ]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- main
def run(n: int, concurrency: int, db_arg: Path | None, out_path: Path | None, json_path: Path | None, keep: bool) -> int:
    import uvicorn  # noqa: PLC0415 - only for the version string in the report

    tmp_dir = Path(tempfile.mkdtemp(prefix="tromox-loadtest-"))
    db_path = (db_arg.resolve() if db_arg else tmp_dir / "leads.db")
    csv_path = tmp_dir / "leads.csv"
    log_path = tmp_dir / "uvicorn.log"
    if db_arg is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[loadtest] tmp={tmp_dir} db={db_path}", file=sys.stderr, flush=True)

    server: Server | None = None
    exit_code = 1
    try:
        server = start_server(db_path, csv_path, log_path)
        print(f"[loadtest] server up at {server.base_url} (pid {server.process.pid})", file=sys.stderr, flush=True)

        # 场景 A
        t0 = time.perf_counter()
        a_shots = fire(server.base_url, scenario_a_payloads(n), concurrency)
        wall_a = time.perf_counter() - t0
        a_counts = wait_for_settle(db_path, expected_notifications=1)
        a_span = lead_timestamps(db_path, a_counts.lead_ids[0]) if a_counts.lead_ids else (None, None)
        a_span_ok = same_instant(a_span[0], a_message_ts(0)) and same_instant(a_span[1], a_message_ts(n - 1))

        # 场景 B（同一库，累加）
        t0 = time.perf_counter()
        b_shots = fire(server.base_url, scenario_b_payloads(n), concurrency)
        wall_b = time.perf_counter() - t0
        b_counts = wait_for_settle(db_path, expected_notifications=n + 1)

        a_ok, a_bad, _ = summarise_shots(a_shots)
        b_ok, b_bad, _ = summarise_shots(b_shots)
        b_leads = b_counts.leads - a_counts.leads
        b_notifications = b_counts.notifications - a_counts.notifications
        b_processed = b_counts.processed - a_counts.processed

        all_lat = [s.latency_ms for s in a_shots + b_shots]
        lat = {"p50": percentile(all_lat, 50), "p95": percentile(all_lat, 95), "max": max(all_lat) if all_lat else 0.0}
        lat_a_list = [s.latency_ms for s in a_shots]
        lat_b_list = [s.latency_ms for s in b_shots]
        lat_a = {"p50": percentile(lat_a_list, 50), "p95": percentile(lat_a_list, 95), "max": max(lat_a_list) if lat_a_list else 0.0}
        lat_b = {"p50": percentile(lat_b_list, 50), "p95": percentile(lat_b_list, 95), "max": max(lat_b_list) if lat_b_list else 0.0}
        threshold_s = load_threshold()

        checks: list[tuple[str, bool, str]] = [
            ("A 全部响应 200 且 lead_upserted", a_bad == 0, f"{a_ok}/{n}"),
            ("A processed_events = n", a_counts.processed == n, f"{a_counts.processed}"),
            ("A leads = 1（同号码并发不丢更新、不分裂）", a_counts.leads == 1, f"{a_counts.leads}"),
            ("A notifications = 1（同线索同原因同会话只发一张卡）", a_counts.notifications == 1, f"{a_counts.notifications}"),
            ("A notifications 无 pending 残留", a_counts.notification_status.get("pending", 0) == 0, f"{a_counts.notification_status}"),
            ("B 全部响应 200 且 lead_upserted", b_bad == 0, f"{b_ok}/{n}"),
            ("B 新增 leads = n", b_leads == n, f"{b_leads}"),
            ("B 新增 notifications = n", b_notifications == n, f"{b_notifications}"),
            ("B 新增 processed_events = n", b_processed == n, f"{b_processed}"),
            ("应答 max 远小于 notify_latency_max_seconds",
             threshold_s is not None and lat["max"] < threshold_s * 1000.0 / 10.0,
             f"max {lat['max']:.1f} ms vs {threshold_s} s" if threshold_s is not None else "thresholds.json 不可读"),
        ]
        checks.insert(3, ("A 合并后 first/last_message_ts 对上最早与最晚一条（最早 / 最晚那条更新没丢）", a_span_ok,
                          f"{a_span[0]} / {a_span[1]}"))
        ok = all(passed for _, passed, _ in checks)

        summary = {
            "n": n, "concurrency": concurrency,
            "a_processed": a_counts.processed, "a_leads": a_counts.leads, "a_notifications": a_counts.notifications,
            "b_leads": b_leads, "b_notifications": b_notifications,
            "p50_ms": round(lat["p50"], 2), "p95_ms": round(lat["p95"], 2), "max_ms": round(lat["max"], 2),
            "ok": ok,
            # extras (not part of the fixed contract, kept after the fixed keys)
            "a_ok_responses": a_ok, "b_ok_responses": b_ok, "b_processed": b_processed,
            "db_leads_total": b_counts.leads, "db_notifications_total": b_counts.notifications,
            "db_processed_total": b_counts.processed, "notification_status": b_counts.notification_status,
            "wall_a_s": round(wall_a, 3), "wall_b_s": round(wall_b, 3), "db": str(db_path),
            "checks": [{"name": name, "pass": passed, "detail": detail} for name, passed, detail in checks],
        }
        report = build_report(
            n=n, concurrency=concurrency, python=sys.version.split()[0], uvicorn_version=uvicorn.__version__,
            httpx_version=httpx.__version__, db_path=db_path, a_shots=a_shots, b_shots=b_shots,
            a_counts=a_counts, b_counts=b_counts, a_span=a_span, a_span_ok=a_span_ok, lat=lat, lat_a=lat_a, lat_b=lat_b,
            threshold_s=threshold_s, checks=checks, ok=ok, wall_a=wall_a, wall_b=wall_b,
        )
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(report, encoding="utf-8")
        if json_path is not None:
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        for name, passed, detail in checks:
            print(f"  {'PASS' if passed else 'FAIL'}  {name}  ({detail})")
        print(f"n={n} concurrency={concurrency} a_leads={a_counts.leads} a_notifications={a_counts.notifications} "
              f"b_leads={b_leads} p95_ms={lat['p95']:.1f} ok={'true' if ok else 'false'}", flush=True)
        exit_code = 0 if ok else 1
    finally:
        if server is not None:
            server.stop()
        if not keep and db_arg is None:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        elif not keep:
            # keep the caller's --db, drop only our scratch (csv, uvicorn log)
            shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            print(f"[loadtest] kept {tmp_dir}", file=sys.stderr)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n", type=int, default=50, help="每个场景的回调条数（默认 50）")
    parser.add_argument("--concurrency", type=int, default=20, help="并发线程数（默认 20）")
    parser.add_argument("--db", type=Path, default=None, help="SQLite 文件路径；不给则用临时目录")
    parser.add_argument("--out", type=Path, default=None, help="Markdown 报告输出路径")
    parser.add_argument("--json", dest="json_path", type=Path, default=None, help="JSON 摘要输出路径")
    parser.add_argument("--keep", action="store_true", help="保留临时目录（含 uvicorn 日志与 CSV）")
    args = parser.parse_args(argv)
    if args.n < 1 or args.concurrency < 1:
        parser.error("--n and --concurrency must be >= 1")
    return run(args.n, args.concurrency, args.db, args.out, args.json_path, args.keep)


if __name__ == "__main__":
    sys.exit(main())
