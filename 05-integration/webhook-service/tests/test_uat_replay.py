"""UAT U01–U20 (06-acceptance/uat-test-cases.md section 2) replayed against the webhook service.

fixtures/uat/manifest.json lists, per case, the Botmaker callbacks to POST in order and what the
service must have done afterwards: the lead stored, how many cards were sent, tags / priority,
source parsing, dedupe. Bot wording, follow-up counts and card latency are checked on site during
UAT, not here; each case's `note` says which part of the UAT row is out of scope for this test.

Manifest vocabulary (`expect`, and per-step `after` checkpoints keyed by callback number):
  lead                dict (or list of dicts matched by `phone`) compared field by field with the
                      stored lead; list fields as sets; fields not listed are not checked
  source              same as `lead`, for source_code / source_channel
  leads_total         number of leads in the store
  notifications       cards the RecordingNotifier delivered
  notifications_total rows in the `notifications` table
  tags                tags the (single) stored lead must carry
  priority            priority of every card sent so far ("high" / "normal" / "")
  status              (after only) `status` of the webhook response for that callback
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

import pytest
from fastapi.testclient import TestClient

from webhook_test_helpers import FIXTURES, HEADERS, RecordingNotifier, load_fixture

UAT = FIXTURES / "uat"
MANIFEST = json.loads((UAT / "manifest.json").read_text(encoding="utf-8"))
CASES: dict[str, dict[str, Any]] = MANIFEST["cases"]
CASE_IDS = [f"U{i:02d}" for i in range(1, 21)]


def _post(client: TestClient, name: str) -> dict[str, Any]:
    response = client.post("/webhooks/botmaker", json=load_fixture(f"uat/{name}"), headers=HEADERS)
    assert response.status_code == 200, f"{name}: HTTP {response.status_code} {response.text}"
    return response.json()


def _notification_rows(client: TestClient) -> int:
    conn = sqlite3.connect(client.app.state.settings.database_path)
    try:
        return int(conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0])
    finally:
        conn.close()


def _pick_lead(leads: list[dict[str, Any]], wanted: dict[str, Any], where: str) -> dict[str, Any]:
    """The stored lead an expectation refers to: by phone when given, else the only one."""
    if "phone" in wanted:
        matches = [lead for lead in leads if lead["phone"] == wanted["phone"]]
        assert len(matches) == 1, f"{where}: expected one lead with phone {wanted['phone']}, store has {[l['phone'] for l in leads]}"
        return matches[0]
    assert len(leads) == 1, f"{where}: expected exactly one lead in the store, found {len(leads)}"
    return leads[0]


def _assert_fields(stored: dict[str, Any], wanted: dict[str, Any], where: str) -> None:
    for name, want in wanted.items():
        assert name in stored, f"{where}: manifest names a field the lead schema does not have: {name}"
        got = stored[name]
        if isinstance(want, list):
            assert set(got) == set(want), f"{where}: {name} = {got!r}, expected {sorted(want)!r}"
        elif isinstance(want, float):
            assert got == pytest.approx(want), f"{where}: {name} = {got!r}, expected {want!r}"
        else:
            assert got == want, f"{where}: {name} = {got!r}, expected {want!r}"


def _check(client: TestClient, notifier: RecordingNotifier, expect: dict[str, Any], where: str,
           response: dict[str, Any] | None = None) -> None:
    leads = [lead.model_dump(mode="json") for lead in client.app.state.pipeline.store.list_leads()]
    for key, want in expect.items():
        if key in ("lead", "source"):
            for wanted in ([want] if isinstance(want, dict) else want):
                _assert_fields(_pick_lead(leads, wanted, where), wanted, f"{where} [{key}]")
        elif key == "leads_total":
            assert len(leads) == want, f"{where}: {len(leads)} leads in the store, expected {want}"
        elif key == "notifications":
            assert len(notifier.cards) == want, f"{where}: {len(notifier.cards)} cards sent, expected {want}"
        elif key == "notifications_total":
            rows = _notification_rows(client)
            assert rows == want, f"{where}: {rows} notification rows, expected {want}"
        elif key == "tags":
            tags = set(_pick_lead(leads, {}, where)["tags"])
            assert set(want) <= tags, f"{where}: tags {sorted(tags)} lack {sorted(set(want) - tags)}"
        elif key == "priority":
            assert notifier.cards, f"{where}: priority expected but no card was sent"
            assert all(card.priority == want for card in notifier.cards), \
                f"{where}: card priorities {[c.priority for c in notifier.cards]}, expected all {want!r}"
        elif key == "status":
            assert response is not None, f"{where}: 'status' is only valid in an 'after' checkpoint"
            assert response["status"] == want, f"{where}: response status {response['status']!r}, expected {want!r}"
        else:
            raise AssertionError(f"{where}: unknown expectation key {key!r}")


def test_manifest_covers_u01_to_u20_and_every_fixture_is_used() -> None:
    assert list(CASES) == CASE_IDS
    referenced = {name for case in CASES.values() for name in case["fixtures"]}
    on_disk = {path.name for path in UAT.glob("U*.json")}
    assert referenced == on_disk, f"unreferenced: {sorted(on_disk - referenced)}, missing: {sorted(referenced - on_disk)}"
    for case_id, case in CASES.items():
        assert case["note"].strip(), f"{case_id}: note is required"
        assert case["expect"], f"{case_id}: expect is required"
        for step in case.get("after", {}):
            assert 1 <= int(step) <= len(case["fixtures"]), f"{case_id}: 'after' step {step} has no callback"


@pytest.mark.parametrize("case_id", CASE_IDS, ids=CASE_IDS)
def test_uat_case(case_id: str, client: TestClient, notifier: RecordingNotifier) -> None:
    case = CASES[case_id]
    checkpoints: dict[str, dict[str, Any]] = case.get("after", {})
    for step, name in enumerate(case["fixtures"], start=1):
        body = _post(client, name)
        if str(step) in checkpoints:
            _check(client, notifier, checkpoints[str(step)], f"{case_id} after callback {step} ({name})", response=body)
    _check(client, notifier, case["expect"], f"{case_id} final")
