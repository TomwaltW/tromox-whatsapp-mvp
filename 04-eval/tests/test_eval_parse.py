from __future__ import annotations

import json

import pytest
from eval_testkit import make_row

from eval.data import Sample
from eval.metrics import evaluate, make_outcome
from eval.parse import extract_json_object, parse_extraction
from tromox_lead import AI_EXTRACTION_FIELDS, B2BType, EscalationReason, Segment

FULL = {
    "language": "en", "segment": "B2B", "b2b_type": "dealer", "b2c_intent": None, "country_stated": "GB",
    "city_region": "Leeds", "contact_name": "A. Smith", "company": "Smith {Motors} Ltd", "role": "owner",
    "product_interest": ["MC10", "Ukko S+"], "volume": "20 units / year", "existing_dealer_relationship": None,
    "ai_summary": "英国利兹经销商，想代理。", "ai_confidence": 0.93, "escalation_flag": True,
    "escalation_reason": "b2b_qualified",
}


def test_fixture_matches_schema():
    assert tuple(FULL) == AI_EXTRACTION_FIELDS


def test_plain_json():
    result = parse_extraction(json.dumps(FULL, ensure_ascii=False))
    assert result.ok and result.missing_keys == () and result.extra_keys == ()
    e = result.extraction
    assert e.segment is Segment.B2B and e.b2b_type is B2BType.DEALER
    assert e.product_interest == ["MC10", "UKKO"] and e.escalation_reason is EscalationReason.B2B_QUALIFIED


@pytest.mark.parametrize("wrapper", [
    "```json\n{body}\n```",
    "```\n{body}\n```",
    "Sure! Here is the JSON:\n{body}\nLet me know if you need anything else.",
    "Thinking about it {{not json}} ... final answer:\n{body}",
])
def test_fences_and_surrounding_text(wrapper):
    text = wrapper.replace("{body}", json.dumps(FULL, ensure_ascii=False, indent=2)).replace("{{", "{").replace("}}", "}")
    result = parse_extraction(text)
    assert result.ok and result.extraction.company == "Smith {Motors} Ltd"


def test_braces_inside_strings_do_not_confuse_the_scanner():
    assert extract_json_object('noise {"a": "x } y { z", "b": {"c": 1}} tail') == {"a": "x } y { z", "b": {"c": 1}}


def test_nullish_strings_and_loose_types_are_cleaned():
    loose = dict(FULL, b2c_intent="null", company="N/A", country_stated="gb", ai_confidence="0.7",
                 escalation_flag="false", escalation_reason="b2b_qualified", product_interest="mc-10; vespa")
    e = parse_extraction(json.dumps(loose)).extraction
    assert e.b2c_intent is None and e.company is None and e.country_stated == "GB"
    assert e.ai_confidence == 0.7 and e.escalation_flag is False and e.escalation_reason is None
    assert e.product_interest == ["MC10"]


def test_missing_and_extra_keys_are_recorded_but_usable():
    partial = {"segment": "B2C", "b2c_intent": "buy", "ai_confidence": 0.8, "mood": "happy"}
    result = parse_extraction(json.dumps(partial))
    assert result.ok and "language" in result.missing_keys and result.extra_keys == ("mood",)


@pytest.mark.parametrize("text, fragment", [
    ("", "no valid JSON"),
    ("I cannot help with that.", "no valid JSON"),
    ('{"segment": "B2B", "b2b_type": "dealer"', "no valid JSON"),          # truncated
    ('{"hello": "world"}', "none of the expected keys"),
    ('{"segment": "B2B", "b2b_type": "retailer"}', "schema validation failed at b2b_type"),
    ('{"segment": "B2C", "escalation_flag": true, "escalation_reason": "angry"}', "schema validation failed"),
    ("[1, 2, 3]", "no valid JSON"),
])
def test_unusable_outputs_are_parse_failures(text, fragment):
    result = parse_extraction(text)
    assert not result.ok and fragment in result.error


def test_out_of_enum_segment_is_unknown_counts_as_parsed_and_still_misses_b2b():
    """Production behaviour, measured as such: the shared model maps a segment other than B2B / B2C to unknown."""
    result = parse_extraction(json.dumps(dict(FULL, segment="business"), ensure_ascii=False))
    assert result.ok and result.error is None and result.extraction.segment is Segment.UNKNOWN
    r = evaluate([make_outcome(Sample.model_validate(make_row()), None, result)])   # gold: B2B dealer
    assert r.parse_ok == 1 and r.parse_success == 1.0
    assert (r.b2b_tp, r.b2b_fn) == (0, 1)
