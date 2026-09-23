"""05-integration/deploy/rehearsal.sh：对真起的回调服务（uvicorn 子进程）连跑演练都过，第 5 项用假 docker 核对容器真的重启（不需要 Docker）。"""
from __future__ import annotations

import json
import os
import re
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "05-integration" / "webhook-service"
SCRIPT = ROOT / "05-integration" / "deploy" / "rehearsal.sh"
FIXTURE = SERVICE / "fixtures" / "message_with_variables_b2b.json"
PYTHON = ROOT / ".venv" / "bin" / "python"
TOKEN = "rehearsal-test-token"
HEALTH_TIMEOUT_S = 30.0

pytestmark = pytest.mark.slow  # 起 uvicorn 子进程；TROMOX_FAST_TESTS=1（check_all.sh --fast）时跳过


# ---------------------------------------------------------------- 真服务

@dataclass
class Service:
    base: str
    env: dict[str, str]
    db: Path


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def get_status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except OSError:
        return 0


@pytest.fixture
def service(tmp_path: Path):
    """每个用例一个新服务、一个新库：用例之间不共享 processed_events，谁先跑都一样。写法同 tools/loadtest.py。"""
    port = free_port()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TROMOX_", "COMPOSE_"))}
    env.update(DATABASE_PATH=str(tmp_path / "leads.db"), CSV_EXPORT_PATH=str(tmp_path / "leads.csv"),
               BOTMAKER_WEBHOOK_TOKEN=TOKEN, NOTIFIERS="", STORAGE_BACKENDS="sqlite,csv",
               LOG_LEVEL="WARNING", ALLOWED_IPS="")
    log_path = tmp_path / "uvicorn.log"
    log = open(log_path, "ab")  # noqa: SIM115 - 交给子进程
    proc = subprocess.Popen([str(PYTHON), "-m", "uvicorn", "app.main:create_app", "--factory",
                             "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
                            cwd=SERVICE, env=env, stdout=log, stderr=subprocess.STDOUT)
    log.close()
    base = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + HEALTH_TIMEOUT_S
        while get_status(f"{base}/health") != 200:
            assert proc.poll() is None, f"uvicorn 提前退出：{log_path.read_text(errors='replace')[-2000:]}"
            assert time.monotonic() < deadline, f"/health {HEALTH_TIMEOUT_S:.0f} 秒内没回 200"
            time.sleep(0.1)
        yield Service(base, env, tmp_path / "leads.db")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)


def post_fixture(service: Service, path: Path) -> dict:
    req = urllib.request.Request(f"{service.base}/webhooks/botmaker", data=path.read_bytes(), method="POST",
                                 headers={"auth-bm-token": TOKEN, "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def lead_count(service: Service, lead_id: str) -> int:
    with sqlite3.connect(service.db) as conn:
        return conn.execute("SELECT count(*) FROM leads WHERE lead_id = ?", (lead_id,)).fetchone()[0]


# ---------------------------------------------------------------- 跑演练、读结果表

def rehearse(service: Service, tmp_path: Path, *args: str, **extra_env: str) -> subprocess.CompletedProcess:
    """TMPDIR 指到用例自己的目录，好核对演练的临时样例退出时删掉了。"""
    tmpdir = tmp_path / "rehearsal-tmp"
    tmpdir.mkdir(exist_ok=True)
    env = dict(service.env, TMPDIR=str(tmpdir), **extra_env)
    return subprocess.run(["bash", str(SCRIPT), service.base, TOKEN, *args],
                          capture_output=True, text=True, timeout=240, env=env)


def row(stdout: str, n: int) -> tuple[str, str]:
    """从 stdout 的 Markdown 表取第 n 行的（结果, 说明），如 `| 5 | 重启容器 | PASS | … |`。"""
    for line in stdout.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0] == str(n):
            return cells[2], cells[3]
    raise AssertionError(f"结果表里没有第 {n} 行：\n{stdout}")


def lead_id_of(stdout: str) -> str:
    m = re.search(r"lead_id=(L-[0-9a-f]+)", row(stdout, 3)[1])
    assert m, stdout
    return m.group(1)


# ---------------------------------------------------------------- 假 docker

# 只认演练脚本用到的四种调用，每次调用记一行到 $FAKE_DOCKER_STATE/calls。
# FAKE_DOCKER_MODE=none（ps -q 回空：项目名对不上）| same（restart 后 StartedAt 不变）| changes（restart 后变了）。
# 第 8 项的 exec 真去调 app.forget：在 webhook-service 目录下用仓库 .venv 的 python 跑，库路径取自继承下来的
# DATABASE_PATH / CSV_EXPORT_PATH（与服务同一个库），所以用例能核对演练线索确实删掉了。
FAKE_DOCKER = r'''#!/usr/bin/env bash
st="$FAKE_DOCKER_STATE"
printf '%s\n' "$*" >> "$st/calls"
started() { cat "$st/started" 2>/dev/null || echo 1; }
if [ "$1" = inspect ]; then
  echo "2026-09-23T08:00:0$(started).123456789Z"; exit 0
fi
[ "$1" = compose ] || { echo "fake docker: 不认识的调用: $*" >&2; exit 99; }
shift
while [ $# -gt 0 ]; do case "$1" in -f|-p|--project-name) shift 2 ;; *) break ;; esac; done
case "$1" in
  ps)
    [ "$FAKE_DOCKER_MODE" = none ] || echo "0123456789abcdef0123456789abcdef"
    exit 0 ;;
  restart)
    [ "$FAKE_DOCKER_MODE" != changes ] || echo $(( $(started) + 1 )) > "$st/started"
    exit 0 ;;
  exec)
    shift
    while [ $# -gt 0 ]; do case "$1" in -T) shift ;; webhook) shift; break ;; *) shift ;; esac; done
    [ "$1" != python ] || shift
    cd "$FAKE_DOCKER_SERVICE_DIR" && exec "$FAKE_DOCKER_PYTHON" "$@" ;;
esac
echo "fake docker: 不认识的 compose 子命令: $*" >&2; exit 99
'''


def rehearse_with_fake_docker(service: Service, tmp_path: Path, mode: str) -> tuple[subprocess.CompletedProcess, list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "docker").write_text(FAKE_DOCKER, encoding="utf-8")
    (bin_dir / "docker").chmod(0o755)
    compose_dir = tmp_path / "compose"
    compose_dir.mkdir()
    (compose_dir / "docker-compose.yml").write_text("", encoding="utf-8")  # 空文件：只要存在
    state = tmp_path / "docker-state"
    state.mkdir()
    r = rehearse(service, tmp_path, "--compose-dir", str(compose_dir),
                 PATH=f"{bin_dir}:{service.env['PATH']}", FAKE_DOCKER_STATE=str(state), FAKE_DOCKER_MODE=mode,
                 FAKE_DOCKER_SERVICE_DIR=str(SERVICE), FAKE_DOCKER_PYTHON=str(PYTHON))
    calls = (state / "calls").read_text(encoding="utf-8").splitlines() if (state / "calls").exists() else []
    return r, calls


def restarted(calls: list[str]) -> bool:
    return any("restart" in c.split() for c in calls)  # 按词比，路径里碰巧有 restart 不算


# ---------------------------------------------------------------- 用例

def test_runs_twice_in_a_row_after_the_46_verification(service, tmp_path):
    # deployment.md 4.6：同一份默认样例先手工验证一次，再按第 8 节删掉测试线索
    first = post_fixture(service, FIXTURE)
    assert first["status"] == "lead_upserted"
    forget = subprocess.run([str(PYTHON), "-m", "app.forget", "--lead-id", first["lead_id"], "--yes"],
                            cwd=SERVICE, env=service.env, capture_output=True, text=True, timeout=60)
    assert forget.returncode == 0, forget.stdout + forget.stderr
    # app.forget 按设计不清 processed_events：原样再发仍判 duplicate——这正是演练要改写 id 的原因
    assert post_fixture(service, FIXTURE)["status"] == "duplicate"

    original = FIXTURE.read_bytes()
    runs = [rehearse(service, tmp_path) for _ in range(2)]  # 不给 --compose-dir
    for r in runs:
        assert r.returncode == 0, r.stdout + r.stderr
        assert [row(r.stdout, n)[0] for n in (1, 2, 3, 4, 5, 8)] == ["PASS", "PASS", "PASS", "PASS", "SKIP", "SKIP"]
    tags = [re.search(r"本次运行标识: (\S+)", r.stderr).group(1) for r in runs]
    assert tags[0] != tags[1]
    assert FIXTURE.read_bytes() == original                       # 原样例不动
    assert list((tmp_path / "rehearsal-tmp").iterdir()) == []     # 临时样例退出时删掉


def test_fixture_without_message_ids_gets_a_run_marker(service, tmp_path):
    # 没有 messages[]._id_ 时事件键是内容哈希：顶层加 _rehearsal_run 让哈希每次不同，照样能连跑
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for m in data["messages"]:
        del m["_id_"]
    fixture = tmp_path / "no-ids.json"
    fixture.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    for _ in range(2):
        r = rehearse(service, tmp_path, "--fixture", str(fixture))
        assert r.returncode == 0, r.stdout + r.stderr
        assert row(r.stdout, 3)[0] == "PASS" and row(r.stdout, 4)[0] == "PASS"
        assert "_rehearsal_run" in r.stderr


def test_row5_fails_without_restart_when_no_container_is_found(service, tmp_path):
    # 项目名对不上：docker compose ps -q webhook 回空 → 第 5 项 FAIL、说明提项目名，不去 restart
    r, calls = rehearse_with_fake_docker(service, tmp_path, "none")
    result, note = row(r.stdout, 5)
    assert result == "FAIL", note
    assert "项目名" in note and "COMPOSE_PROJECT_NAME" in note
    assert r.returncode == 1
    assert any(c.endswith("ps -q webhook") for c in calls), calls
    assert not restarted(calls), calls


def test_row5_fails_when_restart_does_not_change_started_at(service, tmp_path):
    # restart 退出 0，但容器 StartedAt 前后一样 → 没有真的重启
    r, calls = rehearse_with_fake_docker(service, tmp_path, "same")
    result, note = row(r.stdout, 5)
    assert result == "FAIL", note
    assert "没有真的重启" in note
    assert r.returncode == 1
    assert restarted(calls), calls


def test_row5_passes_when_started_at_changes_and_row8_really_forgets(service, tmp_path):
    r, calls = rehearse_with_fake_docker(service, tmp_path, "changes")
    result, note = row(r.stdout, 5)
    assert result == "PASS", note
    assert "duplicate" in note  # 重启后再发本次样例仍判重：数据还在
    assert row(r.stdout, 8)[0] == "PASS"
    assert r.returncode == 0, r.stdout + r.stderr
    # 第 8 项经假 docker 的 exec 真调了 app.forget：演练线索已从库里删掉
    lead_id = lead_id_of(r.stdout)
    assert any(" exec -T webhook python -m app.forget --lead-id " + lead_id in c for c in calls), calls
    assert lead_count(service, lead_id) == 0
