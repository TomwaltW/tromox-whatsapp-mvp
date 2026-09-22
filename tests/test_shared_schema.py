"""Root tests for the shared package: schema consistency and routing rules."""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import tromox_lead as t

ROOT = Path(__file__).resolve().parents[1]


def test_lead_fields_match_pydantic_model():
    assert tuple(t.Lead.model_fields) == t.LEAD_FIELDS
    assert len(t.LEAD_FIELDS) == 30
    assert "profile_name" in t.LEAD_FIELDS and "profile_name" not in t.AI_EXTRACTION_FIELDS


def test_ai_extraction_is_ordered_subset_of_lead():
    assert tuple(t.AIExtraction.model_fields) == t.AI_EXTRACTION_FIELDS
    assert set(t.AI_EXTRACTION_FIELDS) <= set(t.LEAD_FIELDS)
    flagged = tuple(f.name for f in t.FIELD_SPECS if f.ai_extracted)
    assert set(flagged) == set(t.AI_EXTRACTION_FIELDS)


def test_label_columns_are_schema_fields_or_declared_label_only():
    for column in t.LABEL_COLUMNS:
        assert column in t.LEAD_FIELDS or column in t.LABEL_ONLY_COLUMNS, column
    flagged = {f.name for f in t.FIELD_SPECS if f.label_column}
    assert flagged == set(t.LABEL_COLUMNS) - set(t.LABEL_ONLY_COLUMNS)


def test_botmaker_variables_are_schema_fields():
    assert set(t.BOTMAKER_VARIABLES) <= set(t.LEAD_FIELDS)


def test_generated_artifacts_are_fresh():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "gen_schema_artifacts.py"), "--check"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_labeling_template_header_matches():
    with (ROOT / "04-eval" / "labeling-template.csv").open(encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert tuple(header) == t.LABEL_COLUMNS


@pytest.mark.parametrize("rel", ["04-eval/prompts/classify-v1.md", "02-botmaker/ai-agent-system-prompt.md"])
def test_prompt_json_block_keys_equal_extraction_fields(rel):
    text = (ROOT / rel).read_text(encoding="utf-8")
    match = re.search(r"<!-- BEGIN GENERATED: extraction-json -->\s*```json\n(.*?)\n```", text, re.DOTALL)
    assert match, f"no generated JSON block in {rel}"
    assert tuple(json.loads(match.group(1))) == t.AI_EXTRACTION_FIELDS


def test_json_schema_properties_equal_lead_fields():
    schema = json.loads((ROOT / "01-design" / "lead.schema.json").read_text(encoding="utf-8"))
    assert tuple(schema["properties"]) == t.LEAD_FIELDS


def test_country_from_phone_and_e164():
    assert t.normalize_e164("551150392540") == "+551150392540"
    assert t.country_from_phone("+4917604069012") == "DE"
    assert t.country_from_phone("+12025550143") == "US"
    assert t.country_from_phone(None) is None
    assert t.normalize_e164("not a number") is None
    assert t.is_ambiguous_calling_code("+12025550143") is True
    assert t.is_ambiguous_calling_code("+4917604069012") is False
    assert t.effective_country("AT", "DE") == "AT"
    assert t.effective_country(None, "DE") == "DE"


def test_source_code_parsing():
    assert t.parse_source_code("Hi Tromox! [IG-2609]") == ("IG-2609", t.SourceChannel.INSTAGRAM)
    assert t.parse_source_code("hola tt-2610b info") == ("TT-2610B", t.SourceChannel.TIKTOK)
    assert t.parse_source_code("BIG-2609 deal") == (None, t.SourceChannel.UNKNOWN)
    assert t.parse_source_code(None) == (None, t.SourceChannel.UNKNOWN)
    assert t.strip_source_code("Hi Tromox! [IG-2609]") == "Hi Tromox!"
    assert t.build_prefill("ig-2609") == "Hi Tromox! [IG-2609]"


def test_language_fallback_is_deterministic():
    samples = {
        "Hallo, ich möchte Händler werden": "de",
        "Hola, quiero ser distribuidor en México": "es",
        "Bonjour, quel est le prix du MC10 ?": "fr",
        "Olá, vocês têm revendedor em Lisboa?": "pt",
        "Ciao, vorrei un test ride": "it",
        "Hi, I want to become a dealer": "en",
        "ok": "und",
    }
    for text, expected in samples.items():
        assert t.detect_language(text) == expected
        assert t.detect_language(text) == t.detect_language(text)


def test_extraction_cleaning_and_consistency():
    e = t.AIExtraction.model_validate({
        "language": "DE", "segment": "b2b", "b2b_type": "Dealer", "b2c_intent": "buy",
        "country_stated": "de", "product_interest": "Ukko S+; mc-10; Vespa",
        "ai_confidence": "0.95", "escalation_flag": "false", "escalation_reason": "human_requested",
        "company": "null", "unexpected": 1,
    })
    assert e.language == "de" and e.segment is t.Segment.B2B and e.b2b_type is t.B2BType.DEALER
    assert e.b2c_intent is None  # B2C-only field cleared for a B2B lead
    assert e.country_stated == "DE" and e.product_interest == ["MC10", "UKKO"]
    assert e.company is None and e.escalation_reason is None


def test_routing_rules():
    base = dict(segment="B2B", b2b_type="dealer", company="Moto Nord", ai_confidence=0.9)
    qualified = t.apply_routing_rules(t.AIExtraction.model_validate(base), country_by_phone="DE")
    assert qualified.escalation_flag and qualified.escalation_reason is t.EscalationReason.B2B_QUALIFIED
    not_yet = t.apply_routing_rules(t.AIExtraction.model_validate({**base, "company": None}), "DE")
    assert not not_yet.escalation_flag
    # an AI-extracted contact name without a company still counts as "who" (only the WhatsApp
    # profile name is excluded, and it never reaches AIExtraction)
    contact_only = t.apply_routing_rules(
        t.AIExtraction.model_validate({**base, "company": None, "contact_name": "Lucía Martínez"}), "DE")
    assert contact_only.escalation_flag and contact_only.escalation_reason is t.EscalationReason.B2B_QUALIFIED
    low = t.apply_routing_rules(t.AIExtraction.model_validate({"segment": "B2C", "ai_confidence": 0.4}))
    assert low.escalation_reason is t.EscalationReason.LOW_CONFIDENCE
    explicit = t.apply_routing_rules(t.AIExtraction.model_validate(
        {"segment": "B2C", "ai_confidence": 0.3, "escalation_flag": True, "escalation_reason": "human_requested"}))
    assert explicit.escalation_reason is t.EscalationReason.HUMAN_REQUESTED


def test_tags_full_and_lite():
    lead = t.Lead(lead_id=t.lead_id_for_phone("+4917604069012"), phone="+4917604069012",
                  country_by_phone="DE", segment="B2B", b2b_type="distributor",
                  product_interest=["MC10"], language="de", source_channel="instagram")
    full = t.build_tags(lead)
    assert {"country_de", "seg_b2b", "b2b_distributor", "prod_mc10", "src_instagram", "lang_de", "prio_high", "stage_new"} <= set(full)
    assert t.build_tags(lead, t.TIER_LITE_DIMENSIONS) == ["country_de", "seg_b2b"]
    assert t.lead_id_for_phone("+4917604069012") == lead.lead_id


def test_apply_extraction_partial_update_keeps_known_values():
    lead = t.Lead(lead_id="L-x", phone="+4917604069012", segment="B2B", b2b_type="dealer",
                  company="Moto Nord", ai_confidence=0.9, escalation_flag=True,
                  escalation_reason="b2b_qualified")
    lead.apply_extraction(t.AIExtraction.model_validate({"volume": "20 units"}))
    assert lead.volume == "20 units"
    assert lead.company == "Moto Nord" and lead.b2b_type is t.B2BType.DEALER
    assert lead.ai_confidence == 0.9 and lead.escalation_flag is True
    assert lead.escalation_reason is t.EscalationReason.B2B_QUALIFIED


def test_apply_extraction_clears_stale_cross_segment_fields():
    lead = t.Lead(lead_id="L-x", phone="+4917604069012", segment="B2C", b2c_intent="buy")
    lead.apply_extraction(t.AIExtraction.model_validate({"segment": "B2B", "b2b_type": "fleet"}))
    assert lead.segment is t.Segment.B2B and lead.b2b_type is t.B2BType.FLEET and lead.b2c_intent is None
    lead.apply_extraction(t.AIExtraction.model_validate({"segment": "unknown"}))
    assert lead.segment is t.Segment.B2B  # never downgraded
    lead.escalation_flag, lead.escalation_reason = True, t.EscalationReason.HUMAN_REQUESTED
    lead.apply_extraction(t.AIExtraction.model_validate({"escalation_flag": False}))
    assert lead.escalation_flag is False and lead.escalation_reason is None


def test_lead_without_phone_is_keyed_by_platform_customer_id():
    assert t.contact_key("+4917604069012", "C1") == "+4917604069012"
    key = t.contact_key(None, "PRQICKLCR18TSUEXWVQ7")
    assert key == "bm:PRQICKLCR18TSUEXWVQ7" and t.contact_key(None, " ") is None
    lead = t.Lead(lead_id=t.lead_id_for_contact(key), segment="B2B", b2b_type="dealer", country_stated="DE")
    assert lead.phone is None and lead.lead_id == t.lead_id_for_contact(key)
    assert "country_de" in t.build_tags(lead)
    assert t.lead_id_for_phone("+4917604069012") == t.lead_id_for_contact("+4917604069012")
