from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.security import ip_allowed, verify_token

from webhook_test_helpers import HEADERS, load_fixture


def test_health_reports_components_without_secrets(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert body["webhook_token_configured"] is True
    assert body["storage"] == ["sqlite", "csv"] and body["notifiers"] == ["recording"]
    assert "test-token" not in response.text


def test_missing_token_is_401(client: TestClient):
    assert client.post("/webhooks/botmaker", json=load_fixture("message_user_first.json")).status_code == 401


def test_wrong_token_is_401(client: TestClient):
    response = client.post("/webhooks/botmaker", json=load_fixture("message_user_first.json"),
                           headers={"auth-bm-token": "nope"})
    assert response.status_code == 401
    assert client.app.state.pipeline.store.list_leads() == []  # nothing stored for an unauthenticated call


def test_right_token_is_200(client: TestClient):
    response = client.post("/webhooks/botmaker", json=load_fixture("message_user_first.json"), headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "lead_upserted"


def test_unset_token_refuses_with_503(tmp_path):
    app = create_app(Settings(_env_file=None, botmaker_webhook_token="", database_path=tmp_path / "l.db",
                              csv_export_path=tmp_path / "l.csv"), notifiers=[])
    client = TestClient(app)
    response = client.post("/webhooks/botmaker", json={}, headers={"auth-bm-token": ""})
    assert response.status_code == 503
    assert client.get("/health").json()["webhook_token_configured"] is False


def test_invalid_json_and_non_object_are_400(client: TestClient):
    bad = client.post("/webhooks/botmaker", content=b"{not json", headers={**HEADERS, "content-type": "application/json"})
    assert bad.status_code == 400
    array = client.post("/webhooks/botmaker", json=[1, 2], headers=HEADERS)
    assert array.status_code == 400


def test_allowed_ips_blocks_other_callers(tmp_path):
    settings = Settings(_env_file=None, botmaker_webhook_token="t", allowed_ips="203.0.113.0/24",
                        database_path=tmp_path / "l.db", csv_export_path=tmp_path / "l.csv")
    client = TestClient(create_app(settings, notifiers=[]))  # TestClient's peer is not in the allowlist
    response = client.post("/webhooks/botmaker", json=load_fixture("message_user_first.json"),
                           headers={"auth-bm-token": "t"})
    assert response.status_code == 403


def test_ip_allowlist_rules():
    assert ip_allowed("198.51.100.7", []) is True
    assert ip_allowed("203.0.113.9", ["203.0.113.0/24"]) is True
    assert ip_allowed("203.0.113.9", ["203.0.113.9"]) is True
    assert ip_allowed("198.51.100.7", ["203.0.113.0/24", "not-an-ip"]) is False
    assert ip_allowed(None, ["203.0.113.0/24"]) is False
    assert ip_allowed("testclient", ["203.0.113.0/24"]) is False


def test_verify_token():
    assert verify_token("abc", "abc") is True
    assert verify_token("abd", "abc") is False
    assert verify_token(None, "abc") is False
    assert verify_token("", "") is False  # an unset secret never matches


def test_no_interactive_docs_exposed(client: TestClient):
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
