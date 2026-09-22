"""05-integration/deploy/healthcheck-alert.sh: 退出码、verdict 格式与告警 POST（用线程内假服务，不碰真部署）。"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "05-integration" / "deploy" / "healthcheck-alert.sh"
TOKEN = "test-token"
HEALTHY = {"raw_events_unprocessed": 0, "notifications": {"failed_24h": 0},
           "mirror_outbox_pending": 0, "mirror_outbox_failed_24h": 0, "mirror_outbox_exhausted": 0}


def _reply(handler: BaseHTTPRequestHandler, code: int, body: bytes) -> None:
    handler.send_response(code)
    handler.send_header("content-type", "application/json")
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def serve_metrics(metrics: dict) -> tuple[HTTPServer, list[str]]:
    """/health 永远 ok；/metrics 校验 auth-bm-token 并回 metrics。返回 (server, 收到的 /metrics 请求列表)。"""
    hits: list[str] = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):  # 别把请求日志打进 pytest 输出
            pass

        def do_GET(self):  # noqa: N802
            if self.path == "/health":
                _reply(self, 200, b'{"status": "ok"}')
            elif self.path == "/metrics":
                hits.append(self.headers.get("auth-bm-token") or "")
                if self.headers.get("auth-bm-token") != TOKEN:
                    _reply(self, 401, b"{}")
                else:
                    _reply(self, 200, json.dumps(metrics).encode())
            else:
                _reply(self, 404, b"{}")

    return _start(H), hits


def serve_alert() -> tuple[HTTPServer, list[str]]:
    """记录告警 POST 的正文；回 200，免得脚本再多打一行「告警也没发出去」。"""
    bodies: list[str] = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):  # noqa: N802
            bodies.append(self.rfile.read(int(self.headers.get("content-length") or 0)).decode())
            _reply(self, 200, b"{}")

    return _start(H), bodies


def _start(handler: type[BaseHTTPRequestHandler]) -> HTTPServer:
    srv = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def run(health_url: str, alert_url: str | None = None, token: str | None = TOKEN) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "TROMOX_METRICS_TOKEN"}
    if token is not None:
        env["TROMOX_METRICS_TOKEN"] = token
    args = ["bash", str(SCRIPT), health_url] + ([alert_url] if alert_url else [])
    return subprocess.run(args, capture_output=True, text=True, timeout=60, env=env)


def run_against(metrics: dict, *, with_alert: bool = False, token: str | None = TOKEN):
    srv, hits = serve_metrics(metrics)
    alert, bodies = serve_alert() if with_alert else (None, [])
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}/health"
        alert_url = f"http://127.0.0.1:{alert.server_address[1]}/alert" if alert else None
        return run(url, alert_url, token=token), hits, bodies
    finally:
        srv.shutdown(); srv.server_close()
        if alert:
            alert.shutdown(); alert.server_close()


def closed_port() -> int:
    """绑一个端口再关掉：连接被拒，curl 的 --retry 对拒绝不重试，所以很快（别用 503，那要白等 6 秒）。"""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_all_healthy_exits_zero_and_silent():
    r, hits, _ = run_against(HEALTHY)
    assert r.returncode == 0, r.stderr
    assert r.stdout == "" and r.stderr == ""
    assert hits == [TOKEN]


def test_health_unreachable_alarms_down():
    alert, bodies = serve_alert()
    try:
        r = run(f"http://127.0.0.1:{closed_port()}/health", f"http://127.0.0.1:{alert.server_address[1]}/alert")
    finally:
        alert.shutdown(); alert.server_close()
    assert r.returncode == 1
    assert "tromox webhook down" in r.stderr
    assert len(bodies) == 1 and "down" in bodies[0]


def test_unprocessed_backlog_is_degraded():
    r, _, bodies = run_against({**HEALTHY, "raw_events_unprocessed": 1}, with_alert=True)
    assert r.returncode == 1
    assert "tromox webhook degraded" in r.stderr and "unprocessed=1" in r.stderr
    assert len(bodies) == 1 and "degraded" in bodies[0]


def test_exhausted_mirror_row_is_degraded():
    r, _, _ = run_against({**HEALTHY, "mirror_outbox_exhausted": 1})
    assert r.returncode == 1
    # verdict 三个数、格式逐字（deploy/README.md 第 3 节照这个写）
    assert "tromox webhook degraded: unprocessed=0 failed_24h=0 mirror_exhausted=1" in r.stderr


def test_pending_backlog_alone_does_not_alarm():
    # 飞书故障期间积压是正常的，app.replay 每 5 分钟消化；只有用满重试预算的行才是人工项
    r, _, _ = run_against({**HEALTHY, "mirror_outbox_pending": 40, "mirror_outbox_failed_24h": 7})
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""


def test_missing_mirror_key_counts_as_zero():
    # 老版本服务的 /metrics 没有这个键，不能因此报警
    old = {"raw_events_unprocessed": 0, "notifications": {"failed_24h": 0}}
    r, _, _ = run_against(old)
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""


def test_without_token_metrics_is_never_fetched():
    r, hits, _ = run_against({**HEALTHY, "mirror_outbox_exhausted": 9}, token=None)
    assert r.returncode == 0, r.stderr
    assert hits == []
