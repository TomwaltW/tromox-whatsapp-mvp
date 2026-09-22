"""反向代理后的来源 IP：X-Forwarded-For 只在来源可信时被采信，伪造的一律忽略。

TestClient 验不了这件事 —— 它不经过 uvicorn 的 ProxyHeadersMiddleware，而「信不信这个头」
恰恰是那一层按 FORWARDED_ALLOW_IPS 决定的。所以照 test_concurrency.py 的做法起真 uvicorn
子进程（随机端口、--proxy-headers），用 ALLOWED_IPS=203.0.113.5 跑三种组合：

    可信代理 + 带头   -> 200（采信头，来源算 203.0.113.5）
    可信代理 + 无头   -> 403（来源是 127.0.0.1，不在白名单）
    不可信来源 + 带头 -> 403（头被忽略，伪造不了来源）
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from webhook_test_helpers import load_fixture

SERVICE_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_IP = "203.0.113.5"          # 文档用保留网段；本机绝不会真的是这个地址
TOKEN = "proxy-header-token"
START_TIMEOUT_S = 30.0


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_health(port: int, proc: subprocess.Popen) -> None:
    deadline = time.monotonic() + START_TIMEOUT_S
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise AssertionError(f"uvicorn exited early with {proc.returncode}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:  # noqa: S310
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.2)
    raise AssertionError("uvicorn did not answer /health in time")


def _post_webhook(port: int, headers: dict[str, str]) -> int:
    body = json.dumps(load_fixture("message_user_first.json")).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/webhooks/botmaker", data=body, method="POST",
        headers={"content-type": "application/json", "auth-bm-token": TOKEN, **headers})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


@pytest.fixture
def serve(tmp_path: Path):
    """起一个真 uvicorn（--proxy-headers），FORWARDED_ALLOW_IPS 由用例给；退出时收掉进程。"""
    started: list[subprocess.Popen] = []

    def _start(forwarded_allow_ips: str) -> int:
        port = _free_port()
        data = tmp_path / f"srv-{port}"
        data.mkdir()
        env = {**os.environ,
               "DATABASE_PATH": str(data / "leads.db"),
               "CSV_EXPORT_PATH": str(data / "leads.csv"),
               "STORAGE_BACKENDS": "sqlite",
               "BOTMAKER_WEBHOOK_TOKEN": TOKEN,
               "NOTIFIERS": "",
               "LOG_LEVEL": "WARNING",
               "ALLOWED_IPS": ALLOWED_IP,
               "FORWARDED_ALLOW_IPS": forwarded_allow_ips}
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:create_app", "--factory",
             "--host", "127.0.0.1", "--port", str(port), "--proxy-headers"],
            cwd=SERVICE_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        started.append(proc)
        _wait_health(port, proc)
        return port

    try:
        yield _start
    finally:
        for proc in started:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)


def test_forwarded_header_from_trusted_proxy_is_believed(serve) -> None:
    # 本机就是「可信代理」：头里的 203.0.113.5 被当成真实来源，过 ALLOWED_IPS。
    port = serve("127.0.0.1")
    assert _post_webhook(port, {"X-Forwarded-For": ALLOWED_IP}) == 200


def test_without_forwarded_header_the_peer_address_decides(serve) -> None:
    # 同样可信，但没有头：来源就是 127.0.0.1，不在白名单里。
    port = serve("127.0.0.1")
    assert _post_webhook(port, {}) == 403


def test_forwarded_header_from_untrusted_source_is_ignored(serve) -> None:
    # 只信 10.9.9.9 的代理头；本机发的同一个头被忽略，伪造不出白名单里的来源。
    port = serve("10.9.9.9")
    assert _post_webhook(port, {"X-Forwarded-For": ALLOWED_IP}) == 403


def test_health_stays_reachable_without_any_forwarded_header(serve) -> None:
    # /health 不套 ALLOWED_IPS：容器健康检查从 127.0.0.1 发起，不能被这层挡住。
    port = serve("127.0.0.1")
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as response:  # noqa: S310
        assert response.status == 200
        assert json.loads(response.read())["database"] == "ok"
