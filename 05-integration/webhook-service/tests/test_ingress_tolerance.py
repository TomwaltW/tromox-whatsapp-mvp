"""Callback field types that differ from the fixtures must not lose leads.

- Type drift the model is built to absorb (epoch-ms `date`, `variables: null`, numeric `operatorId` /
  `contactId`, object `clientPayload`, `null` lists) is processed like the fixture itself.
- A shape it cannot absorb is a processing failure, not an outcome: the raw callback stays in
  `raw_events` unprocessed (payload kept, `error` = "validation: <field paths>"), is counted in
  `/metrics` raw_events_unprocessed, a redelivery is tried again instead of answered `duplicate`,
  and `app.replay` recovers it under the key it was stored with once the model is fixed.
"""
from __future__ import annotations

import copy
import json
import logging
import sqlite3
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import field_validator

import app.pipeline as pipeline_mod
from app.logging_setup import JsonFormatter
from app.models import BotmakerWebhook
from app.replay import replay

from webhook_test_helpers import HEADERS, load_fixture

PHONE_DIGITS = "4917604069011"
COMPANY = "Nordrad Mobility GmbH"


def _b2b(mutate=None) -> dict:
    payload = load_fixture("message_with_variables_b2b.json")
    if mutate is not None:
        mutate(payload)
    return payload


def _post(client: TestClient, payload: dict) -> dict:
    response = client.post("/webhooks/botmaker", json=payload, headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json()


def _rows(client: TestClient, sql: str):
    conn = sqlite3.connect(client.app.state.settings.database_path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def _unprocessed(client: TestClient) -> int:
    return client.get("/metrics", headers=HEADERS).json()["raw_events_unprocessed"]


def _assert_b2b_lead(client: TestClient, body: dict):
    assert body["status"] == "lead_upserted" and body["kind"] == "message", body
    lead = client.app.state.pipeline.store.get_lead(body["lead_id"])
    assert lead is not None and lead.phone == "+" + PHONE_DIGITS
    assert lead.company == COMPANY and lead.segment.value == "B2B" and lead.b2b_type.value == "distributor"
    assert body["notification_queued"] is True
    assert _unprocessed(client) == 0
    return lead


# ------------------------------------------------------------------ type drift that is absorbed
def test_epoch_millisecond_date_is_parsed(client):
    lead = _assert_b2b_lead(client, _post(client, _b2b(lambda d: d["messages"][0].__setitem__("date", 1762283523120))))
    assert lead.first_message_ts == datetime(2025, 11, 4, 19, 12, 3, 120000, tzinfo=timezone.utc)


def test_null_variables_are_treated_as_empty(client):
    body = _post(client, _b2b(lambda d: d.__setitem__("variables", None)))
    assert body["status"] == "lead_upserted", body
    lead = client.app.state.pipeline.store.get_lead(body["lead_id"])
    # without variables there is nothing B2B to extract, but the lead itself is not lost
    assert lead is not None and lead.phone == "+" + PHONE_DIGITS and lead.company is None
    assert _unprocessed(client) == 0


def test_numeric_operator_id_is_accepted(client):
    _assert_b2b_lead(client, _post(client, _b2b(lambda d: d["messages"][0].__setitem__("operatorId", 12345))))


def test_numeric_contact_id_becomes_the_phone(client):
    _assert_b2b_lead(client, _post(client, _b2b(lambda d: d.__setitem__("contactId", int(PHONE_DIGITS)))))


def test_object_client_payload_is_accepted(client):
    _assert_b2b_lead(client, _post(client, _b2b(
        lambda d: d["messages"][0].__setitem__("clientPayload", {"button": "b2b", "id": 3}))))


def test_null_lists_in_event_and_status_callbacks(client):
    event = load_fixture("event_conversation_close.json")
    event["events"].append({"name": "conversation-close", "info": None})
    assert _post(client, event)["status"] == "lead_upserted"
    status = load_fixture("status_delivered.json")
    status["error"] = None
    assert _post(client, status)["status"] == "ignored_status"
    assert _unprocessed(client) == 0


# ------------------------------------------------------------------ shapes that are not
def test_unparseable_callback_is_kept_unprocessed_and_counted(client):
    bad = _b2b(lambda d: d.__setitem__("messages", "not a list"))
    first = _post(client, bad)
    assert first == {"status": "stored_unprocessed", "kind": "unknown", "lead_id": None, "notification_queued": False}
    (key, processed, payload_json, error), = _rows(client, "SELECT event_key, processed, payload_json, error FROM raw_events")
    assert key.startswith("hash:") and processed == 0
    assert json.loads(payload_json) == bad                         # the original is kept for the replay
    assert error == "validation: messages (list_type)" and PHONE_DIGITS not in error
    assert _rows(client, "SELECT COUNT(*) FROM processed_events") == [(0,)]
    assert _unprocessed(client) == 1                               # -> the health alert goes degraded
    assert client.app.state.pipeline.store.list_leads() == []

    again = _post(client, bad)                                     # a redelivery is tried again, not "duplicate"
    assert again["status"] == "stored_unprocessed"
    assert _rows(client, "SELECT COUNT(*), SUM(processed) FROM raw_events") == [(1, 0)]
    assert _unprocessed(client) == 1


def test_validation_warning_carries_field_paths_but_no_values(client, caplog):
    bad = _b2b(lambda d: d.__setitem__("variables", ["oops", PHONE_DIGITS]))
    with caplog.at_level(logging.INFO):
        assert _post(client, bad)["status"] == "stored_unprocessed"
    warnings = [r for r in caplog.records if getattr(r, "outcome", None) == "stored_unprocessed"]
    assert len(warnings) == 1
    record = warnings[0]
    assert record.levelno == logging.WARNING and record.exc_info is None
    assert record.error_type == "ValidationError" and record.reason == "variables (dict_type)"
    line = JsonFormatter().format(record)
    for text in (repr(record.__dict__), line):
        assert PHONE_DIGITS not in text and COMPANY not in text and "Nordrad" not in text
    assert json.loads(line)["reason"] == "variables (dict_type)"


def test_many_validation_errors_are_capped(client):
    bad = _b2b(lambda d: d.__setitem__("messages", [{"_id_": f"M{i}", "date": [i]} for i in range(12)]))
    assert _post(client, bad)["status"] == "stored_unprocessed"
    (error,), = _rows(client, "SELECT error FROM raw_events")
    # 3 errors per message (the date union has three members); only the first 10 are listed
    assert error.startswith("validation: messages.0.date.str (string_type); ") and error.endswith("; +26 more")
    assert error.count("(") == 10 and len(error) <= 500


# ------------------------------------------------------------------ replay
class _FixedWebhook(BotmakerWebhook):
    """Stands in for the model after the fix: accepts `variables` sent as a list."""

    @field_validator("variables", mode="before")
    @classmethod
    def _list_variables(cls, value):
        return {} if isinstance(value, list) else value


def test_replay_after_the_model_fix_recovers_under_the_stored_key(client, notifier, monkeypatch):
    bad = _b2b(lambda d: d.__setitem__("variables", ["oops"]))
    assert _post(client, bad)["status"] == "stored_unprocessed"
    (stored_key,), = _rows(client, "SELECT event_key FROM raw_events")
    assert stored_key.startswith("hash:") and _unprocessed(client) == 1

    pipeline = client.app.state.pipeline
    assert replay(pipeline)["events"] == 1                         # model not fixed yet: stays put, same key
    assert _rows(client, "SELECT event_key, processed FROM raw_events") == [(stored_key, 0)]

    monkeypatch.setattr(pipeline_mod, "BotmakerWebhook", _FixedWebhook)
    assert replay(pipeline) == {"events": 1, "notifications": 0, "mirrors": 0, "mirrors_reset": 0}
    assert _unprocessed(client) == 0
    (lead,) = pipeline.store.list_leads()
    assert lead.phone == "+" + PHONE_DIGITS and notifier.calls == 0    # no escalation variables in this payload
    # both keys count as processed: the stored hash key, and the one the fixed model computes now (its
    # raw_events row is only the duplicate marker: payload dropped, the original row is the record)
    fresh_key = pipeline_mod.compute_event_key(bad, _FixedWebhook.model_validate(bad))
    assert fresh_key == "msg:TRXDEMOMSG0000000006+TRXDEMOMSG0000000007"
    assert _rows(client, "SELECT event_key, processed, payload_json, error FROM raw_events ORDER BY id") == \
        [(stored_key, 1, None, None), (fresh_key, 1, None, None)]
    assert sorted(_rows(client, "SELECT event_key, outcome FROM processed_events")) == \
        sorted([(stored_key, "lead_upserted"), (fresh_key, "lead_upserted")])

    # Botmaker redelivering the same message is a duplicate under the fixed model ...
    assert _post(client, bad)["status"] == "duplicate"
    monkeypatch.setattr(pipeline_mod, "BotmakerWebhook", BotmakerWebhook)
    # ... and under the old one (hash key) as well
    assert _post(client, bad)["status"] == "duplicate"
    assert len(pipeline.store.list_leads()) == 1 and _rows(client, "SELECT COUNT(*) FROM raw_events") == [(2,)]


def test_handle_uses_the_given_event_key(client):
    pipeline = client.app.state.pipeline
    result = pipeline.handle(copy.deepcopy(_b2b()), event_key="hash:given")
    assert result.outcome == "lead_upserted" and result.event_key == "hash:given"
    fresh_key = "msg:TRXDEMOMSG0000000006+TRXDEMOMSG0000000007"
    assert _rows(client, "SELECT event_key, processed FROM raw_events ORDER BY id") == [("hash:given", 1), (fresh_key, 1)]
    assert sorted(k for k, in _rows(client, "SELECT event_key FROM processed_events")) == ["hash:given", fresh_key]
    assert _post(client, _b2b())["status"] == "duplicate"


# ------------------------------------------------------------------ transport
@pytest.mark.parametrize("body", [b"[" * 5000, b'{"a":' * 5000])
def test_deeply_nested_json_is_400(client, body):
    response = client.post("/webhooks/botmaker", content=body,
                           headers={**HEADERS, "content-type": "application/json"})
    assert response.status_code == 400 and response.json() == {"detail": "body is not valid JSON"}
    assert _rows(client, "SELECT COUNT(*) FROM raw_events") == [(0,)]
