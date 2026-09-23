from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models import BotmakerWebhook
from app.normalize import (
    collect_message_facts,
    extract_phone,
    map_variables,
    merge_events,
    merge_message,
    parse_ts,
)
from tromox_lead import B2BType, B2CIntent, EscalationReason, LeadStatus, Segment, SourceChannel

from webhook_test_helpers import FIXTURES, load_fixture

DE_PHONE = "+4917604069011"


def _message(name: str, existing=None, tier: str = "full"):
    payload = BotmakerWebhook.model_validate(load_fixture(name))
    phone = extract_phone(payload)
    assert phone is not None
    return merge_message(existing, phone, collect_message_facts(payload), tier)


def _payload(variables: dict, text: str = "hello", contact: str = "4917604069011", msg_id: str = "X1",
             sender: str = "user", date: str = "2026-11-04T20:00:00.000Z", **extra) -> BotmakerWebhook:
    return BotmakerWebhook.model_validate({
        "v": "1.1", "type": "message", "chatPlatform": "whatsapp", "contactId": contact, "customerId": "C1",
        "sessionId": "C1_s1", "messages": [{"_id_": msg_id, "date": date, "from": sender, "message": text}],
        "variables": variables, **extra,
    })


def _merge(payload: BotmakerWebhook, existing=None, tier: str = "full"):
    return merge_message(existing, extract_phone(payload), collect_message_facts(payload), tier)


def test_every_fixture_is_a_known_kind():
    kinds = {path.name: BotmakerWebhook.model_validate(load_fixture(path.name)).kind for path in FIXTURES.glob("*.json")}
    assert kinds == {
        "message_user_first.json": "message", "message_with_variables_b2b.json": "message",
        "message_b2c_faq.json": "message", "message_camelcase_variables.json": "message",
        "event_conversation_close.json": "event", "status_delivered.json": "status",
    }


def test_first_message_short_code_country_language_and_fallback_name():
    lead = _message("message_user_first.json")
    assert lead.phone == DE_PHONE and lead.country_by_phone == "DE" and lead.country_stated is None
    assert (lead.source_code, lead.source_channel) == ("IG-2609", SourceChannel.INSTAGRAM)
    assert lead.language == "und"                      # the English prefill says nothing about the customer's language
    assert lead.profile_name == "Jonas K" and lead.contact_name is None   # profile name is display-only, not a contact
    assert lead.segment is Segment.UNKNOWN and lead.status is LeadStatus.NEW
    assert lead.escalation_flag is False and lead.escalation_reason is None
    assert lead.first_message_ts == lead.last_message_ts == datetime(2026, 11, 4, 19, 12, 3, 120000, tzinfo=timezone.utc)
    assert {"country_de", "seg_unknown", "src_instagram", "stage_new"} <= set(lead.tags)
    assert not [tag for tag in lead.tags if tag.startswith("lang_")]


def test_fallback_detection_waits_for_the_customers_own_words():
    first = _message("message_user_first.json")
    assert first.language == "und"
    own = _merge(_payload({}, text="Hallo, ich möchte Händler werden, bitte schicken Sie mir die Preise",
                          msg_id="X2", date="2026-11-04T19:13:00.000Z"), existing=first)
    assert own.lead_id == first.lead_id and own.language == "de" and "lang_de" in own.tags


def test_legacy_mexican_whatsapp_number_keeps_phone_and_country():
    payload = load_fixture("message_with_variables_b2b.json")
    payload.update(contactId="5215512345678", customerId="MX0001")
    payload.pop("whatsappNumber", None)
    lead = _merge(BotmakerWebhook.model_validate(payload))
    assert lead.phone == "+525512345678" and lead.country_by_phone == "MX"
    assert "country_de" in lead.tags  # the stated market (DE) still wins for the tag


def test_short_message_without_language_variable_stays_und_not_un():
    lead = _merge(_payload({}, text="ok"))
    assert lead.language == "und"
    later = _merge(_payload({"segment": "B2C"}, text="ok", msg_id="X2"), existing=lead)
    assert later.language == "und" and not [tag for tag in later.tags if tag.startswith("lang_")]


def test_qualified_b2b_merges_into_the_same_lead():
    first = _message("message_user_first.json")
    lead = _message("message_with_variables_b2b.json", existing=first)
    assert lead.lead_id == first.lead_id
    assert lead.segment is Segment.B2B and lead.b2b_type is B2BType.DISTRIBUTOR and lead.b2c_intent is None
    assert lead.country_stated == "DE" and lead.city_region == "Hamburg"
    assert lead.company == "Nordrad Mobility GmbH" and lead.contact_name == "Jonas Keller"  # AI value; profile name kept apart
    assert lead.profile_name == "Jonas K"
    assert lead.product_interest == ["MC10", "UKKO"] and lead.volume == "about 40 units per year"
    assert lead.ai_confidence == pytest.approx(0.95)
    assert lead.escalation_flag and lead.escalation_reason is EscalationReason.B2B_QUALIFIED
    assert lead.status is LeadStatus.QUALIFIED
    assert lead.source_code == "IG-2609"                                       # first touch kept
    assert lead.first_message_ts == first.first_message_ts
    assert lead.last_message_ts == datetime(2026, 11, 4, 19, 16, 40, tzinfo=timezone.utc)  # user message, not the bot reply
    assert {"b2b_distributor", "prio_high", "prod_mc10", "prod_ukko", "stage_qualified"} <= set(lead.tags)


def test_b2c_faq_needs_no_human():
    lead = _message("message_b2c_faq.json")
    assert lead.country_by_phone == "US" and lead.segment is Segment.B2C and lead.b2c_intent is B2CIntent.TEST_RIDE
    assert lead.b2b_type is None and lead.product_interest == ["MC10"]
    assert lead.escalation_flag is False and lead.escalation_reason is None and lead.status is LeadStatus.NEW


def test_camelcase_variables_and_json_array_products():
    lead = _message("message_camelcase_variables.json")
    assert lead.country_by_phone == "ES" and lead.country_stated == "ES" and lead.city_region == "Valencia"
    assert lead.segment is Segment.B2B and lead.b2b_type is B2BType.DEALER and lead.product_interest == ["M05"]
    assert lead.escalation_reason is EscalationReason.PRICE_NEGOTIATION and lead.consent_marketing is False
    assert (lead.source_code, lead.source_channel) == ("TT-2610B", SourceChannel.TIKTOK)
    assert lead.language == "es"


def test_close_event_writes_status_back():
    lead = _message("message_with_variables_b2b.json", existing=_message("message_user_first.json"))
    events = BotmakerWebhook.model_validate(load_fixture("event_conversation_close.json")).events
    closed, unmapped = merge_events(lead, lead.phone, events)
    assert closed.status is LeadStatus.CONTACTED and closed.assigned_to == "Li Wei" and unmapped == []
    assert "stage_contacted" in closed.tags and "stage_qualified" not in closed.tags


@pytest.mark.parametrize("typification,status", [
    ("won", LeadStatus.CLOSED_WON), ("Lost", LeadStatus.CLOSED_LOST), ("nurture", LeadStatus.NURTURE),
    ("Not a lead", LeadStatus.INVALID), ("qualified-followup", LeadStatus.CONTACTED),
])
def test_typification_mapping(typification, status):
    payload = BotmakerWebhook.model_validate({"type": "event", "events": [
        {"name": "conversation-close", "info": [{"name": "typification", "value": typification}]}]})
    lead, unmapped = merge_events(None, DE_PHONE, payload.events)
    assert lead.status is status and unmapped == []


def test_unknown_typification_keeps_status_and_is_reported():
    payload = BotmakerWebhook.model_validate({"type": "event", "events": [
        {"name": "conversation-close", "info": [{"name": "typification", "value": "something else"}]}]})
    lead, unmapped = merge_events(None, DE_PHONE, payload.events)
    assert lead.status is LeadStatus.NEW and unmapped == ["something else"]


def test_assignment_event_marks_handed_off():
    payload = BotmakerWebhook.model_validate({"type": "event", "events": [
        {"name": "assigned-to-agent", "info": [{"name": "agentName", "value": "Li Wei"}]}]})
    lead, _ = merge_events(None, DE_PHONE, payload.events)
    assert lead.status is LeadStatus.HANDED_OFF and lead.assigned_to == "Li Wei"


def test_agent_message_means_contacted():
    lead = _merge(_payload({}, text="Hello, this is Tromox sales.", sender="agent"))
    assert lead.status is LeadStatus.NEW  # no operator info on that message -> nothing to record
    payload = BotmakerWebhook.model_validate({
        "type": "message", "chatPlatform": "whatsapp", "contactId": "4917604069011",
        "messages": [{"_id_": "A1", "date": "2026-11-05T01:00:00Z", "from": "agent", "fromName": "Li Wei", "message": "Hi"}]})
    lead = _merge(payload)
    assert lead.status is LeadStatus.CONTACTED and lead.assigned_to == "Li Wei"
    assert lead.last_message_ts is None  # agent messages never move the customer-window clock


def test_button_press_alone_is_not_low_confidence():
    lead = _merge(_payload({"segment": "B2B"}))
    assert lead.segment is Segment.B2B and lead.ai_confidence == 0.0
    assert lead.escalation_flag is False and lead.escalation_reason is None


def test_explicit_low_confidence_escalates():
    lead = _merge(_payload({"segment": "B2C", "ai_confidence": "0.4"}))
    assert lead.escalation_flag and lead.escalation_reason is EscalationReason.LOW_CONFIDENCE


def test_empty_values_never_overwrite_and_unknown_never_downgrades():
    known = _message("message_with_variables_b2b.json", existing=_message("message_user_first.json"))
    later = _merge(_payload({"segment": "unknown", "company": "", "contact_name": "null", "product_interest": "",
                             "country_stated": None, "volume": "n/a"}, msg_id="X2"), existing=known)
    assert later.segment is Segment.B2B and later.b2b_type is B2BType.DISTRIBUTOR
    assert later.company == "Nordrad Mobility GmbH" and later.contact_name == "Jonas Keller"
    assert later.product_interest == ["MC10", "UKKO"] and later.country_stated == "DE"
    assert later.volume == "about 40 units per year" and later.ai_confidence == pytest.approx(0.95)
    assert later.escalation_flag and later.escalation_reason is EscalationReason.B2B_QUALIFIED


def test_segment_change_clears_the_other_branch():
    b2b = _merge(_payload({"segment": "B2B", "b2b_type": "dealer", "ai_confidence": "0.9"}))
    b2c = _merge(_payload({"segment": "B2C", "b2c_intent": "buy", "ai_confidence": "0.9"}, msg_id="X2"), existing=b2b)
    assert b2c.segment is Segment.B2C and b2c.b2b_type is None and b2c.b2c_intent is B2CIntent.BUY
    assert "b2b_dealer" not in b2c.tags


def test_one_invalid_variable_does_not_discard_the_rest():
    lead = _merge(_payload({"segment": "B2B", "b2b_type": "retailer", "company": "Moto Sur", "ai_confidence": "0.9"}))
    assert lead.segment is Segment.B2B and lead.b2b_type is None and lead.company == "Moto Sur"


def test_first_touch_source_is_kept():
    first = _merge(_payload({}, text="Hi Tromox! [IG-2609]"))
    second = _merge(_payload({}, text="Hi Tromox! [FB-2610]", msg_id="X2"), existing=first)
    assert second.source_code == "IG-2609" and second.source_channel is SourceChannel.INSTAGRAM


def test_only_the_first_customer_message_is_scanned_for_a_short_code():
    first = _merge(_payload({}, text="Hello, do you ship to Spain?"))
    later = _merge(_payload({}, text="I used to ride an AD-2023 scooter", msg_id="X2",
                            date="2026-11-04T20:05:00.000Z"), existing=first)
    assert later.source_code is None and later.source_channel is SourceChannel.UNKNOWN


def test_bot_greeting_arriving_first_does_not_block_short_code_parsing():
    greeted = _merge(_payload({}, text="Welcome to Tromox.", sender="bot"))
    assert greeted.first_message_ts is None
    lead = _merge(_payload({}, text="Hi Tromox! [YT-2610]", msg_id="X2"), existing=greeted)
    assert (lead.source_code, lead.source_channel) == ("YT-2610", SourceChannel.YOUTUBE)


def test_source_code_variable_is_used_when_text_has_none():
    lead = _merge(_payload({"source_code": "qr-2611"}, text="hello"))
    assert (lead.source_code, lead.source_channel) == ("QR-2611", SourceChannel.OFFLINE_QR)


def test_lite_tier_limits_tags():
    lead = _message("message_with_variables_b2b.json", existing=_message("message_user_first.json"), tier="lite")
    assert lead.tags == ["country_de", "seg_b2b"]


def test_referral_passthrough_sets_ctwa_channel():
    payload = _payload({}, text="Hello", referral={"sourceType": "ad", "sourceId": "120000000000001",
                                                   "sourceUrl": "https://fb.me/example", "headline": "Become a dealer"})
    lead = _merge(payload)
    assert lead.referral is not None and lead.referral.source_id == "120000000000001"
    assert lead.source_channel is SourceChannel.CTWA_AD


def test_non_whatsapp_platform_has_no_phone():
    payload = BotmakerWebhook.model_validate({"type": "message", "chatPlatform": "messenger", "contactId": "1234567890123"})
    assert extract_phone(payload) is None


def test_phone_extraction_is_strict():
    def phone(**fields):
        return extract_phone(BotmakerWebhook.model_validate({"chatPlatform": "whatsapp", **fields}))

    assert phone(contactId="551150392540") == "+551150392540"
    assert phone(contactId="+49 176 0406-9011") == "+4917604069011"
    assert phone(contactId="US.ab12025550143") is None                      # contains digits, is not a number
    assert phone(contactId="BSUID-XYZ", whatsappNumber="12025550143") == "+12025550143"
    assert phone(contactId="BSUID-XYZ", whatsappNumber="551149331774",
                 chatChannelId="demo-whatsapp-551149331774") is None        # company line, not the customer


def test_lead_json_variable_is_accepted_and_individual_variables_win():
    mapped = map_variables({"lead_json": '{"segment": "B2B", "company": "From Blob", "b2bType": "fleet"}',
                            "company": "From Variable", "unrelated": "x"})
    assert mapped == {"segment": "B2B", "company": "From Variable", "b2b_type": "fleet"}


@pytest.mark.parametrize("value,expected", [
    ("2026-11-04T19:12:03.120Z", datetime(2026, 11, 4, 19, 12, 3, 120000, tzinfo=timezone.utc)),
    ("2026-11-05T03:12:03+08:00", datetime(2026, 11, 4, 19, 12, 3, tzinfo=timezone.utc)),
    (1793819523000, datetime.fromtimestamp(1793819523, tz=timezone.utc)),
    ("not a date", None), (None, None),
])
def test_parse_ts(value, expected):
    assert parse_ts(value) == expected
