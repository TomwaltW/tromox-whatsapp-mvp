from __future__ import annotations

import threading

from app.normalize import new_lead
from app.store import RawEventState, SqliteStore

PHONE = "+4917604069011"


def test_raw_event_states(tmp_path):
    store = SqliteStore(tmp_path / "s.db")
    assert store.record_raw_event("msg:1", "message", "{}") is RawEventState.NEW
    assert store.record_raw_event("msg:1", "message", "{}") is RawEventState.DUPLICATE_UNPROCESSED
    assert store.unprocessed_events() == [("msg:1", "{}")]
    store.mark_processed("msg:1", "lead_upserted")
    assert store.record_raw_event("msg:1", "message", "{}") is RawEventState.DUPLICATE_PROCESSED
    assert store.unprocessed_events() == []


def test_notification_claim_is_unique_per_lead_reason_session(tmp_path):
    store = SqliteStore(tmp_path / "s.db")
    first = store.claim_notification("L-1", "b2b_qualified", "s1", "C1")
    assert first is not None
    assert store.claim_notification("L-1", "b2b_qualified", "s1", "C1") is None
    assert store.claim_notification("L-1", "price_negotiation", "s1", "C1") is not None
    assert store.claim_notification("L-1", "b2b_qualified", "s2", "C1") is not None
    row = store.get_notification(first)
    assert row is not None and row.status == "pending" and row.customer_id == "C1"


def test_update_lead_is_atomic_under_concurrency(tmp_path):
    """Eight callbacks for the same phone at once: no update may be lost."""
    store = SqliteStore(tmp_path / "s.db")
    store.update_lead(PHONE, lambda existing: existing or new_lead(PHONE), customer_id="C1")
    barrier = threading.Barrier(8)

    def worker(index: int) -> None:
        def mutate(existing):
            lead = existing.model_copy(deep=True)
            lead.tags = sorted({*lead.tags, f"t{index}"})
            return lead

        barrier.wait()
        store.update_lead(PHONE, mutate)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    lead = store.get_lead_by_phone(PHONE)
    assert lead is not None and lead.tags == [f"t{i}" for i in range(8)]
    assert store.get_customer_id(lead.lead_id) == "C1"  # a later call without customer_id keeps the known one
    assert len(store.list_leads()) == 1 and store.ping() is True


def test_delete_lead_removes_lead_notifications_and_raw_payloads_with_the_contact_only(tmp_path):
    store = SqliteStore(tmp_path / "s.db")
    other = "+34612345678"
    store.update_lead(PHONE, lambda existing: existing or new_lead(PHONE), customer_id="C1")
    store.update_lead(other, lambda existing: existing or new_lead(other), customer_id="C2")
    target = store.get_lead_by_phone(PHONE)
    assert target is not None
    store.claim_notification(target.lead_id, "b2b_qualified", "s1", "C1")
    store.claim_notification(target.lead_id, "price_negotiation", "s2", "C1")
    store.claim_notification("L-other", "b2b_qualified", "s1", "C2")
    store.record_raw_event("e1", "message", '{"contactId": "4917604069011"}')       # phone digits, payload kept
    store.record_raw_event("e2", "message", '{"customerId": "C1"}')                # customer id, payload kept
    store.record_raw_event("e3", "message", '{"contactId": "4917604069011"}')       # payload blanked -> stays
    store.mark_processed("e3", "lead_upserted")
    store.record_raw_event("e4", "message", '{"contactId": "34612345678"}')         # the other contact
    store.mark_processed("e1", "lead_upserted", keep_payload=True)

    preview = store.lead_footprint(target.lead_id, "4917604069011", "C1")
    assert preview == {"leads": 1, "notifications": 2, "raw_events": 2}
    assert len(store.list_leads()) == 2                                             # the preview changed nothing
    assert store.delete_lead(target.lead_id, "4917604069011", "C1") == preview
    assert store.get_lead(target.lead_id) is None and store.get_lead_by_phone(other) is not None
    assert [row.lead_id for row in store.retryable_notifications()] == ["L-other"]
    assert store.unprocessed_events() == [("e4", '{"contactId": "34612345678"}')]
    assert store.record_raw_event("e3", "message", "{}") is RawEventState.DUPLICATE_PROCESSED   # ledger keeps idempotency
    assert store.delete_lead(target.lead_id, "4917604069011", "C1") == {"leads": 0, "notifications": 0, "raw_events": 0}


def test_delete_lead_with_no_identifiers_never_touches_raw_events(tmp_path):
    store = SqliteStore(tmp_path / "s.db")
    store.record_raw_event("e1", "message", '{"contactId": "4917604069011"}')
    store.record_raw_event("e2", "message", "{}")
    assert store.delete_lead("L-missing", None, "") == {"leads": 0, "notifications": 0, "raw_events": 0}
    assert store.delete_lead("L-missing", " ", None)["raw_events"] == 0
    assert len(store.unprocessed_events()) == 2
