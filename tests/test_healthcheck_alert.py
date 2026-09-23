"""05-integration/deploy/healthcheck-alert.sh: 退出码、verdict 格式与告警 POST（用线程内假服务，不碰真部署）。"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import shutil
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


def serve_metrics(metrics: dict, *, first_status: int | None = None) -> tuple[HTTPServer, list[str]]:
    """/health 永远 ok；/metrics 校验 auth-bm-token 并回 metrics。返回 (server, 收到的 /metrics 请求列表)。

    first_status 给了时，第一次 /metrics 先回这个状态码 + 一段 HTML 正文（模拟反向代理抖一下）。"""
    hits: list[str] = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):  # 别把请求日志打进 pytest 输出
            pass

        def do_GET(self):  # noqa: N802
            if self.path == "/health":
                _reply(self, 200, b'{"status": "ok"}')
            elif self.path == "/metrics":
                hits.append(self.headers.get("auth-bm-token") or "")
                if first_status is not None and len(hits) == 1:
                    _reply(self, first_status, b"<html><body>502 Bad Gateway</body></html>")
                elif self.headers.get("auth-bm-token") != TOKEN:
                    _reply(self, 401, b"{}")
                else:
                    _reply(self, 200, json.dumps(metrics).encode())
            else:
                _reply(self, 404, b"{}")

    return _start(H), hits


def serve_alert(status: int = 200, reply: bytes = b"{}") -> tuple[HTTPServer, list[str]]:
    """记录告警 POST 的正文；默认回 200 {}，免得脚本再多打一行「告警也没发出去」。"""
    bodies: list[str] = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):  # noqa: N802
            bodies.append(self.rfile.read(int(self.headers.get("content-length") or 0)).decode())
            _reply(self, status, reply)

    return _start(H), bodies


def _start(handler: type[BaseHTTPRequestHandler]) -> HTTPServer:
    srv = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def run(health_url: str, alert_url: str | None = None, token: str | None = TOKEN,
        extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "TROMOX_METRICS_TOKEN" and not k.startswith("TROMOX_ALERT_")}
    if token is not None:
        env["TROMOX_METRICS_TOKEN"] = token
    env.update(extra_env or {})
    args = ["bash", str(SCRIPT), health_url] + ([alert_url] if alert_url else [])
    return subprocess.run(args, capture_output=True, text=True, timeout=60, env=env)


def run_against(metrics: dict, *, with_alert: bool = False, token: str | None = TOKEN, first_status: int | None = None):
    srv, hits = serve_metrics(metrics, first_status=first_status)
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


# ---------------------------------------------------------------- /metrics 重试、告警格式与返回码

def alarm_down(alert_status: int = 200, alert_reply: bytes = b"{}", *, alert_path: str = "/alert",
               health_url: str | None = None, **extra_env: str) -> tuple[subprocess.CompletedProcess, list[str]]:
    """/health 连不上 → 脚本告警一次；返回 (结果, 告警假服务收到的请求体列表)。"""
    alert, bodies = serve_alert(alert_status, alert_reply)
    try:
        r = run(health_url or f"http://127.0.0.1:{closed_port()}/health",
                f"http://127.0.0.1:{alert.server_address[1]}{alert_path}", token=None, extra_env=extra_env)
    finally:
        alert.shutdown(); alert.server_close()
    assert r.returncode == 1
    assert len(bodies) == 1, bodies
    return r, bodies


def test_metrics_retry_after_502_is_not_concatenated():
    # 第一次 502（HTML 正文）、重试拿到 200：落临时文件的响应被 curl 截断重写，不会把两段拼成坏 JSON
    r, hits, _ = run_against(HEALTHY, first_status=502)
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""
    assert len(hits) == 2


def test_feishu_format_with_nonzero_code_reports_not_sent():
    # 飞书对格式不对的请求回 HTTP 200 + code 非 0；地址里的 key 不能出现在 stderr
    r, bodies = alarm_down(200, b'{"code": 19002, "msg": "params error"}',
                           alert_path="/open-apis/bot/v2/hook/SECRETKEY123", TROMOX_ALERT_FORMAT="feishu")
    body = json.loads(bodies[0])
    assert body["msg_type"] == "text"
    assert "tromox webhook down" in body["content"]["text"]
    assert "告警也没发出去" in r.stderr and "code=19002" in r.stderr and "HTTP 200" in r.stderr
    assert "SECRETKEY" not in r.stderr


def test_wecom_format_errcode_zero_is_delivered():
    r, bodies = alarm_down(200, b'{"errcode": 0, "errmsg": "ok"}', TROMOX_ALERT_FORMAT="wecom")
    body = json.loads(bodies[0])
    assert body["msgtype"] == "text"
    assert "tromox webhook down" in body["text"]["content"]
    assert "没发出去" not in r.stderr


def test_wecom_nonzero_errcode_reports_not_sent():
    r, _ = alarm_down(200, b'{"errcode": 93000, "errmsg": "invalid webhook url"}', TROMOX_ALERT_FORMAT="wecom")
    assert "告警也没发出去" in r.stderr and "errcode=93000" in r.stderr


def test_feishu_signing_secret_adds_timestamp_and_sign():
    r, bodies = alarm_down(200, b'{"code": 0, "msg": "success"}',
                           TROMOX_ALERT_FORMAT="feishu", TROMOX_ALERT_SIGNING_SECRET="s3cret")
    body = json.loads(bodies[0])
    ts = body["timestamp"]
    assert isinstance(ts, str) and ts.isdigit()
    # 独立重算：sign = base64(HMAC-SHA256(key = f"{timestamp}\n{secret}", msg = b""))
    want = base64.b64encode(hmac.new(f"{ts}\ns3cret".encode(), b"", hashlib.sha256).digest()).decode()
    assert body["sign"] == want
    assert "没发出去" not in r.stderr


def test_generic_body_is_valid_json_with_quotes_and_only_http_status_counts():
    # 消息里带双引号、反斜杠：请求体仍是合法 JSON；通用格式不看返回体里的 code
    health = f'http://127.0.0.1:{closed_port()}/health?x="q"&y=a\\b'
    r, bodies = alarm_down(200, b'{"code": 1}', health_url=health)
    body = json.loads(bodies[0])
    assert set(body) == {"text"}
    assert '"q"' in body["text"] and "a\\b" in body["text"]
    assert "没发出去" not in r.stderr


def test_generic_http_error_reports_not_sent():
    r, _ = alarm_down(500, b"oops")
    assert "告警也没发出去" in r.stderr and "HTTP 500" in r.stderr and "127.0.0.1" in r.stderr


FAKE_CURL = r'''#!/usr/bin/env python3
# 假 curl：发往飞书 / 企业微信主机的请求记下地址与请求体、回一个成功响应；其余原样交给真 curl。
import json, os, sys
args = sys.argv[1:]
url = next((a for a in reversed(args) if a.startswith(("http://", "https://"))), "")
if not any(h in url for h in ("open.feishu.cn", "open.larksuite.com", "qyapi.weixin.qq.com")):
    os.execv(os.environ["REAL_CURL"], ["curl"] + args)
body, out, wfmt = None, None, ""
for i, a in enumerate(args[:-1]):
    if a in ("-d", "--data", "--data-binary"):
        v = args[i + 1]
        body = sys.stdin.read() if v == "@-" else open(v[1:], encoding="utf-8").read() if v.startswith("@") else v
    elif a == "-o":
        out = args[i + 1]
    elif a in ("-w", "--write-out"):
        wfmt = args[i + 1]
with open(os.environ["FAKE_CURL_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps({"url": url, "body": body}) + "\n")
resp = '{"code": 0, "msg": "success", "errcode": 0, "errmsg": "ok"}'
w = wfmt.replace("\\n", "\n").replace("%{http_code}", "200")
if out:
    open(out, "w", encoding="utf-8").write(resp); sys.stdout.write(w)
else:
    sys.stdout.write(resp + w)
'''


def test_format_follows_alert_host_without_override(tmp_path):
    # 不设 TROMOX_ALERT_FORMAT：按主机名选格式。假 curl 只拦这三个主机，/health 仍由真 curl 去连（连不上 → down）
    real_curl = shutil.which("curl")
    assert real_curl
    (tmp_path / "curl").write_text(FAKE_CURL, encoding="utf-8")
    (tmp_path / "curl").chmod(0o755)
    log = tmp_path / "curl.log"
    env = {"PATH": f"{tmp_path}:{os.environ['PATH']}", "REAL_CURL": real_curl, "FAKE_CURL_LOG": str(log)}
    cases = {
        "https://open.feishu.cn/open-apis/bot/v2/hook/SECRETKEY1": "feishu",
        "https://open.larksuite.com/open-apis/bot/v2/hook/SECRETKEY2": "feishu",
        "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=SECRETKEY3": "wecom",
    }
    for alert_url, fmt in cases.items():
        r = run(f"http://127.0.0.1:{closed_port()}/health", alert_url, token=None, extra_env=env)
        assert r.returncode == 1
        assert "tromox webhook down" in r.stderr
        assert "没发出去" not in r.stderr and "SECRETKEY" not in r.stderr
        rec = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
        assert rec["url"] == alert_url
        body = json.loads(rec["body"])
        if fmt == "feishu":
            assert body["msg_type"] == "text" and "tromox webhook down" in body["content"]["text"]
            assert "sign" not in body  # 没设 TROMOX_ALERT_SIGNING_SECRET 就不加签
        else:
            assert body["msgtype"] == "text" and "tromox webhook down" in body["text"]["content"]
