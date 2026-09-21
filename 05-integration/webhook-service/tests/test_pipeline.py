from __future__ import annotations

import asyncio
import csv
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.pipeline import compute_event_key
from app.replay import replay
from app.store import build_sinks
from tromox_lead import LEAD_FIELDS, LeadStatus, lead_id_for_contact

from webhook_test_helpers import HEADERS, NO_WAIT, RecordingNotifier, load_fixture


def _post(client: TestClient, name_or_payload):
    payload = load_fixture(name_or_payload) if isinstance(name_or_payload, str) else name_or_payload
    response = client.post("/webhooks/botmaker", json=payload, headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json()


def _rows(client: TestClient, sql: str):
    conn = sqlite3.connect(client.app.state.settings.database_path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def test_same_payload_twice_gives_one_lead_and_one_notification(client, notifier):
    _post(client, "message_user_first.json")
    first = _post(client, "message_with_variables_b2b.json")
    again = _post(client, "message_with_variables_b2b.json")
    assert first["status"] == "lead_upserted" and first["notification_queued"] is True
    assert again["status"] == "duplicate" and again["notification_queued"] is False
    assert len(client.app.state.pipeline.store.list_leads()) == 1
    assert _rows(client, "SELECT COUNT(*) FROM notifications")[0][0] == 1
    assert notifier.calls == 1 and len(notifier.cards) == 1


def test_notification_is_once_per_lead_reason_and_session(client, notifier):
    _post(client, "message_with_variables_b2b.json")
    follow_up = load_fixture("message_with_variables_b2b.json")
    follow_up["messages"] = [{"_id_": "TRXDEMOMSG0000000009", "date": "2026-11-04T19:20:00.000Z", "from": "user",
                              "message": "One more thing: we also rent scooters."}]
    assert _post(client, follow_up)["notification_queued"] is False       # same session, same reason
    new_session = dict(follow_up, sessionId="TRXDEMOCUSTOMER00001_2026-11-20T08:00:00.000Z")
    new_session["messages"] = [dict(follow_up["messages"][0], _id_="TRXDEMOMSG0000000050")]
    assert _post(client, new_session)["notification_queued"] is True      # a later session notifies again
    assert notifier.calls == 2


def test_b2c_faq_does_not_notify(client, notifier):
    body = _post(client, "message_b2c_faq.json")
    assert body["status"] == "lead_upserted" and body["notification_queued"] is False and notifier.calls == 0


def test_contact_without_phone_number_is_recorded_by_customer_id_not_guessed(client, notifier):
    payload = load_fixture("message_with_variables_b2b.json")
    payload["contactId"] = "US.ab12025550143"          # an id that merely contains digits
    payload["whatsappNumber"] = "000000000000"          # never a customer number
    body = _post(client, payload)
    assert body["status"] == "lead_upserted" and body["notification_queued"] is True
    leads = client.app.state.pipeline.store.list_leads()
    assert len(leads) == 1
    lead = leads[0]
    assert lead.phone is None and lead.country_by_phone is None     # nothing guessed from the id
    assert lead.lead_id == lead_id_for_contact(f"bm:{payload['customerId']}")
    assert notifier.calls == 1                                      # a B2B lead is never dropped
    assert _post(client, payload)["status"] == "duplicate"


def test_callback_without_any_contact_identity_is_skipped(client):
    payload = load_fixture("message_user_first.json")
    payload["contactId"] = "US.ab12025550143"
    payload["whatsappNumber"] = "000000000000"
    payload.pop("customerId", None)
    assert _post(client, payload)["status"] == "skipped_no_contact"
    assert client.app.state.pipeline.store.list_leads() == []


def test_other_channels_are_skipped(client):
    payload = load_fixture("message_user_first.json")
    payload["chatPlatform"] = "instagram"
    assert _post(client, payload)["status"] == "skipped_no_contact"


def test_oversized_body_is_rejected(client):
    huge = {"type": "message", "padding": "x" * 1_100_000}
    response = client.post("/webhooks/botmaker", json=huge, headers=HEADERS)
    assert response.status_code == 413


def test_status_callback_is_stored_and_ignored(client):
    assert _post(client, "status_delivered.json")["status"] == "ignored_status"
    assert client.app.state.pipeline.store.list_leads() == []


def test_close_event_updates_status_via_http(client):
    _post(client, "message_user_first.json")
    _post(client, "message_with_variables_b2b.json")
    assert _post(client, "event_conversation_close.json")["status"] == "lead_upserted"
    lead = client.app.state.pipeline.store.list_leads()[0]
    assert lead.status is LeadStatus.CONTACTED and lead.assigned_to == "Li Wei"
    assert lead.company == "Nordrad Mobility GmbH"  # the event did not blank anything


def test_csv_export_mirrors_the_lead_table(client):
    _post(client, "message_user_first.json")
    _post(client, "message_with_variables_b2b.json")
    _post(client, "message_b2c_faq.json")
    path = client.app.state.settings.csv_export_path
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert tuple(rows[0].keys()) == LEAD_FIELDS and len(rows) == 2
    german = next(r for r in rows if r["phone"] == "+4917604069011")
    assert german["product_interest"] == "MC10;UKKO" and german["escalation_flag"] == "true"
    assert not list(path.parent.glob(".leads-*.tmp"))  # atomic swap leaves no temp file behind


def test_raw_payload_is_dropped_after_processing_by_default(client):
    _post(client, "message_user_first.json")
    assert _rows(client, "SELECT processed, payload_json FROM raw_events") == [(1, None)]
    assert _rows(client, "SELECT outcome FROM processed_events") == [("lead_upserted",)]


def test_raw_payload_can_be_kept_during_the_trial(tmp_path):
    settings = Settings(_env_file=None, botmaker_webhook_token="test-token", keep_raw_payloads=True,
                        database_path=tmp_path / "l.db", csv_export_path=tmp_path / "l.csv")
    client = TestClient(create_app(settings, notifiers=[]))
    _post(client, "message_user_first.json")
    (processed, payload_json), = _rows(client, "SELECT processed, payload_json FROM raw_events")
    assert processed == 1 and json.loads(payload_json)["contactId"] == "4917604069011"


def test_processing_failure_answers_200_and_replay_recovers(client, notifier, monkeypatch):
    pipeline = client.app.state.pipeline
    original = pipeline.store.update_lead
    monkeypatch.setattr(pipeline.store, "update_lead", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk hiccup")))
    body = _post(client, "message_with_variables_b2b.json")
    assert body["status"] == "stored_unprocessed" and pipeline.store.list_leads() == []
    assert _rows(client, "SELECT processed, payload_json IS NOT NULL, error FROM raw_events") == [(0, 1, "RuntimeError: disk hiccup")]

    monkeypatch.setattr(pipeline.store, "update_lead", original)
    assert replay(pipeline) == {"events": 1, "notifications": 0}
    assert len(pipeline.store.list_leads()) == 1 and notifier.calls == 1
    assert _rows(client, "SELECT processed FROM raw_events") == [(1,)]


def test_notifier_failure_never_breaks_the_webhook_and_is_retryable(settings):
    broken = RecordingNotifier("feishu", fail_times=99)
    client = TestClient(create_app(settings, notifiers=[broken], retry_policy=NO_WAIT))
    assert _post(client, "message_with_variables_b2b.json")["notification_queued"] is True
    assert broken.calls == 3                                                   # bounded retries
    assert _rows(client, "SELECT status, attempts, last_error FROM notifications") == [
        ("failed", 3, "feishu: simulated failure")]

    pipeline = client.app.state.pipeline
    healthy = RecordingNotifier("feishu")
    pipeline.notifiers = [healthy]
    assert replay(pipeline) == {"events": 0, "notifications": 1}
    assert len(healthy.cards) == 1
    assert _rows(client, "SELECT status, attempts FROM notifications") == [("sent", 4)]


def test_partial_and_skipped_delivery_states(settings, tmp_path):
    ok, bad = RecordingNotifier("wecom"), RecordingNotifier("email", fail_times=99)
    client = TestClient(create_app(settings, notifiers=[ok, bad], retry_policy=NO_WAIT))
    _post(client, "message_with_variables_b2b.json")
    assert _rows(client, "SELECT status, channels_ok FROM notifications") == [("partial", "wecom")]

    other = Settings(_env_file=None, botmaker_webhook_token="test-token",
                     database_path=tmp_path / "other.db", csv_export_path=tmp_path / "other.csv")
    silent = TestClient(create_app(other, notifiers=[]))
    _post(silent, "message_with_variables_b2b.json")
    assert _rows(silent, "SELECT status FROM notifications") == [("skipped",)]


def test_handle_itself_never_calls_a_notifier(client, notifier):
    result = client.app.state.pipeline.handle(load_fixture("message_with_variables_b2b.json"))
    assert result.notification_id is not None and notifier.calls == 0


def test_response_is_sent_before_the_notifier_runs(app, notifier):
    """Latency: the HTTP reply must not wait for Feishu / WeCom / SMTP."""
    order: list[str] = []
    notifier.on_send = lambda: order.append("notifier.send")
    body = json.dumps(load_fixture("message_with_variables_b2b.json")).encode("utf-8")
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "scheme": "http",
        "path": "/webhooks/botmaker", "raw_path": b"/webhooks/botmaker", "query_string": b"", "root_path": "",
        "headers": [(b"auth-bm-token", b"test-token"), (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode())],
        "client": ("127.0.0.1", 50000), "server": ("127.0.0.1", 8000),
    }

    async def run() -> None:
        sent = False

        async def receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.sleep(3600)

        async def send(message):
            order.append(message["type"])

        await app(scope, receive, send)

    asyncio.run(run())
    assert order.index("http.response.body") < order.index("notifier.send")
    assert order.count("notifier.send") == 1


def test_event_key_is_stable_and_ignores_the_fixture_note():
    payload = load_fixture("event_conversation_close.json")
    without_note = {k: v for k, v in payload.items() if k != "_note"}
    assert compute_event_key(payload, None) == compute_event_key(without_note, None)
    assert compute_event_key(payload, None).startswith("hash:")


def test_stub_and_unknown_storage_backends_fail_fast(client, tmp_path):
    store = client.app.state.pipeline.store
    for name in ("feishu_bitable", "gsheets"):
        with pytest.raises(NotImplementedError):
            build_sinks([name], store, tmp_path / "x.csv")
    with pytest.raises(ValueError):
        build_sinks(["mongodb"], store, tmp_path / "x.csv")


def test_logs_are_json_and_contain_no_full_phone_number(capsys, settings):
    # build the app while capsys is active, so the JSON log handler writes to the captured stdout
    client = TestClient(create_app(settings, notifiers=[RecordingNotifier()], retry_policy=NO_WAIT))
    capsys.readouterr()
    _post(client, "message_with_variables_b2b.json")
    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    assert lines, "expected structured log lines on stdout"
    records = [json.loads(line) for line in lines]
    assert any(r.get("outcome") == "lead_upserted" and r.get("lead_id", "").startswith("L-") for r in records)
    assert "4917604069011" not in "\n".join(lines)
