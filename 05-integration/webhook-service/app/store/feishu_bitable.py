"""Feishu Bitable (飞书多维表格) sink: mirrors every lead upsert into one row of one table.

SQLite stays the ledger; the Bitable is the copy the sales team opens. One row per lead,
keyed by the `lead_id` column: search the table for that lead_id, then update the record
found or create a new one. Any failure raises `FeishuBitableError`; `pipeline._process`
logs and swallows it, so the ledger and the notification are never held up by the mirror.

Column name = field name in `tromox_lead.LEAD_FIELDS`; column type <- lead field:
    文本      <- lead_id (去重键), phone, contact_name, profile_name, company, role, city_region,
                 volume, existing_dealer_relationship, source_code, ai_summary, assigned_to, notes
    单选      <- segment, b2b_type, b2c_intent, status, source_channel, escalation_reason,
                 language, country_by_phone, country_stated
    多选      <- product_interest, tags
    数字      <- ai_confidence
    复选框    <- escalation_flag, consent_marketing
    日期      <- first_message_ts, last_message_ts (毫秒时间戳)
    文本(JSON) <- referral
A field whose value is None is left out of the request: a Bitable cell is never sent as null.

Requests (all JSON):
    POST {base}/open-apis/auth/v3/tenant_access_token/internal        -> tenant token, cached
    POST .../bitable/v1/apps/{app_token}/tables/{table_id}/records/search  filter lead_id = ...
    POST .../records                 create   {"fields": {...}}
    PUT  .../records/{record_id}     update   {"fields": {...}}
The token is cached for `expire - 300` seconds; a token-invalid error code (99991661,
99991663) drops the cache and retries the data request once. The request shapes follow the
public Bitable open API documentation and have NOT been checked against a real tenant
(README §8). Error messages never contain the app secret or the tenant token.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

import httpx
from pydantic import BaseModel

from tromox_lead import LEAD_FIELDS, Lead

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)      # same values as notify/_http.py
TOKEN_SAFETY_MARGIN_SECONDS = 300                       # refresh this long before Feishu says it expires
TOKEN_INVALID_CODES = frozenset({99991661, 99991663})   # tenant token expired / invalid: refetch once
_TOKEN_PATH = "/open-apis/auth/v3/tenant_access_token/internal"


class FeishuBitableError(RuntimeError):
    """Raised for any transport, HTTP or API-level failure. Never carries a secret."""


def _to_millis(value: datetime) -> int:
    if value.tzinfo is None:  # the store only holds UTC datetimes; never interpret a naive one as local time
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def lead_to_fields(lead: Lead) -> dict[str, Any]:
    """Convert a lead into the `fields` object of a Bitable record (see module docstring)."""
    fields: dict[str, Any] = {}
    for name in LEAD_FIELDS:
        value = getattr(lead, name, None)
        if value is None:
            continue
        if isinstance(value, Enum):
            fields[name] = value.value
        elif isinstance(value, bool):
            fields[name] = value
        elif isinstance(value, datetime):
            fields[name] = _to_millis(value)
        elif isinstance(value, BaseModel):
            fields[name] = json.dumps(value.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        elif isinstance(value, dict):
            fields[name] = json.dumps(value, ensure_ascii=False, sort_keys=True)
        elif isinstance(value, (list, tuple)):
            fields[name] = [str(item) for item in value]
        elif isinstance(value, (int, float)):
            fields[name] = float(value)
        else:
            fields[name] = str(value)
    return fields


class FeishuBitableSink:
    name = "feishu_bitable"

    def __init__(self, app_id: str, app_secret: str, app_token: str, table_id: str, *,
                 client: httpx.Client | None = None, clock: Callable[[], float] = time.time,
                 base_url: str = "https://open.feishu.cn") -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._base_url = base_url.rstrip("/")
        self._records_url = f"{self._base_url}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        self._client = client or httpx.Client(timeout=DEFAULT_TIMEOUT)
        self._clock = clock
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._lock = threading.Lock()  # one upsert at a time: two threads must not both create the same lead

    # --- public -------------------------------------------------------------------------

    def upsert_lead(self, lead: Lead) -> None:
        fields = lead_to_fields(lead)
        with self._lock:
            record_id = self._find_record(lead.lead_id)
            if record_id is None:
                self._request("create", "POST", self._records_url, {"fields": fields})
            else:
                self._request("update", "PUT", f"{self._records_url}/{record_id}", {"fields": fields})

    # --- Bitable calls --------------------------------------------------------------------

    def _find_record(self, lead_id: str) -> str | None:
        body = {
            "field_names": ["lead_id"],
            "filter": {"conjunction": "and",
                       "conditions": [{"field_name": "lead_id", "operator": "is", "value": [lead_id]}]},
            "page_size": 1,
        }
        data = self._request("search", "POST", f"{self._records_url}/search", body)
        items = (data.get("data") or {}).get("items") or []
        for item in items:
            record_id = item.get("record_id") if isinstance(item, dict) else None
            if record_id:
                return str(record_id)
        return None

    def _request(self, step: str, method: str, url: str, body: dict[str, Any]) -> dict[str, Any]:
        """One authenticated data request; on a token-invalid code, refetch the token and retry once."""
        data = self._send(step, method, url, body, token=self._tenant_token())
        code = data.get("code")
        if code in TOKEN_INVALID_CODES:
            self._token = None
            data = self._send(step, method, url, body, token=self._tenant_token())
            code = data.get("code")
        if code != 0:
            raise FeishuBitableError(f"feishu_bitable: {step} code={code} msg={data.get('msg')}")
        return data

    def _tenant_token(self) -> str:
        now = self._clock()
        if self._token is None or now >= self._token_expires_at:
            data = self._send("tenant_access_token", "POST", f"{self._base_url}{_TOKEN_PATH}",
                              {"app_id": self._app_id, "app_secret": self._app_secret}, token=None)
            token = data.get("tenant_access_token")
            if data.get("code") != 0 or not token:
                raise FeishuBitableError(f"feishu_bitable: tenant_access_token code={data.get('code')} msg={data.get('msg')}")
            try:
                expire = float(data.get("expire", 7200))
            except (TypeError, ValueError):
                expire = 7200.0
            self._token = str(token)
            self._token_expires_at = now + max(expire - TOKEN_SAFETY_MARGIN_SECONDS, 0.0)
        return self._token

    def _send(self, step: str, method: str, url: str, body: dict[str, Any], *, token: str | None) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            if method == "PUT":
                response = self._client.put(url, json=body, headers=headers)
            else:
                response = self._client.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise FeishuBitableError(f"feishu_bitable: {step} transport error {type(exc).__name__}") from None
        if not 200 <= response.status_code < 300:
            raise FeishuBitableError(f"feishu_bitable: {step} HTTP {response.status_code}")
        try:
            data = response.json()
        except ValueError:
            raise FeishuBitableError(f"feishu_bitable: {step} response is not JSON") from None
        if not isinstance(data, dict):
            raise FeishuBitableError(f"feishu_bitable: {step} response is not a JSON object")
        return data
