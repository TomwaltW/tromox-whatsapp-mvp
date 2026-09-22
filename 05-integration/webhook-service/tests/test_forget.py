"""python -m app.forget: erase one contact from ledger, CSV and Bitable mirror; preview and confirm;
no phone number in any output. Two leads are built from the UAT fixtures (U01 German dealer, U03
Spanish dealer); the German one is forgotten, the Spanish one must survive untouched."""
from __future__ import annotations

import csv
import logging
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from app import forget
from app.config import Settings
from app.pipeline import Pipeline
from app.store import CsvExportSink, SqliteStore
from app.store.feishu_bitable import FeishuBitableSink

from webhook_test_helpers import NO_WAIT, RecordingNotifier, load_fixture

SERVICE_DIR = Path(__file__).resolve().parents[1]
TARGET_PHONE, TARGET_DIGITS, TARGET_CUSTOMER = "+4917604069021", "4917604069021", "TRXUAT01C1"
OTHER_PHONE = "+34612345678"
FEISHU = {"feishu_app_id": "cli", "feishu_app_secret": "sec", "feishu_bitable_app_token": "bascnX",
          "feishu_bitable_table_id": "tblX"}


@pytest.fixture
def populated(tmp_path: Path) -> Settings:
    """Ledger + CSV with the two leads, raw payloads kept (as during the trial), notifications delivered."""
    settings = Settings(_env_file=None, botmaker_webhook_token="t", database_path=tmp_path / "leads.db",
                        csv_export_path=tmp_path / "leads.csv", storage_backends="sqlite,csv", keep_raw_payloads=True)
    store = SqliteStore(settings.database_path)
    pipeline = Pipeline(settings, store, [CsvExportSink(store, settings.csv_export_path)], [RecordingNotifier()],
                        retry_policy=NO_WAIT)
    for name in ("U01a", "U01b", "U01c", "U03a", "U03b", "U03c"):
        result = pipeline.handle(load_fixture(f"uat/{name}.json"))
        if result.notification_id is not None:
            pipeline.deliver(result.notification_id)
    return settings


def _counts(settings: Settings) -> dict[str, int]:
    conn = sqlite3.connect(settings.database_path)
    try:
        return {t: conn.execute(f"select count(*) from {t}").fetchone()[0]
                for t in ("leads", "notifications", "raw_events", "processed_events")}
    finally:
        conn.close()


def _csv_phones(settings: Settings) -> list[str]:
    with settings.csv_export_path.open(encoding="utf-8-sig", newline="") as fh:
        return [row["phone"] for row in csv.DictReader(fh)]


def _no_phone(text: str) -> bool:
    return TARGET_DIGITS not in text and TARGET_PHONE not in text


def test_dry_run_and_missing_yes_print_the_preview_and_change_nothing(populated, capsys):
    before = _counts(populated)
    assert before["leads"] == 2 and before["notifications"] == 2 and before["raw_events"] == 6
    csv_before = populated.csv_export_path.read_bytes()

    assert forget.run(populated, ["--phone", TARGET_PHONE, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "leads:         1" in out and "notifications: 1" in out and "raw_events:    3" in out
    assert "csv:           rewrite" in out and "sinks:         none" in out and "dry run: nothing changed" in out
    assert _no_phone(out)

    assert forget.run(populated, ["--phone", TARGET_PHONE]) == 3
    out = capsys.readouterr().out
    assert out.rstrip().endswith("add --yes to execute") and _no_phone(out)

    assert _counts(populated) == before and populated.csv_export_path.read_bytes() == csv_before


def test_yes_erases_ledger_rows_and_rewrites_the_csv_leaving_the_other_lead(populated, capsys, caplog):
    store = SqliteStore(populated.database_path)
    target = store.get_lead_by_phone(TARGET_PHONE)
    assert target is not None
    with caplog.at_level(logging.INFO, logger="app.forget"):
        assert forget.run(populated, ["--phone", TARGET_PHONE, "--yes"]) == 0
    out = capsys.readouterr().out
    assert out.strip().splitlines()[-1] == (
        f"forgotten lead_id={target.lead_id} leads=1 notifications=1 raw_events=3 csv=rewritten sinks=none")

    after = _counts(populated)
    assert after == {"leads": 1, "notifications": 1, "raw_events": 3, "processed_events": 6}  # processed_events untouched
    assert store.get_lead_by_phone(TARGET_PHONE) is None and store.get_lead(target.lead_id) is None
    other = store.get_lead_by_phone(OTHER_PHONE)
    assert other is not None and other.company == "Motos Valencia SL"
    conn = sqlite3.connect(populated.database_path)
    payloads = [row[0] for row in conn.execute("select payload_json from raw_events")]
    conn.close()
    assert all(TARGET_DIGITS not in p and TARGET_CUSTOMER not in p for p in payloads)
    assert _csv_phones(populated) == [OTHER_PHONE]

    record = next(r for r in caplog.records if r.getMessage().startswith("lead forgotten"))
    assert record.lead_id == target.lead_id and (record.leads, record.notifications, record.raw_events) == (1, 1, 3)
    assert _no_phone(out) and _no_phone(caplog.text)

    # a second run: nothing left to find
    assert forget.run(populated, ["--phone", TARGET_PHONE, "--yes"]) == 2
    assert capsys.readouterr().out.strip() == "not found"


def test_lead_id_selects_the_same_row_and_csv_is_left_alone_when_not_a_backend(populated, capsys):
    settings = populated.model_copy(update={"storage_backends": "sqlite"})
    lead_id = SqliteStore(settings.database_path).get_lead_by_phone(TARGET_PHONE).lead_id
    csv_before = settings.csv_export_path.read_bytes()
    assert forget.run(settings, ["--lead-id", lead_id, "--yes"]) == 0
    out = capsys.readouterr().out
    assert out.strip().splitlines()[-1].endswith("csv=skipped sinks=none")
    assert _counts(settings)["leads"] == 1 and settings.csv_export_path.read_bytes() == csv_before


def test_unknown_phone_lead_id_or_unparseable_number_exit_2_without_echoing_it(populated, capsys):
    for argv in (["--phone", "+4915100000000"], ["--lead-id", "L-nope"], ["--phone", "not-a-number"]):
        assert forget.run(populated, argv) == 2
        assert capsys.readouterr().out.strip() == "not found"
    assert _counts(populated)["leads"] == 2


def test_feishu_mirror_is_deleted_after_search_and_a_failing_sink_exits_1_without_rollback(populated, capsys, caplog):
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path.rsplit("/", 1)[-1]))
        if request.url.path.endswith("/tenant_access_token/internal"):
            return httpx.Response(200, json={"code": 0, "tenant_access_token": "tok", "expire": 7200})
        if request.url.path.endswith("/records/search"):
            return httpx.Response(200, json={"code": 0, "data": {"items": [{"record_id": "recT", "fields": {}}]}})
        if request.method == "DELETE" and request.url.path.endswith("/records/recT"):
            return httpx.Response(200, json={"code": 0, "data": {"deleted": True, "record_id": "recT"}})
        return httpx.Response(404, json={"code": 404, "msg": "unexpected"})

    good = FeishuBitableSink("cli", "sec", "bascnX", "tblX", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert good.delete_lead("L-any") is True
    assert calls == [("POST", "internal"), ("POST", "search"), ("DELETE", "recT")]
    assert "Bearer" not in str(calls)

    # wired through the command: STORAGE_BACKENDS lists feishu_bitable, the fake tenant answers HTTP 500
    settings = populated.model_copy(update={"storage_backends": "sqlite,csv,feishu_bitable", **FEISHU})
    broken = FeishuBitableSink("cli", "sec", "bascnX", "tblX",
                               client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))))
    original = forget.build_sinks

    def fake_build_sinks(names, store, csv_path, *, settings=None):
        return [s if s.name != "feishu_bitable" else broken for s in original(names, store, csv_path, settings=settings)]

    forget.build_sinks = fake_build_sinks
    try:
        assert forget.run(settings, ["--phone", TARGET_PHONE, "--dry-run"]) == 0
        assert "sinks:         feishu_bitable" in capsys.readouterr().out
        with caplog.at_level(logging.ERROR, logger="app.forget"):
            assert forget.run(settings, ["--phone", TARGET_PHONE, "--yes"]) == 1
    finally:
        forget.build_sinks = original
    out = capsys.readouterr().out
    assert out.strip().splitlines()[-1].endswith("csv=rewritten sinks=feishu_bitable=failed")
    assert _counts(settings)["leads"] == 1 and _csv_phones(settings) == [OTHER_PHONE]   # ledger not rolled back
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1 and errors[0].channel == "feishu_bitable" and errors[0].error_type == "FeishuBitableError"
    assert _no_phone(out) and _no_phone(caplog.text)


def test_half_configured_bitable_is_refused_before_anything_is_deleted(populated, capsys):
    settings = populated.model_copy(update={"storage_backends": "sqlite,csv,feishu_bitable", "feishu_app_id": "cli"})
    assert forget.run(settings, ["--phone", TARGET_PHONE, "--yes"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("configuration error:") and "FEISHU_APP_SECRET" in out and _no_phone(out)
    assert _counts(settings)["leads"] == 2


def test_forget_lead_is_the_shared_deletion_path_and_leaves_the_csv_to_its_caller(populated, caplog):
    """`app.retention` deletes every expired lead through this function, then rewrites the CSV once."""
    store = SqliteStore(populated.database_path)
    target = store.get_lead_by_phone(TARGET_PHONE)
    csv_before = populated.csv_export_path.read_bytes()
    broken = FeishuBitableSink("cli", "sec", "bascnX", "tblX",
                               client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))))

    with caplog.at_level(logging.ERROR, logger="app.forget"):
        outcome = forget.forget_lead(store, [broken], target)

    assert outcome["counts"]["leads"] == 1 and outcome["counts"]["notifications"] == 1
    assert outcome["counts"]["raw_events"] == 3
    assert outcome["sink_states"] == ["feishu_bitable=failed"] and outcome["failed"] is True
    assert store.get_lead(target.lead_id) is None and _counts(populated)["leads"] == 1
    assert populated.csv_export_path.read_bytes() == csv_before   # the mirror is the caller's job
    assert _no_phone(caplog.text)


def test_module_entry_point_reads_the_environment(populated):
    env = {**os.environ, "DATABASE_PATH": str(populated.database_path), "CSV_EXPORT_PATH": str(populated.csv_export_path),
           "STORAGE_BACKENDS": "sqlite,csv", "BOTMAKER_WEBHOOK_TOKEN": "t", "NOTIFIERS": ""}
    run = subprocess.run([sys.executable, "-m", "app.forget", "--phone", TARGET_PHONE, "--yes"],
                         cwd=SERVICE_DIR, capture_output=True, text=True, env=env, timeout=120)
    assert run.returncode == 0, run.stderr
    lines = run.stdout.strip().splitlines()
    assert lines[-1].startswith("forgotten lead_id=") and lines[-1].endswith("csv=rewritten sinks=none")
    assert '"msg": "lead forgotten: leads=1 notifications=1 raw_events=3"' in lines[-2]   # JSON log line before the summary
    assert _no_phone(run.stdout + run.stderr)
    assert _counts(populated)["leads"] == 1
