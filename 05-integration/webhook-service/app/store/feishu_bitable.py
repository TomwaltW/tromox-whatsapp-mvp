"""STUB - Feishu Bitable (飞书多维表格) sink. NOT implemented in the MVP.

Reserved so the interface is stable. Selecting `feishu_bitable` in STORAGE_BACKENDS fails
fast at start-up instead of silently dropping leads.

Planned field mapping (Bitable column type <- lead field):
    文本      <- lead_id (用作去重键), phone, company, contact_name, role, city_region,
                 volume, existing_dealer_relationship, source_code, ai_summary, assigned_to, notes
    单选      <- segment, b2b_type, b2c_intent, status, source_channel, escalation_reason,
                 language, country_by_phone, country_stated
    多选      <- product_interest, tags
    数字      <- ai_confidence
    复选框    <- escalation_flag, consent_marketing
    日期      <- first_message_ts, last_message_ts
    文本(JSON) <- referral
Implementation notes for phase 2: upsert = search by lead_id then create/update a record
through the Bitable open API with a tenant access token (app id / secret via env); respect
the API rate limit; keep SQLite as the ledger and treat Bitable as a mirror only.
"""
from __future__ import annotations

from tromox_lead import Lead


class FeishuBitableSink:
    name = "feishu_bitable"

    def __init__(self) -> None:
        raise NotImplementedError(
            "feishu_bitable storage is a documented stub (phase 2). Use STORAGE_BACKENDS=sqlite,csv."
        )

    def upsert_lead(self, lead: Lead) -> None:  # pragma: no cover - unreachable
        raise NotImplementedError
