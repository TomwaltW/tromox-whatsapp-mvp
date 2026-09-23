"""05-integration/deploy/update.sh：新版本不健康时自动回滚到上一版镜像（假 git / 假 docker + 线程内假 /health，不碰真部署）。

假 git：pull 之前 rev-parse 回旧 sha，pull 之后回新 sha。假 docker：每次调用记一行到 calls；
`image inspect tromox-webhook:latest` 按 HAS_IMAGE 决定有没有镜像；收到反向 tag（rollback → latest）时
写一个 rolled 标记；`compose port webhook 8000` 回假 /health 服务的地址。假 /health 按用例决定何时回 200。
"""
from __future__ import annotations

import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "05-integration" / "deploy"
SCRIPT = DEPLOY / "update.sh"
OLD_SHA, NEW_SHA = "0ld5ha1", "n3w5ha9"
SAVE_TAG = "tag tromox-webhook:latest tromox-webhook:rollback"
REVERSE_TAG = "tag tromox-webhook:rollback tromox-webhook:latest"

FAKE_GIT = f"""#!/usr/bin/env bash
echo "git $*" >> "$STATE/calls"
case "$*" in
  *"rev-parse --show-toplevel"*) echo "$FAKE_REPO" ;;
  *"rev-parse --short HEAD"*) if [ -f "$STATE/pulled" ]; then echo {NEW_SHA}; else echo {OLD_SHA}; fi ;;
  *"pull --ff-only"*) touch "$STATE/pulled"; echo "Updating {OLD_SHA}..{NEW_SHA}" ;;
  *"log --oneline -1"*) if [ -f "$STATE/pulled" ]; then echo "{NEW_SHA} 新版本"; else echo "{OLD_SHA} 旧版本"; fi ;;
esac
exit 0
"""

FAKE_DOCKER = """#!/usr/bin/env bash
echo "docker $*" >> "$STATE/calls"
case "$*" in
  "image inspect tromox-webhook:latest") if [ "$HAS_IMAGE" = 1 ]; then echo '[{}]'; exit 0; else echo "No such image" >&2; exit 1; fi ;;
  "tag tromox-webhook:rollback tromox-webhook:latest") touch "$STATE/rolled"; exit 0 ;;
  "compose port webhook 8000") echo "127.0.0.1:$HEALTH_PORT"; exit 0 ;;
esac
exit 0
"""


def _serve(healthy) -> HTTPServer:
    """假 /health：healthy() 为真回 200，否则 503（curl -f 判失败）。"""

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):  # 别把请求日志打进 pytest 输出
            pass

        def do_GET(self):  # noqa: N802
            ok = healthy()
            body = b'{"status": "ok"}' if ok else b'{"status": "down"}'
            self.send_response(200 if ok else 503)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture()
def shims(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("git", FAKE_GIT), ("docker", FAKE_DOCKER)):
        (bin_dir / name).write_text(body, encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    return tmp_path


def run_update(tmp: Path, health: str, *, has_image: bool = True, args: tuple[str, ...] = ()):
    """health：always（新版本就健康）/ after_rollback（收到反向 tag 才健康）/ never。返回 (结果, docker+git 调用列表)。"""
    state = tmp / "state"
    state.mkdir()
    rules = {"always": lambda: True, "after_rollback": lambda: (state / "rolled").exists(), "never": lambda: False}
    srv = _serve(rules[health])
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TROMOX_", "COMPOSE_"))}
    env.update(PATH=f"{tmp / 'bin'}{os.pathsep}{os.environ['PATH']}", STATE=str(state), FAKE_REPO=str(ROOT),
               HAS_IMAGE="1" if has_image else "0", HEALTH_PORT=str(srv.server_address[1]), TROMOX_UPDATE_WAIT_S="2")
    try:
        result = subprocess.run(["bash", str(SCRIPT), *args, str(DEPLOY)], capture_output=True, text=True, timeout=60, env=env)
    finally:
        srv.shutdown()
    calls_file = state / "calls"
    calls = calls_file.read_text(encoding="utf-8").splitlines() if calls_file.exists() else []
    return result, calls


def _index(calls: list[str], needle: str) -> int:
    return next(i for i, c in enumerate(calls) if needle in c)


def test_healthy_update_saves_rollback_image_and_exits_0(shims):
    r, calls = run_update(shims, "always")
    assert r.returncode == 0, r.stderr
    assert f"docker {SAVE_TAG}" in calls
    assert not any(REVERSE_TAG in c for c in calls)
    assert not any("--no-build" in c for c in calls)
    # 先另存镜像、记下旧 sha，再 pull；pull 之后才 build / up
    assert _index(calls, SAVE_TAG) < _index(calls, "pull --ff-only") < _index(calls, "compose build webhook") \
        < _index(calls, "compose up -d webhook")
    assert f"{OLD_SHA} → {NEW_SHA}" in r.stdout


def test_unhealthy_then_rollback_healthy_exits_1_with_pin_command(shims):
    r, calls = run_update(shims, "after_rollback")
    assert r.returncode == 1, r.stderr
    assert _index(calls, "compose up -d webhook") < _index(calls, REVERSE_TAG) < _index(calls, "compose up -d --no-build webhook")
    assert "已回滚到上一版镜像" in r.stderr
    assert NEW_SHA in r.stderr and OLD_SHA in r.stderr
    assert f"reset --hard {OLD_SHA}" in r.stderr
    # 回滚前把新版本容器的日志留底（重建之后就没了）
    assert _index(calls, "compose logs") < _index(calls, REVERSE_TAG)


def test_rollback_still_unhealthy_exits_2(shims):
    r, calls = run_update(shims, "never")
    assert r.returncode == 2, r.stderr
    assert any(REVERSE_TAG in c for c in calls)
    assert any("up -d --no-build webhook" in c for c in calls)
    assert "回滚后" in r.stderr and "没有健康的版本" in r.stderr


def test_no_rollback_flag_reports_only_and_exits_1(shims):
    r, calls = run_update(shims, "never", args=("--no-rollback",))
    assert r.returncode == 1, r.stderr
    assert not any(REVERSE_TAG in c for c in calls)
    assert not any("--no-build" in c for c in calls)
    assert "--no-rollback" in r.stderr and f"reset --hard {OLD_SHA}" in r.stderr


def test_first_deploy_without_image_cannot_roll_back_exits_2(shims):
    r, calls = run_update(shims, "never", has_image=False)
    assert r.returncode == 2, r.stderr
    assert not any("tag " in c for c in calls)
    assert "无可回滚的镜像" in r.stderr


def test_build_failure_leaves_containers_alone_and_exits_1(shims):
    # 假 docker 的 build 返回 1：线上容器没动（没有 up），给出钉回旧 sha 的命令
    docker = shims / "bin" / "docker"
    docker.write_text(FAKE_DOCKER.replace('case "$*" in\n', 'case "$*" in\n  "compose build webhook") exit 1 ;;\n', 1),
                      encoding="utf-8")
    r, calls = run_update(shims, "always")
    assert r.returncode == 1, r.stderr
    assert not any("compose up" in c for c in calls)
    assert "构建失败" in r.stderr and f"reset --hard {OLD_SHA}" in r.stderr


def test_help_and_bad_wait_value(shims):
    r = subprocess.run(["bash", str(SCRIPT), "--help"], capture_output=True, text=True, timeout=10)
    assert r.returncode == 0 and "--no-rollback" in r.stdout and "TROMOX_UPDATE_WAIT_S" in r.stdout
    env = {**os.environ, "PATH": f"{shims / 'bin'}{os.pathsep}{os.environ['PATH']}", "TROMOX_UPDATE_WAIT_S": "abc"}
    r = subprocess.run(["bash", str(SCRIPT), str(DEPLOY)], capture_output=True, text=True, timeout=10, env=env)
    assert r.returncode == 1 and "TROMOX_UPDATE_WAIT_S" in r.stderr
