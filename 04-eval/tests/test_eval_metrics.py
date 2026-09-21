"""Metrics on a six-sample fixture whose expected numbers are computed by hand (see comments)."""
from __future__ import annotations

import pytest
from eval_testkit import make_row

from eval.clients.base import Completion, Usage
from eval.data import Sample
from eval.metrics import (
    check_thresholds,
    cost_per_100,
    evaluate,
    fallback_prediction,
    load_thresholds,
    make_outcome,
)
from eval.parse import ParseResult, parse_extraction
from tromox_lead import AIExtraction, EscalationReason, Segment


def _sample(**overrides: str) -> Sample:
    return Sample.model_validate(make_row(**overrides))


def _outcome(sample: Sample, prediction: dict | None, usage: Usage):
    completion = Completion(text="x", usage=usage, model="test", stop_reason="end_turn", latency_s=0.5)
    parse = ParseResult(AIExtraction.model_validate(prediction)) if prediction else ParseResult(None, error="bad json")
    return make_outcome(sample, completion, parse)


@pytest.fixture()
def outcomes():
    base = Usage(input_tokens=1000, output_tokens=100)
    return [
        # S1 B2B dealer; model forgets to escalate, routing adds b2b_qualified (type + company + phone market)
        _outcome(_sample(sample_id="S1", product_interest="MC10;UKKO", escalation_flag="true", escalation_reason="b2b_qualified"),
                 {"language": "de", "segment": "B2B", "b2b_type": "dealer", "company": "X GmbH",
                  "product_interest": ["MC10", "UKKO"], "ai_confidence": 0.9}, base),
        # S2 B2B distributor stating AT from a DE phone; predicted B2C and no stated country -> miss + country error
        _outcome(_sample(sample_id="S2", b2b_type="distributor", country_gold="AT"),
                 {"language": "de", "segment": "B2C", "b2c_intent": "buy", "ai_confidence": 0.9}, base),
        # S3 B2C buyer predicted as B2B (false positive), product missed
        _outcome(_sample(sample_id="S3", phone="+12025550143", language="en", segment="B2C", b2b_type="", b2c_intent="buy",
                         country_gold="US", product_interest="MINO", is_valid_lead="no"),
                 {"language": "en", "segment": "B2B", "b2b_type": "other", "ai_confidence": 0.9}, base),
        # S4 complaint: escalated by both, but with a different reason
        _outcome(_sample(sample_id="S4", phone="+447700900123", language="en", segment="B2C", b2b_type="", b2c_intent="warranty",
                         country_gold="GB", escalation_flag="true", escalation_reason="complaint_warranty_legal_safety",
                         is_valid_lead="no"),
                 {"language": "en", "segment": "B2C", "b2c_intent": "warranty", "ai_confidence": 0.9,
                  "escalation_flag": True, "escalation_reason": "human_requested"},
                 Usage(input_tokens=1000, output_tokens=100, cache_write_tokens=1000)),
        # S5 unknown, no phone; unusable output -> production fallback (unknown + hand over)
        _outcome(_sample(sample_id="S5", phone="", language="en", segment="unknown", b2b_type="", country_gold="",
                         is_valid_lead="no"), None, Usage(input_tokens=1000, output_tokens=100, cache_read_tokens=1000)),
        # S6 B2C support answered correctly but with low confidence -> routing escalates
        _outcome(_sample(sample_id="S6", phone="+33639981234", language="fr", segment="B2C", b2b_type="", b2c_intent="support",
                         country_gold="FR", product_interest="M05", is_valid_lead="no"),
                 {"language": "fr", "segment": "B2C", "b2c_intent": "support", "product_interest": ["M05"],
                  "ai_confidence": 0.5}, base),
    ]


def test_hand_computed_metrics(outcomes):
    r = evaluate(outcomes)
    assert (r.n_total, r.n_real, r.n_real_b2b, r.n_gold_b2b) == (6, 6, 2, 2)
    assert r.parse_ok == 5 and r.parse_success == pytest.approx(5 / 6)
    assert [o.sample.sample_id for o in r.parse_failures] == ["S5"]

    assert r.confusion[("B2B", "B2B")] == 1 and r.confusion[("B2B", "B2C")] == 1
    assert r.confusion[("B2C", "B2B")] == 1 and r.confusion[("B2C", "B2C")] == 2
    assert r.confusion[("unknown", "unknown")] == 1 and sum(r.confusion.values()) == 6
    assert (r.b2b_tp, r.b2b_fn, r.b2b_fp) == (1, 1, 1)
    assert r.b2b_recall == r.b2b_precision == r.b2b_f1 == pytest.approx(0.5)
    assert [o.sample.sample_id for o in r.b2b_misses] == ["S2"]
    assert [o.sample.sample_id for o in r.b2b_false_positives] == ["S3"]

    assert (r.country_correct, r.country_eligible) == (4, 5)          # S5 has no phone; S2 is wrong
    assert [o.sample.sample_id for o in r.country_errors] == ["S2"]
    assert (r.product_exact, r.product_eligible) == (2, 3)            # S1 ok, S3 missed, S6 ok
    assert (r.product_tp, r.product_fp, r.product_fn) == (3, 0, 1)

    assert r.escalation_pred == 4 and r.escalation_rate == pytest.approx(4 / 6)   # S1, S4, S5, S6
    assert (r.escalation_gold, r.escalation_tp, r.escalation_reason_match) == (2, 2, 1)
    assert r.escalation_recall == 1.0 and r.escalation_precision == 0.5
    assert r.escalation_by_reason == {"b2b_qualified": 1, "human_requested": 1, "low_confidence": 2}

    assert (r.b2b_type_correct, r.b2b_type_eligible) == (1, 1)
    assert (r.b2c_intent_correct, r.b2c_intent_eligible) == (2, 2)
    assert r.language_correct == 5                                    # S5 falls back to "und"
    german = next(row for row in r.per_language if row.language == "de")
    assert (german.n, german.n_b2b, german.b2b_recall) == (2, 2, 0.5)
    assert r.usage == Usage(6000, 600, 1000, 1000)
    assert r.latency_p50 == 0.5 and r.latency_p95 == 0.5


def test_routing_rules_are_applied_like_production(outcomes):
    s1, _, _, _, s5, s6 = outcomes
    assert s1.prediction.escalation_reason is EscalationReason.B2B_QUALIFIED
    assert s6.prediction.escalation_reason is EscalationReason.LOW_CONFIDENCE
    assert s5.prediction.segment is Segment.UNKNOWN and s5.prediction.escalation_flag
    assert fallback_prediction().escalation_reason is EscalationReason.LOW_CONFIDENCE


def test_cost_per_100(outcomes):
    r = evaluate(outcomes)
    # input 6000 + cache write 1000 x 1.25 + cache read 1000 x 0.10 = 7350 tokens at 1 USD/M = 0.00735
    # output 600 tokens at 5 USD/M = 0.003 ; total 0.01035 for 6 samples -> 0.1725 per 100
    assert cost_per_100(r, (1.0, 5.0)) == pytest.approx(0.1725)
    assert cost_per_100(r, None) is None


def test_threshold_checks(outcomes):
    r = evaluate(outcomes)
    checks = {c.key: c for c in check_thresholds(r, {
        "offline_min_samples": 5, "offline_min_b2b_samples": 3, "b2b_recall_min": 0.9,
        "escalation_rate_max": 0.3, "json_parse_success_min": 0.8, "notify_latency_max_seconds": 60,
    })}
    assert set(checks) == {"offline_min_samples", "offline_min_b2b_samples", "b2b_recall_min",
                           "escalation_rate_max", "json_parse_success_min"}       # unrelated keys are ignored
    assert checks["offline_min_samples"].passed and not checks["offline_min_b2b_samples"].passed
    assert not checks["b2b_recall_min"].passed and not checks["escalation_rate_max"].passed
    assert checks["json_parse_success_min"].passed


def test_undefined_metric_fails_its_threshold():
    sample = _sample(segment="B2C", b2b_type="", b2c_intent="buy")
    r = evaluate([make_outcome(sample, None, parse_extraction('{"segment": "B2C", "b2c_intent": "buy", "ai_confidence": 0.9}'))])
    check = check_thresholds(r, {"b2b_recall_min": 0.9})[0]
    assert r.b2b_recall is None and not check.passed and "无可统计样本" in check.note


def test_repo_thresholds_file_is_readable():
    thresholds = load_thresholds()
    assert thresholds["b2b_recall_min"] == 0.90 and thresholds["offline_min_samples"] == 150
    assert "_comment" not in thresholds
