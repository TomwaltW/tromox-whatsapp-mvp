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
