"""Deterministic mock model: perturbs the gold labels so the pipeline can run offline.

The mock proves that the tool works end to end; its numbers say nothing about a real model.
Every random draw is seeded by (seed, sample_id), so two runs give byte-identical reports.
"""
from __future__ import annotations

import json
import random

from tromox_lead import AI_EXTRACTION_FIELDS, B2BType, B2CIntent, EscalationReason, Segment

from ..data import Sample
from .base import Completion, Usage

# Picked so the demo report on the synthetic set exercises every section (B2B misses, false
# positives, a country error, one JSON parse failure) while staying above the thresholds.
DEFAULT_SEED = 45
DEFAULT_ERROR_RATE = 0.06
_WRONG_COUNTRIES = ("FR", "NL", "BR", "PL", "SE")


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class MockClient:
    """`error_rate` scales every perturbation; 0.0 reproduces the gold labels exactly."""

    def __init__(self, seed: int = DEFAULT_SEED, error_rate: float = DEFAULT_ERROR_RATE) -> None:
        if not 0.0 <= error_rate <= 1.0:
            raise ValueError("error_rate must be between 0 and 1")
        self.seed = seed
        self.error_rate = error_rate
        self.name = "mock"

    def _extraction(self, sample: Sample, rng: random.Random) -> dict[str, object]:
        rate = self.error_rate
        segment = sample.segment
        b2b_type, b2c_intent = sample.b2b_type, sample.b2c_intent
        # Segment errors are asymmetric on purpose: the prompt prefers B2B when unsure, so
        # false B2B positives are more frequent than missed dealers.
        if segment is Segment.B2B and rng.random() < rate * 0.75:
            segment, b2b_type, b2c_intent = Segment.B2C, None, B2CIntent.BUY
        elif segment is Segment.B2C and rng.random() < rate:
            segment, b2b_type, b2c_intent = Segment.B2B, B2BType.OTHER, None
        elif segment is Segment.UNKNOWN and rng.random() < rate:
            segment, b2c_intent = Segment.B2C, B2CIntent.OTHER

        products = list(sample.product_interest)
        if products and rng.random() < rate * 1.5:
            products.pop(rng.randrange(len(products)))

        phone_country = sample.country_by_phone
        country_stated = sample.country_gold if sample.country_gold != phone_country else None
        if rng.random() < rate * 0.25:
            country_stated = rng.choice([c for c in _WRONG_COUNTRIES if c != sample.country_gold])

        flag, reason = sample.escalation_flag, sample.escalation_reason
        if rng.random() < rate * 0.5:
            flag = not flag
            reason = EscalationReason.HUMAN_REQUESTED if flag else None
        # The routing rules add b2b_qualified when type + who + market are known, so the mock
        # only reports a company when the gold label says the lead is qualified.
        qualified = flag and reason is EscalationReason.B2B_QUALIFIED and segment is Segment.B2B
        confidence = 0.5 if (flag and reason is EscalationReason.LOW_CONFIDENCE) else 0.9

        values: dict[str, object] = {
            "language": sample.language,
            "segment": segment.value,
            "b2b_type": b2b_type.value if b2b_type else None,
            "b2c_intent": b2c_intent.value if b2c_intent else None,
            "country_stated": country_stated,
            "city_region": None,
            "contact_name": None,
            "company": "Mock Company" if qualified else None,
            "role": None,
            "product_interest": products,
            "volume": None,
            "existing_dealer_relationship": None,
            "ai_summary": f"（mock）{segment.value} 咨询，样本 {sample.sample_id}。",
            "ai_confidence": confidence,
            "escalation_flag": flag,
            "escalation_reason": reason.value if reason else None,
        }
        assert tuple(values) == AI_EXTRACTION_FIELDS
        return values

    def complete(self, system_prompt: str, user_message: str, *, sample: Sample | None = None) -> Completion:
        if sample is None:
            raise ValueError("the mock client needs the labelled sample")
        rng = random.Random(f"{self.seed}:{sample.sample_id}")
        text = json.dumps(self._extraction(sample, rng), ensure_ascii=False, indent=2)
        # Formatting noise a real model produces; the parser must cope with the first two.
        draw = rng.random()
        if draw < self.error_rate * 0.25:
            text = text[: len(text) // 2]                       # truncated -> parse failure
        elif draw < self.error_rate * 0.25 + 0.05 and self.error_rate > 0:
            text = f"```json\n{text}\n```"
        elif draw < self.error_rate * 0.25 + 0.08 and self.error_rate > 0:
            text = f"Here is the JSON:\n{text}\nLet me know if you need anything else."
        usage = Usage(input_tokens=_approx_tokens(system_prompt) + _approx_tokens(user_message),
                      output_tokens=_approx_tokens(text))
        return Completion(text=text, usage=usage, model="mock", stop_reason="end_turn")
