"""配错启动即报：ALLOWED_IPS 与 DISPLAY_TIMEZONE 在 Settings 构造时校验，`app.demo --timezone` 同一套校验。

以前 ALLOWED_IPS 里解析不了的条目在请求时被静默跳过（用空格分隔的整串全部失效、所有回调 403），
DISPLAY_TIMEZONE 拼错时卡片静默改用 UTC 却仍标原名。现在两者都在启动时报错并指出是哪个值。
"""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app import demo
from app.config import Settings


@pytest.mark.parametrize(("value", "bad_item"), [
    ("203.0.113.0/33", "203.0.113.0/33"),                                 # prefix out of range
    ("203.0.113.0/24 198.51.100.7", "203.0.113.0/24 198.51.100.7"),       # space instead of comma
    ("203.0.113.0/24，198.51.100.7", "203.0.113.0/24，198.51.100.7"),     # full-width comma
    ("203.0.113.0/24, botmaker-egress", "botmaker-egress"),               # one bad entry among good ones
])
def test_allowed_ips_with_a_bad_entry_refuses_to_load(value, bad_item):
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None, allowed_ips=value)
    message = str(excinfo.value)
    assert "allowed_ips" in message and repr(bad_item) in message
    assert "多个地址用英文逗号分隔" in message


@pytest.mark.parametrize(("value", "entries"), [
    ("", []),
    ("203.0.113.0/24, 198.51.100.7", ["203.0.113.0/24", "198.51.100.7"]),
    (" 203.0.113.5/24 ,2001:db8::/32, ", ["203.0.113.5/24", "2001:db8::/32"]),   # host bits allowed (strict=False)
])
def test_allowed_ips_comma_separated_or_empty_loads(value, entries):
    assert Settings(_env_file=None, allowed_ips=value).allowed_ip_list == entries


def test_allowed_ips_from_the_environment_is_checked_at_startup(monkeypatch):
    monkeypatch.setenv("ALLOWED_IPS", "203.0.113.0/24 198.51.100.7")
    with pytest.raises(ValidationError, match="多个地址用英文逗号分隔"):
        Settings(_env_file=None)


@pytest.mark.parametrize("value", ["Asia/Shangai", "Shanghai", "", "../etc/passwd"])
def test_display_timezone_typo_refuses_to_load(value):
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None, display_timezone=value)
    message = str(excinfo.value)
    assert "display_timezone" in message and repr(value) in message and "Asia/Shanghai" in message


def test_display_timezone_from_the_environment_is_checked_at_startup(monkeypatch):
    monkeypatch.setenv("DISPLAY_TIMEZONE", "Asia/Shangai")
    with pytest.raises(ValidationError, match="Asia/Shangai"):
        Settings(_env_file=None)


@pytest.mark.parametrize("value", ["Europe/Berlin", "UTC", "America/Sao_Paulo"])
def test_default_and_real_time_zones_load(value):
    assert Settings(_env_file=None).display_timezone == "Asia/Shanghai"
    assert Settings(_env_file=None, display_timezone=value).display_timezone == value


def test_demo_timezone_typo_is_a_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as excinfo:
        demo.main(["--out", str(tmp_path / "out"), "--cases", "U03", "--timezone", "Asia/Shangai"])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "--timezone" in err and "'Asia/Shangai'" in err and "Asia/Shanghai" in err
    assert not (tmp_path / "out").exists()
