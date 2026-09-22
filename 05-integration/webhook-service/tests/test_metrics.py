"""GET /metrics 与 app.metrics.collect：鉴权、口径、窗口、空库。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.metrics import NOTIFICATION_STATUSES, collect

from webhook_test_helpers import HEADERS, NO_WAIT, RecordingNotifier, load_fixture

KEYS = {"generated_at", "window_hours", "callbacks", "notifications", "raw_events_unprocessed", "last_callback_at",
        "leads_total"}


def _insert_raw(db_path, key: str, received_at: str = "2026-09-22T00:00:00.000+00:00") -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO raw_events (event_key, kind, received_at, payload_json, processed) VALUES (?, 'message', ?, '{}', 0)",
                 (key, received_at))
    conn.commit()
    conn.close()


def test_metrics_requires_the_webhook_token(client: TestClient):
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"auth-bm-token": "nope"}).status_code == 401
    assert client.get("/metrics", headers=HEADERS).status_code == 200


def test_metrics_is_503_when_token_unset(tmp_path):
    app = create_app(Settings(_env_file=None, botmaker_webhook_token="", database_path=tmp_path / "l.db",
                              csv_export_path=tmp_path / "l.csv"), notifiers=[])
    assert TestClient(app).get("/metrics", headers={"auth-bm-token": ""}).status_code == 503


def test_empty_database_is_all_zero(client: TestClient):
    body = client.get("/metrics", headers=HEADERS).json()
    assert set(body) == KEYS
    assert body["window_hours"] == 24 and body["generated_at"].endswith("Z")
    assert body["callbacks"] == {"total": 0, "by_outcome": {"lead_upserted": 0}}
    assert body["notifications"] == {"by_status": {s: 0 for s in NOTIFICATION_STATUSES}, "failed_24h": 0, "pending": 0}
    assert body["raw_events_unprocessed"] == 0 and body["last_callback_at"] is None and body["leads_total"] == 0


def test_counts_after_replaying_fixtures(client: TestClient):
    first = client.post("/webhooks/botmaker", json=load_fixture("message_user_first.json"), headers=HEADERS)
    assert first.status_code == 200
    escalated = client.post("/webhooks/botmaker", json=load_fixture("message_with_variables_b2b.json"), headers=HEADERS)
    assert escalated.json()["status"] == "lead_upserted" and escalated.json()["notification_queued"] is True
    dup = client.post("/webhooks/botmaker", json=load_fixture("message_with_variables_b2b.json"), headers=HEADERS)
    assert dup.json()["status"] == "duplicate"

    body = client.get("/metrics", headers=HEADERS).json()
    assert body["callbacks"]["total"] == 2  # the duplicate never reaches processed_events
    assert body["callbacks"]["by_outcome"]["lead_upserted"] == 2
    assert body["notifications"]["by_status"]["sent"] == 1 and body["notifications"]["failed_24h"] == 0
    assert body["notifications"]["pending"] == 0
    assert body["raw_events_unprocessed"] == 0
    assert body["last_callback_at"] is not None
    assert body["leads_total"] == len(client.app.state.pipeline.store.list_leads()) >= 1


def test_failed_notifications_are_counted(settings: Settings):
    client = TestClient(create_app(settings, notifiers=[RecordingNotifier(fail_times=99)], retry_policy=NO_WAIT))
    response = client.post("/webhooks/botmaker", json=load_fixture("message_with_variables_b2b.json"), headers=HEADERS)
    assert response.json()["notification_queued"] is True
    body = client.get("/metrics", headers=HEADERS).json()
    assert body["notifications"]["by_status"]["failed"] == 1
    assert body["notifications"]["failed_24h"] == 1


def test_unprocessed_raw_event_is_reported(client: TestClient, settings: Settings):
    _insert_raw(settings.database_path, "hash:stuck")
    body = client.get("/metrics", headers=HEADERS).json()
    assert body["raw_events_unprocessed"] == 1
    assert body["last_callback_at"] == "2026-09-22T00:00:00.000+00:00"


def test_hours_query_is_validated(client: TestClient):
    assert client.get("/metrics?hours=1", headers=HEADERS).json()["window_hours"] == 1
    assert client.get("/metrics?hours=168", headers=HEADERS).json()["window_hours"] == 168
    for bad in ("0", "169", "-5", "abc", ""):
        assert client.get(f"/metrics?hours={bad}", headers=HEADERS).status_code == 400, bad


def test_collect_window_excludes_old_rows(client: TestClient, settings: Settings):
    now = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
    old = (now - timedelta(hours=30)).isoformat(timespec="milliseconds")
    recent = (now - timedelta(hours=2)).isoformat(timespec="milliseconds")
    conn = sqlite3.connect(settings.database_path)
    conn.executemany("INSERT INTO processed_events (event_key, processed_at, outcome) VALUES (?, ?, ?)",
                     [("k-old", old, "lead_upserted"), ("k-new", recent, "lead_upserted"), ("k-skip", recent, "skipped_no_contact")])
    conn.executemany("INSERT INTO notifications (lead_id, escalation_reason, session_key, status, created_at) VALUES (?, ?, ?, ?, ?)",
                     [("L-1", "human_requested", "s1", "failed", old), ("L-1", "human_requested", "s2", "failed", recent),
                      ("L-1", "human_requested", "s3", "pending", old)])
    conn.commit()
    conn.close()

    day = collect(settings.database_path, hours=24, now=now)
    assert day["callbacks"] == {"total": 2, "by_outcome": {"lead_upserted": 1, "skipped_no_contact": 1}}
    assert day["notifications"]["by_status"]["failed"] == 2  # by_status is the whole table
    assert day["notifications"]["failed_24h"] == 1 and day["notifications"]["pending"] == 1
    week = collect(settings.database_path, hours=168, now=now)
    assert week["callbacks"]["total"] == 3 and week["notifications"]["failed_24h"] == 2


def test_collect_without_database_file(tmp_path):
    body = collect(tmp_path / "missing.db")
    assert body["leads_total"] == 0 and body["raw_events_unprocessed"] == 0 and body["last_callback_at"] is None
