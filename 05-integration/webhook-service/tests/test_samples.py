"""python -m app.samples：回放 3 个 fixture 造库，再把 raw_events 里的原文导出来，验脱敏、摘要与开关。

库里留原文要 KEEP_RAW_PAYLOADS=true，conftest 的 settings 没开，所以这里自己造一套 Settings 与 TestClient。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import samples
from app.config import Settings
from app.main import create_app
from webhook_test_helpers import HEADERS, NO_WAIT, TOKEN, RecordingNotifier, load_fixture

# 一条 B 端带变量的消息、一条首触消息、一条结束会话事件：两种 kind、有 variables 也有 events。
CASES = ["message_with_variables_b2b.json", "message_user_first.json", "event_conversation_close.json"]
PHONE = "4917604069011"      # 三个 fixture 的 contactId / whatsappNumber / chatIdInChatPlatform
FIRST_NAME = "Jonas"         # firstName；lastName 是 "K"


@pytest.fixture
def raw_db(tmp_path: Path) -> Path:
    """回放 CASES，返回留有 payload_json 的线索库路径。"""
    settings = Settings(_env_file=None, botmaker_webhook_token=TOKEN, keep_raw_payloads=True,
                        database_path=tmp_path / "data" / "leads.db", csv_export_path=tmp_path / "data" / "leads.csv")
    client = TestClient(create_app(settings, notifiers=[RecordingNotifier()], retry_policy=NO_WAIT))
    for name in CASES:
        assert client.post("/webhooks/botmaker", json=load_fixture(name), headers=HEADERS).status_code == 200, name
    return settings.database_path


def _run(capsys, db: Path, out: Path, *extra: str) -> tuple[str, str]:
    """跑一次导出，返回 (stdout 末行, stderr)。create_app 装了 stdout 日志处理器，先把它排干净。"""
    capsys.readouterr()
    assert samples.main(["--out", str(out), "--db", str(db), *extra]) == 0
    captured = capsys.readouterr()
    return [line for line in captured.out.splitlines() if line.strip()][-1], captured.err


def test_exports_one_file_per_event_with_a_schema_summary(raw_db, tmp_path, capsys):
    out = tmp_path / "samples"
    last_line, err = _run(capsys, raw_db, out)

    files = sorted(out.glob("*.json"))
    assert len(files) == 3
    assert last_line == f"samples=3 kinds=event:1,message:2 out={out}"
    assert err == ""
    assert sum("_message_" in p.name for p in files) == 2 and sum("_event_" in p.name for p in files) == 1
    for path in files:  # <YYYYMMDDTHHMMSS>_<kind>_<id>.json
        head, kind, tail = path.stem.split("_", 2)
        assert len(head) == 15 and head[8] == "T" and kind in {"message", "event"} and tail.isdigit()

    summary = (out / "schema-summary.md").read_text(encoding="utf-8")
    assert summary.startswith("# 回调结构摘要")
    for heading in ("## 1. 样本", "## 2. 每种 kind 的键", "## 3. 与 fixture 的差异"):
        assert heading in summary
    assert "- 条数：3" in summary and "kind 分布：event 1、message 2" in summary
    # 第 2 节要能看出顶层有 contactId、有 variables，以及 variables 里具体哪些变量名
    assert "`contactId` | 2" in summary and "`variables` | 2" in summary
    assert "variables：" in summary and "`source_code` | 1" in summary and "`messages` | 2" in summary
    # 第 3 节按 kind 列差异；本次样本就是 fixture，所以顶层没有差异，而驼峰变量是 fixture 独有的
    assert "### message（样本 2 条 / fixture " in summary and "### status（样本 0 条 / fixture " in summary
    assert "`aiSummary`" in summary


def test_redaction_hides_phone_numbers_and_names_but_keeps_the_message_text(raw_db, tmp_path, capsys):
    out = tmp_path / "samples"
    _run(capsys, raw_db, out)
    blob = "".join(p.read_text(encoding="utf-8") for p in sorted(out.glob("*.json")))
    summary = (out / "schema-summary.md").read_text(encoding="utf-8")

    assert PHONE not in blob and PHONE not in summary
    assert "***9011" in blob                        # 号码只留尾号 4 位
    assert f'"{FIRST_NAME}"' not in blob and '"K"' not in blob
    assert blob.count("<redacted>") >= 4            # firstName / lastName / fromName / events[].name
    assert "Hi Tromox! [IG-2609]" in blob           # 正文保留：结构对照要看正文落在哪个字段
    assert "Nordrad Mobility GmbH" in blob
    # 摘要只有键名与计数，所以连姓名字段的值都不会出现，键名本身照常列出来
    assert FIRST_NAME not in summary and "`firstName` | 2" in summary


def test_no_redact_keeps_the_raw_payload_and_warns_on_stderr(raw_db, tmp_path, capsys):
    redacted, raw = tmp_path / "redacted", tmp_path / "raw"
    _run(capsys, raw_db, redacted)
    last_line, err = _run(capsys, raw_db, raw, "--no-redact")

    raw_blob = "".join(p.read_text(encoding="utf-8") for p in sorted(raw.glob("*.json")))
    assert last_line == f"samples=3 kinds=event:1,message:2 out={raw}"
    assert err.strip() == samples.RAW_WARNING and err.startswith("WARNING:")
    assert PHONE in raw_blob and f'"{FIRST_NAME}"' in raw_blob and "conversation-close" in raw_blob
    assert "***9011" not in raw_blob
    # 摘要不含字段值，开不开脱敏都一样
    assert (raw / "schema-summary.md").read_text(encoding="utf-8").splitlines()[5:] == \
           (redacted / "schema-summary.md").read_text(encoding="utf-8").splitlines()[5:]


def test_limit_takes_the_newest_row_and_since_filters_by_date(raw_db, tmp_path, capsys):
    out = tmp_path / "one"
    last_line, _ = _run(capsys, raw_db, out, "--limit", "1")
    files = sorted(out.glob("*.json"))
    assert len(files) == 1 and "_event_" in files[0].name      # 最后回放的是结束会话事件
    assert last_line == f"samples=1 kinds=event:1 out={out}"

    future = tmp_path / "future"
    last_line, _ = _run(capsys, raw_db, future, "--since", "2099-01-01")
    assert last_line == f"samples=0 kinds= out={future}"
    assert list(future.glob("*.json")) == [] and (future / "schema-summary.md").exists()


def test_empty_database_still_writes_a_summary(tmp_path, capsys):
    """没有一条样本时也要出摘要：第 3 节这时就是一份"fixture 里都有哪些键"的清单。"""
    settings = Settings(_env_file=None, botmaker_webhook_token=TOKEN, keep_raw_payloads=True,
                        database_path=tmp_path / "data" / "empty.db", csv_export_path=tmp_path / "data" / "empty.csv")
    create_app(settings, notifiers=[RecordingNotifier()], retry_policy=NO_WAIT)  # 建库建表
    out = tmp_path / "empty"
    last_line, _ = _run(capsys, settings.database_path, out)

    assert last_line == f"samples=0 kinds= out={out}"
    assert list(out.glob("*.json")) == []
    summary = (out / "schema-summary.md").read_text(encoding="utf-8")
    assert "- 条数：0" in summary and "（无样本）" in summary and "（本次没有样本" in summary
    assert "## 3. 与 fixture 的差异" in summary and "### message（样本 0 条 / fixture " in summary


def test_redact_value_walks_nested_structures():
    payload = {
        "contactId": 4917604069011,                       # 整数形态的号码
        "customerId": "TRXDEMOCUSTOMER00001",             # 字母开头的 ID 不该被当号码
        "profileName": "Jonas Keller",
        "messages": [{"fromName": "Jonas K", "message": "call +4917604069011 or sales@example.com", "seq": 7}],
        "flags": {"ok": True, "missing": None},
    }
    got = samples.redact_value(payload)

    assert got["contactId"] == "***9011" and got["customerId"] == "TRXDEMOCUSTOMER00001"
    assert got["profileName"] == "<redacted>" and got["messages"][0]["fromName"] == "<redacted>"
    assert got["messages"][0]["message"] == "call ***9011 or <email>"
    assert got["messages"][0]["seq"] == 7                 # 短数字不动
    assert got["flags"] == {"ok": True, "missing": None}  # bool 不当整数打码
    assert payload["profileName"] == "Jonas Keller"       # 原 payload 不被改


def test_missing_database_exits_2(tmp_path, capsys):
    capsys.readouterr()
    assert samples.main(["--out", str(tmp_path / "out"), "--db", str(tmp_path / "nope.db")]) == 2
    assert "线索库不存在" in capsys.readouterr().err


def test_fixture_items_skips_the_uat_manifest():
    kinds = [kind for kind, _ in samples.fixture_items()]
    payloads = [payload for _, payload in samples.fixture_items()]
    assert set(kinds) == {"message", "event", "status"}
    assert all("cases" not in payload for payload in payloads)   # uat/manifest.json 判不出 kind，被跳过
    assert json.loads((samples.FIXTURES_DIR / "uat" / "manifest.json").read_text(encoding="utf-8"))["cases"]
