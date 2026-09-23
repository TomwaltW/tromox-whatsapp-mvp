"""05-integration/deploy/docker-compose.yml：TROMOX_FORWARDED_ALLOW_IPS 未设取 *、设成空就是空串（谁的代理头都不信）。

compose 的 `${VAR:-默认}` 在变量为空时也取默认，文档说的「留空＝谁都不信」因此不生效；
要写成不带冒号的 `${VAR-默认}`。文本断言之外，有 docker 时真跑一次 `docker compose config` 看渲染结果
（只渲染，不 build、不起容器）；没有 docker 就跳过那一条。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "05-integration" / "deploy"
COMPOSE = DEPLOY / "docker-compose.yml"


def test_forwarded_allow_ips_uses_dash_not_colon_dash():
    text = COMPOSE.read_text(encoding="utf-8")
    assert 'FORWARDED_ALLOW_IPS: "${TROMOX_FORWARDED_ALLOW_IPS-*}"' in text
    assert "${TROMOX_FORWARDED_ALLOW_IPS:-" not in text


def _compose_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "compose", "version"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _rendered_forwarded_allow_ips(env_file: Path, extra: dict[str, str]) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TROMOX_", "COMPOSE_"))}
    env.update(TROMOX_ENV_FILE=str(env_file), **extra)
    # --env-file 也指向这个空文件：本目录若有一份真的 .env（部署机上），它的 TROMOX_* 不会混进插值
    cmd = ["docker", "compose", "--env-file", str(env_file), "-f", str(COMPOSE), "config"]
    r = subprocess.run(cmd, cwd=DEPLOY, env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    m = re.search(r"^\s*FORWARDED_ALLOW_IPS:\s*(.*)$", r.stdout, re.M)
    assert m, r.stdout
    return m.group(1).strip()


def test_docker_compose_config_renders_empty_and_unset(tmp_path):
    if not _compose_available():
        pytest.skip("没有 docker / docker compose")
    env_file = tmp_path / "empty.env"   # 空文件：容器环境里不带任何变量，只看插值
    env_file.write_text("", encoding="utf-8")
    assert _rendered_forwarded_allow_ips(env_file, {"TROMOX_FORWARDED_ALLOW_IPS": ""}) in ('""', "''")
    assert _rendered_forwarded_allow_ips(env_file, {}) in ("'*'", '"*"')
    assert _rendered_forwarded_allow_ips(env_file, {"TROMOX_FORWARDED_ALLOW_IPS": "172.18.0.1"}) == "172.18.0.1"
