"""Feishu Bitable sink against a fake Bitable (httpx.MockTransport). No network.

The request shapes are the ones written down in app/store/feishu_bitable.py; they follow the
public open API documentation and are not yet confirmed against a real tenant (README §8).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import pytest

from app.config import Settings
from app.pipeline import Pipeline
from app.store import SqliteStore, build_sinks
from app.store.feishu_bitable import FeishuBitableError, FeishuBitableSink, lead_to_fields
from tromox_lead import B2BType, EscalationReason, Lead, Referral, Segment

from webhook_test_helpers import NO_WAIT, RecordingNotifier, load_fixture

APP_SECRET = "s3cr3t-app-secret"
TOKENS = ["tok-one", "tok-two", "tok-three"]
APP_TOKEN, TABLE_ID = "bascnFAKE", "tblFAKE"
RECORDS = f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"


class FakeBitable:
    """Token endpoint + search / create / update on one table. Records every request."""

    def __init__(self, *, fail_code: int | None = None, expired_once: bool = False) -> None:
        self.fail_code = fail_code
        self.expired_once = expired_once     # first data request answers "token expired"
        self.calls: list[tuple[str, str, dict, dict]] = []   # method, path, headers, body
        self.records: dict[str, dict] = {}
        self.tokens_issued = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content or b"{}")
        self.calls.append((request.method, request.url.path, dict(request.headers), body))
        path = request.url.path
        if path.endswith("/auth/v3/tenant_access_token/internal"):
            self.tokens_issued += 1
            return httpx.Response(200, json={"code": 0, "msg": "ok", "tenant_access_token": TOKENS[self.tokens_issued - 1],
                                             "expire": 7200})
        if self.expired_once:
            self.expired_once = False
            return httpx.Response(200, json={"code": 99991663, "msg": "access token expired"})
        if self.fail_code is not None:
            return httpx.Response(200, json={"code": self.fail_code, "msg": "simulated failure"})
        if request.method == "POST" and path == RECORDS + "/search":
            wanted = json.dumps(body)
            items = [{"record_id": rid, "fields": f} for rid, f in self.records.items() if f["lead_id"] in wanted]
            return httpx.Response(200, json={"code": 0, "data": {"items": items, "has_more": False}})
        if request.method == "POST" and path == RECORDS:
            rid = f"rec{len(self.records) + 1}"
            self.records[rid] = dict(body["fields"])
            return httpx.Response(200, json={"code": 0, "data": {"record": {"record_id": rid}}})
        if request.method == "PUT" and path.startswith(RECORDS + "/"):
            rid = path.rsplit("/", 1)[1]
            self.records[rid] = dict(body["fields"])
            return httpx.Response(200, json={"code": 0, "data": {"record": {"record_id": rid}}})
        if request.method == "DELETE" and path.startswith(RECORDS + "/"):
            rid = path.rsplit("/", 1)[1]
            if rid not in self.records:
                return httpx.Response(200, json={"code": 1254005, "msg": "RecordIdNotFound"})
            del self.records[rid]
            return httpx.Response(200, json={"code": 0, "data": {"deleted": True, "record_id": rid}})
        return httpx.Response(404, json={"code": 404, "msg": f"unexpected {request.method} {path}"})

    def data_calls(self) -> list[tuple[str, str]]:
        return [(m, p.rsplit("/", 1)[-1]) for m, p, _, _ in self.calls if "tenant_access_token" not in p]


def _sink(fake: FakeBitable, clock=None) -> FeishuBitableSink:
    client = httpx.Client(transport=httpx.MockTransport(fake.handler))
    kwargs = {"clock": clock} if clock else {}
    return FeishuBitableSink("cli_fake", APP_SECRET, APP_TOKEN, TABLE_ID, client=client, **kwargs)


def _lead(**overrides) -> Lead:
    base = dict(lead_id="L-feishu-1", phone="+4915112345678", country_by_phone="DE", language="de",
                contact_name="Anna Keller", profile_name="Anna K", company="Moto Nord GmbH",
                segment=Segment.B2B, b2b_type=B2BType.DEALER, product_interest=["MC10", "UKKO"],
                ai_confidence=0.9, escalation_flag=True, escalation_reason=EscalationReason.B2B_QUALIFIED,
                first_message_ts=datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc),
                last_message_ts=datetime(2026, 11, 10, 9, 5, tzinfo=timezone.utc),
                tags=["seg_b2b", "prio_high"], consent_marketing=None,
                referral=Referral(source_id="ad-1", headline="MC10 launch"))
    base.update(overrides)
    return Lead(**base)


def test_upsert_twice_fetches_one_token_then_searches_creates_searches_updates():
    fake = FakeBitable()
    sink = _sink(fake)
    sink.upsert_lead(_lead())
    sink.upsert_lead(_lead(company="Moto Nord GmbH & Co"))
    assert fake.tokens_issued == 1
    assert fake.data_calls() == [("POST", "search"), ("POST", "records"), ("POST", "search"), ("PUT", "rec1")]
    assert all(h["authorization"] == "Bearer tok-one" for _, p, h, _ in fake.calls if "tenant_access_token" not in p)
    assert "authorization" not in fake.calls[0][2]
    assert fake.calls[0][3] == {"app_id": "cli_fake", "app_secret": APP_SECRET}
    search_body = json.dumps(fake.calls[1][3])
    assert "lead_id" in search_body and "L-feishu-1" in search_body
    assert len(fake.records) == 1 and fake.records["rec1"]["company"] == "Moto Nord GmbH & Co"


def test_fields_follow_the_bitable_column_types_and_never_carry_null():
    fields = lead_to_fields(_lead())
    assert fields["lead_id"] == "L-feishu-1" and fields["profile_name"] == "Anna K"     # 文本
    assert fields["segment"] == "B2B" and fields["b2b_type"] == "dealer"                # 单选: enum .value
    assert fields["status"] == "new" and fields["source_channel"] == "unknown"
    assert fields["product_interest"] == ["MC10", "UKKO"] and fields["tags"] == ["seg_b2b", "prio_high"]  # 多选
    assert fields["ai_confidence"] == 0.9 and isinstance(fields["ai_confidence"], float)   # 数字
    assert fields["escalation_flag"] is True                                            # 复选框
    assert fields["first_message_ts"] == 1_794_301_200_000 and fields["last_message_ts"] == 1_794_301_500_000  # 日期: ms
    assert json.loads(fields["referral"])["source_id"] == "ad-1"                         # 文本(JSON)
    for absent in ("consent_marketing", "b2c_intent", "notes", "assigned_to", "country_stated"):
        assert absent not in fields
    assert None not in fields.values()
    assert set(fields) <= set(Lead.model_fields)


def test_naive_datetimes_are_read_as_utc():
    fields = lead_to_fields(_lead(first_message_ts=datetime(2026, 11, 10, 9, 0)))
    assert fields["first_message_ts"] == 1_794_301_200_000


def test_token_is_cached_until_expiry_minus_safety_margin():
    now = [1_000_000.0]
    fake = FakeBitable()
    sink = _sink(fake, clock=lambda: now[0])
    sink.upsert_lead(_lead())
    now[0] += 6_899                       # still inside expire - 300
    sink.upsert_lead(_lead())
    assert fake.tokens_issued == 1
    now[0] += 1                           # exactly at expire - 300: refetch
    sink.upsert_lead(_lead())
    assert fake.tokens_issued == 2
    assert fake.calls[-1][2]["authorization"] == "Bearer tok-two"


def test_expired_token_code_drops_the_cache_and_retries_the_request_once():
    fake = FakeBitable(expired_once=True)
    sink = _sink(fake)
    sink.upsert_lead(_lead())
    assert fake.tokens_issued == 2
    assert fake.data_calls() == [("POST", "search"), ("POST", "search"), ("POST", "records")]
    assert [h["authorization"] for _, p, h, _ in fake.calls if "tenant_access_token" not in p] == \
        ["Bearer tok-one", "Bearer tok-two", "Bearer tok-two"]


def test_delete_lead_searches_then_deletes_the_record_and_is_false_when_absent():
    fake = FakeBitable()
    sink = _sink(fake)
    sink.upsert_lead(_lead())
    assert sink.delete_lead("L-feishu-1") is True
    assert fake.records == {}
    assert fake.data_calls()[-2:] == [("POST", "search"), ("DELETE", "rec1")]
    method, path, headers, body = fake.calls[-1]
    assert headers["authorization"] == "Bearer tok-one" and body == {}
    assert sink.delete_lead("L-feishu-1") is False           # second request: nothing left to delete
    assert fake.data_calls()[-1] == ("POST", "search") and fake.tokens_issued == 1


def test_delete_lead_failure_raises_without_secret():
    fake = FakeBitable()
    sink = _sink(fake)
    sink.upsert_lead(_lead())
    fake.fail_code = 1254005
    with pytest.raises(FeishuBitableError) as info:
        sink.delete_lead("L-feishu-1")
    assert str(info.value).startswith("feishu_bitable: search code=1254005") and APP_SECRET not in str(info.value)


def test_api_error_code_raises_and_the_message_carries_no_secret():
    fake = FakeBitable(fail_code=1254000)
    with pytest.raises(FeishuBitableError) as info:
        _sink(fake).upsert_lead(_lead())
    message = str(info.value)
    assert message.startswith("feishu_bitable: search code=1254000 msg=")
    assert APP_SECRET not in message and "tok-one" not in message


def test_http_and_token_failures_raise_without_secret():
    with pytest.raises(FeishuBitableError, match=r"feishu_bitable: tenant_access_token HTTP 500"):
        FeishuBitableSink("cli", APP_SECRET, APP_TOKEN, TABLE_ID,
                          client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))).upsert_lead(_lead())

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 10003, "msg": "invalid app_secret"})

    with pytest.raises(FeishuBitableError) as info:
        FeishuBitableSink("cli", APP_SECRET, APP_TOKEN, TABLE_ID,
                          client=httpx.Client(transport=httpx.MockTransport(refuse))).upsert_lead(_lead())
    assert "code=10003" in str(info.value) and APP_SECRET not in str(info.value)


def test_sink_failure_never_blocks_the_ledger(settings):
    store = SqliteStore(settings.database_path)
    broken = FeishuBitableSink("cli", APP_SECRET, APP_TOKEN, TABLE_ID,
                               client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))))
    pipeline = Pipeline(settings, store, [broken], [RecordingNotifier()], retry_policy=NO_WAIT)
    result = pipeline.handle(load_fixture("uat/U01a.json"))
    assert result.outcome == "lead_upserted" and len(store.list_leads()) == 1

    fake = FakeBitable()
    good = Pipeline(settings, SqliteStore(settings.database_path.with_name("good.db")), [_sink(fake)],
                    [RecordingNotifier()], retry_policy=NO_WAIT)
    assert good.handle(load_fixture("uat/U01a.json")).outcome == "lead_upserted"
    assert fake.data_calls() == [("POST", "search"), ("POST", "records")]


def test_build_sinks_keeps_the_old_signature_and_refuses_a_half_configured_bitable(settings, tmp_path):
    store = SqliteStore(settings.database_path)
    assert [s.name for s in build_sinks(["sqlite", "csv"], store, tmp_path / "x.csv")] == ["csv"]
    with pytest.raises(ValueError, match="FEISHU_APP_ID"):
        build_sinks(["sqlite", "csv", "feishu_bitable"], store, tmp_path / "x.csv")
    partial = settings.model_copy(update={"feishu_app_id": "cli", "feishu_app_secret": APP_SECRET,
                                          "feishu_bitable_app_token": APP_TOKEN})
    with pytest.raises(ValueError) as info:
        build_sinks(["feishu_bitable"], store, tmp_path / "x.csv", settings=partial)
    assert "FEISHU_BITABLE_TABLE_ID" in str(info.value) and "FEISHU_APP_ID" not in str(info.value)
    assert APP_SECRET not in str(info.value)


def test_build_sinks_with_full_settings_builds_csv_and_bitable(settings, tmp_path):
    full = settings.model_copy(update={"feishu_app_id": "cli", "feishu_app_secret": APP_SECRET,
                                       "feishu_bitable_app_token": APP_TOKEN, "feishu_bitable_table_id": TABLE_ID})
    sinks = build_sinks(["sqlite", "csv", "feishu_bitable"], SqliteStore(settings.database_path), tmp_path / "x.csv",
                        settings=full)
    assert [s.name for s in sinks] == ["csv", "feishu_bitable"]
    assert isinstance(sinks[1], FeishuBitableSink)


def test_settings_read_the_four_feishu_variables(monkeypatch, tmp_path):
    monkeypatch.setenv("FEISHU_APP_ID", "cli_env")
    monkeypatch.setenv("FEISHU_APP_SECRET", "env-secret")
    monkeypatch.setenv("FEISHU_BITABLE_APP_TOKEN", "bascnENV")
    monkeypatch.setenv("FEISHU_BITABLE_TABLE_ID", "tblENV")
    monkeypatch.setenv("STORAGE_BACKENDS", "sqlite,csv,feishu_bitable")
    settings = Settings(_env_file=None, botmaker_webhook_token="t",
                        database_path=tmp_path / "leads.db", csv_export_path=tmp_path / "leads.csv")
    assert (settings.feishu_app_id, settings.feishu_bitable_table_id) == ("cli_env", "tblENV")
    assert settings.storage_backend_list == ["sqlite", "csv", "feishu_bitable"]
