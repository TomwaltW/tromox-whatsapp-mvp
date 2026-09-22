"""python -m app.retention: the scheduled half of the retention promise in compliance.md section 4.

The ledger is built by hand (not through the pipeline) because these tests are about the clock:
`last_message_ts` 800 days back, an `updated_at` 800 days back with no message timestamp at all,
a processed callback 100 days old, an orphan notification. Nothing here may print a phone number.
"""
from __future__ import annotations

import csv
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from app import retention
from app.config import Settings
from app.store import CsvExportSink, SqliteStore
from app.store.feishu_bitable import FeishuBitableSink

from tromox_lead import B2BType, Lead, LeadStatus, Segment

NOW = "2026-12-01"
BASE = datetime(2026, 12, 1, tzinfo=timezone.utc)
PHONES = {"old": "+4915100000001", "recent": "+4915100000002", "nots": "+4915100000003"}
FEISHU = {"feishu_app_id": "cli", "feishu_app_secret": "sec", "feishu_bitable_app_token": "bascnX",
          "feishu_bitable_table_id": "tblX"}


def _settings(tmp_path: Path, **overrides) -> Settings:
    return Settings(_env_file=None, botmaker_webhook_token="t", database_path=tmp_path / "leads.db",
                    csv_export_path=tmp_path / "leads.csv", storage_backends="sqlite,csv", **overrides)


def _add_lead(settings: Settings, lead: Lead, phone: str, updated_days_ago: int) -> None:
    store = SqliteStore(settings.database_path)
    store.update_lead(phone, lambda _existing: lead)
    _sql(settings, "update leads set updated_at = ? where lead_id = ?",
         ((BASE - timedelta(days=updated_days_ago)).isoformat(), lead.lead_id))


def _sql(settings: Settings, statement: str, params: tuple = ()) -> None:
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(statement, params)
        conn.commit()
    finally:
        conn.close()


def _raw_event(settings: Settings, key: str, days_ago: int, processed: int, payload: str | None = None) -> None:
    _sql(settings, "insert into raw_events (event_key, kind, received_at, payload_json, processed) "
                   "values (?, 'message', ?, ?, ?)",
         (key, (BASE - timedelta(days=days_ago)).isoformat(), payload, processed))


def _counts(settings: Settings) -> dict[str, int]:
    conn = sqlite3.connect(settings.database_path)
    try:
        return {table: conn.execute(f"select count(*) from {table}").fetchone()[0]
                for table in ("leads", "notifications", "raw_events")}
    finally:
        conn.close()


def _lead_ids(settings: Settings) -> list[str]:
    conn = sqlite3.connect(settings.database_path)
    try:
        return sorted(row[0] for row in conn.execute("select lead_id from leads"))
    finally:
        conn.close()


def _csv_rows(settings: Settings) -> list[dict[str, str]]:
    with settings.csv_export_path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _no_phone(text: str) -> bool:
    return all(phone not in text and phone.lstrip("+") not in text for phone in PHONES.values())


@pytest.fixture
def ledger(tmp_path: Path) -> Settings:
    """Three leads (two expired, one fresh), three raw callbacks (one expired), one orphan notification."""
    settings = _settings(tmp_path)
    _add_lead(settings, Lead(lead_id="L-old", phone=PHONES["old"], segment=Segment.B2B, b2b_type=B2BType.DEALER,
                             last_message_ts=BASE - timedelta(days=800)), PHONES["old"], 800)
    _add_lead(settings, Lead(lead_id="L-recent", phone=PHONES["recent"], segment=Segment.B2C,
                             last_message_ts=BASE - timedelta(days=10)), PHONES["recent"], 10)
    # no last_message_ts at all: the row's updated_at decides
    _add_lead(settings, Lead(lead_id="L-nots", phone=PHONES["nots"], segment=Segment.B2B, b2b_type=B2BType.DEALER),
              PHONES["nots"], 800)
    _raw_event(settings, "hash:old", 100, processed=1)
    _raw_event(settings, "hash:new", 5, processed=1)
    _raw_event(settings, "hash:unprocessed", 200, processed=0, payload="{}")   # still work to do: app.replay owns it
    _sql(settings, "insert into notifications (lead_id, escalation_reason, session_key, status, attempts, created_at) "
                   "values ('L-gone', 'b2b_qualified', 's', 'sent', 1, ?)",
         ((BASE - timedelta(days=300)).isoformat(),))
    CsvExportSink(SqliteStore(settings.database_path), settings.csv_export_path, min_interval_s=0).export()
    return settings


def test_dry_run_counts_what_is_due_per_segment_and_changes_nothing(ledger, capsys):
    before, csv_before = _counts(ledger), ledger.csv_export_path.read_bytes()
    assert before == {"leads": 3, "notifications": 1, "raw_events": 3}

    assert retention.run(ledger, ["--now", NOW, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "  leads:         2" in out and "    B2B:         2" in out
    assert "  raw_events:    1" in out and "  notifications: 1" in out
    assert "dry run: nothing changed" in out
    assert out.strip().splitlines()[-1] == "retention leads=2 raw_events=1 notifications=1 csv=rewritten sinks=none"

    assert _counts(ledger) == before and ledger.csv_export_path.read_bytes() == csv_before


def test_neither_dry_run_nor_yes_prints_the_plan_exits_3_and_changes_nothing(ledger, capsys):
    before, csv_before = _counts(ledger), ledger.csv_export_path.read_bytes()
    assert retention.run(ledger, ["--now", NOW]) == 3
    out = capsys.readouterr().out
    assert "add --yes to execute" in out
    assert out.strip().splitlines()[-1].startswith("retention leads=2 ")
    assert _counts(ledger) == before and ledger.csv_export_path.read_bytes() == csv_before


def test_yes_deletes_expired_leads_events_and_orphan_notifications_and_rewrites_the_csv(ledger, capsys):
    assert retention.run(ledger, ["--now", NOW, "--yes"]) == 0
    out = capsys.readouterr().out
    assert out.strip().splitlines()[-1] == "retention leads=2 raw_events=1 notifications=1 csv=rewritten sinks=none"

    assert _lead_ids(ledger) == ["L-recent"]
    # hash:old is gone; hash:new is inside its window and hash:unprocessed is not processed yet
    conn = sqlite3.connect(ledger.database_path)
    try:
        assert sorted(row[0] for row in conn.execute("select event_key from raw_events")) == ["hash:new", "hash:unprocessed"]
    finally:
        conn.close()
    assert _counts(ledger)["notifications"] == 0
    assert [row["lead_id"] for row in _csv_rows(ledger)] == ["L-recent"]


def test_a_handed_off_lead_past_the_cutoff_is_deleted_like_any_other(tmp_path, capsys):
    settings = _settings(tmp_path)
    for lead_id, status in (("L-handed", LeadStatus.HANDED_OFF), ("L-contacted", LeadStatus.CONTACTED)):
        phone = f"+49151000009{'1' if lead_id == 'L-handed' else '2'}0"
        _add_lead(settings, Lead(lead_id=lead_id, phone=phone, segment=Segment.B2B, b2b_type=B2BType.DEALER,
                                 status=status, last_message_ts=BASE - timedelta(days=900)), phone, 900)
    assert retention.run(settings, ["--now", NOW, "--yes"]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1].startswith("retention leads=2 ")
    assert _lead_ids(settings) == []


def test_custom_windows_shift_both_cutoffs(ledger, capsys):
    assert retention.run(ledger, ["--now", NOW, "--older-than-days", "5", "--raw-events-days", "1", "--yes"]) == 0
    out = capsys.readouterr().out
    assert out.strip().splitlines()[-1] == "retention leads=3 raw_events=2 notifications=1 csv=rewritten sinks=none"
    assert _lead_ids(ledger) == [] and _csv_rows(ledger) == []
    assert _counts(ledger)["raw_events"] == 1      # the unprocessed callback still stays


def test_nothing_due_and_an_empty_ledger_both_report_zeros_and_exit_0(tmp_path, capsys):
    empty = _settings(tmp_path / "empty")
    SqliteStore(empty.database_path)
    assert retention.run(empty, ["--now", NOW, "--yes"]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == (
        "retention leads=0 raw_events=0 notifications=0 csv=skipped sinks=none")

    fresh = _settings(tmp_path / "fresh")
    _add_lead(fresh, Lead(lead_id="L-recent", phone=PHONES["recent"], segment=Segment.B2C,
                          last_message_ts=BASE - timedelta(days=10)), PHONES["recent"], 10)
    csv_sink = CsvExportSink(SqliteStore(fresh.database_path), fresh.csv_export_path, min_interval_s=0)
    csv_sink.export()
    csv_before = fresh.csv_export_path.read_bytes()
    assert retention.run(fresh, ["--now", NOW, "--yes"]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1].startswith("retention leads=0 ")
    assert _lead_ids(fresh) == ["L-recent"] and fresh.csv_export_path.read_bytes() == csv_before


def test_no_phone_number_reaches_stdout_or_the_log(ledger, capsys, caplog):
    with caplog.at_level(logging.INFO, logger="app.retention"):
        assert retention.run(ledger, ["--now", NOW, "--dry-run"]) == 0
        assert retention.run(ledger, ["--now", NOW, "--yes"]) == 0
    out = capsys.readouterr().out
    assert out and _no_phone(out) and _no_phone(caplog.text)
    finished = [record for record in caplog.records if record.getMessage() == "retention finished"]
    assert len(finished) == 2                                   # one line per run, counts only
    assert (finished[-1].leads, finished[-1].raw_events, finished[-1].notifications) == (2, 1, 1)
    assert not hasattr(finished[-1], "lead_id")


def test_a_failing_mirror_is_logged_and_exits_1_without_rolling_the_ledger_back(ledger, capsys, caplog):
    settings = ledger.model_copy(update={"storage_backends": "sqlite,csv,feishu_bitable", **FEISHU})
    broken = FeishuBitableSink("cli", "sec", "bascnX", "tblX",
                               client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))))
    original = retention.build_sinks

    def fake_build_sinks(names, store, csv_path, *, settings=None):
        return [s if s.name != "feishu_bitable" else broken for s in original(names, store, csv_path, settings=settings)]

    retention.build_sinks = fake_build_sinks
    try:
        assert retention.run(settings, ["--now", NOW, "--dry-run"]) == 0
        assert capsys.readouterr().out.strip().splitlines()[-1].endswith("csv=rewritten sinks=feishu_bitable")
        with caplog.at_level(logging.ERROR, logger="app.forget"):
            assert retention.run(settings, ["--now", NOW, "--yes"]) == 1
    finally:
        retention.build_sinks = original
    out = capsys.readouterr().out
    assert out.strip().splitlines()[-1].endswith("csv=rewritten sinks=feishu_bitable=ok0/failed2")
    assert _lead_ids(settings) == ["L-recent"]                  # the ledger is not rolled back
    errors = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert len(errors) == 2 and {record.channel for record in errors} == {"feishu_bitable"}
    assert _no_phone(out) and _no_phone(caplog.text)


def test_half_configured_bitable_is_refused_before_anything_is_deleted(ledger, capsys):
    settings = ledger.model_copy(update={"storage_backends": "sqlite,csv,feishu_bitable", "feishu_app_id": "cli"})
    assert retention.run(settings, ["--now", NOW, "--yes"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("configuration error:") and "FEISHU_APP_SECRET" in out
    assert _counts(settings)["leads"] == 3
