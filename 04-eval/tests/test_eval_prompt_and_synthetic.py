from __future__ import annotations

import collections
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from eval.data import load_dataset
from eval.prompt import build_user_message, load_prompt, strip_html_comments
from tromox_lead import (
    AI_EXTRACTION_FIELDS,
    AIExtraction,
    B2BType,
    B2CIntent,
    EscalationReason,
    Segment,
    apply_routing_rules,
    parse_source_code,
)

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "prompts" / "classify-v1.md"
JSON_BLOCK_RE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


# ----------------------------------------------------------------------------- prompt
def test_prompt_is_sent_without_comments_or_markers():
    spec = load_prompt(PROMPT)
    assert spec.version == "classify-v1" and len(spec.sha256) == 64
    assert "<!--" not in spec.text and "GENERATED" not in spec.text and "维护规则" not in spec.text
    assert "### Extraction rules (shared block)" in spec.text and "Asymmetric cost" in spec.text
    assert strip_html_comments("a\n<!-- x\ny -->\n\n\n\nb") == "a\n\nb\n"


def test_prompt_blocks_match_the_shared_source():
    raw = PROMPT.read_text(encoding="utf-8")
    shared = (ROOT.parent / "shared" / "prompt_blocks" / "extraction-rules.md").read_text(encoding="utf-8").strip()
    assert shared in raw
    schema_block = json.loads(JSON_BLOCK_RE.findall(raw)[0])
    assert tuple(schema_block) == AI_EXTRACTION_FIELDS


def test_few_shot_examples_are_valid_and_stable_under_routing():
    blocks = [json.loads(b) for b in JSON_BLOCK_RE.findall(load_prompt(PROMPT).text)][1:]
    assert len(blocks) == 3
    for block in blocks:
        assert tuple(block) == AI_EXTRACTION_FIELDS                   # exactly the keys, in order
        extraction = AIExtraction.model_validate(block)
        routed = apply_routing_rules(extraction, country_by_phone=None)
        assert (routed.escalation_flag, routed.escalation_reason) == (extraction.escalation_flag, extraction.escalation_reason)
        assert re.search(r"[一-鿿]", extraction.ai_summary)     # summary for sales is in Chinese
    assert [b["segment"] for b in blocks] == ["B2B", "B2C", "B2B"]
    assert blocks[1]["country_stated"] is None and blocks[1]["city_region"] == "Torino"   # a city is not a country
    assert blocks[2]["ai_confidence"] < 0.6 and blocks[2]["escalation_reason"] == "low_confidence"


def test_user_message_strips_short_code_and_validates_button():
    message = build_user_message("Hi Tromox! [IG-2609] We sell scooters")
    assert "IG-2609" not in message and "<button_choice>none</button_choice>" in message
    assert "We sell scooters" in message
    assert "<button_choice>Dealer/Distributor</button_choice>" in build_user_message("x", "Dealer/Distributor")
    assert "<button_choice>none</button_choice>" in build_user_message("x", "Free pizza")
    code_only = build_user_message("[IG-2609]")                          # never send an empty conversation
    assert "<conversation>\n[IG-2609]\n</conversation>" in code_only


# ----------------------------------------------------------------------------- synthetic set
@pytest.fixture(scope="module")
def synthetic():
    return load_dataset(ROOT / "synthetic-samples.csv").samples


def test_every_synthetic_row_validates_and_is_marked_synthetic(synthetic):
    assert len(synthetic) == 80
    assert [s.sample_id for s in synthetic] == [f"SYN-{i:03d}" for i in range(1, 81)]
    assert {s.data_origin for s in synthetic} == {"synthetic"}
    assert all(s.phone and s.country_by_phone and s.country_gold for s in synthetic)


def test_synthetic_mix(synthetic):
    languages = collections.Counter(s.language for s in synthetic)
    assert languages == {"en": 28, "de": 12, "es": 12, "fr": 10, "pt": 9, "it": 9}
    segments = collections.Counter(s.segment for s in synthetic)
    assert segments == {Segment.B2B: 24, Segment.B2C: 44, Segment.UNKNOWN: 12}
    assert {s.b2b_type for s in synthetic if s.b2b_type} == set(B2BType)
    assert {s.b2c_intent for s in synthetic if s.b2c_intent} == set(B2CIntent)
    reasons = {s.escalation_reason for s in synthetic if s.escalation_reason}
    assert reasons == set(EscalationReason) - {EscalationReason.NOT_UNDERSTOOD_TWICE}   # conversation-mode only
    assert sum(s.escalation_flag for s in synthetic) / len(synthetic) <= 0.30
    assert sum(parse_source_code(s.conversation_text)[0] is not None for s in synthetic) >= 10
    assert sum(s.country_gold != s.country_by_phone for s in synthetic) >= 5           # stated country wins
    assert sum("歧义" in (s.label_notes or "") for s in synthetic) >= 2


def test_synthetic_texts_contain_no_prices_or_spec_numbers(synthetic):
    for s in synthetic:
        assert not re.search(r"[€$£]|\b(?:USD|EUR|GBP)\b|\bkm/h\b|\bkWh?\b|\bmph\b", s.conversation_text), s.sample_id


def test_synthetic_csv_is_in_sync_with_its_generator():
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "make_synthetic.py"), "--check"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
