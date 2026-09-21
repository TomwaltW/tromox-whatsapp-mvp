"""Routing rules applied on top of the raw AI extraction (01-design/routing-rules.md).

The same function runs in the offline eval and in the webhook service, so that the
measured behaviour is the production behaviour.
"""
from __future__ import annotations

from .enums import LOW_CONFIDENCE_THRESHOLD, EscalationReason, Segment
from .schema import AIExtraction


def is_b2b_qualified(extraction: AIExtraction, country_by_phone: str | None = None) -> bool:
    """B2B field collection complete: type + who (company or contact) + market."""
    if extraction.segment is not Segment.B2B or extraction.b2b_type is None:
        return False
    has_who = bool(extraction.company or extraction.contact_name)
    has_market = bool(extraction.country_stated or country_by_phone)
    return has_who and has_market


def apply_routing_rules(extraction: AIExtraction, country_by_phone: str | None = None) -> AIExtraction:
    """Return a copy with rule-based escalations enforced.

    Priority: an explicit reason from the model wins; otherwise low confidence, then
    B2B-qualified. Rules only ever *add* an escalation, never remove one.
    """
    result = extraction.model_copy(deep=True)
    if result.escalation_flag and result.escalation_reason is not None:
        return result
    if result.ai_confidence < LOW_CONFIDENCE_THRESHOLD:
        result.escalation_flag = True
        result.escalation_reason = EscalationReason.LOW_CONFIDENCE
    elif is_b2b_qualified(result, country_by_phone):
        result.escalation_flag = True
        result.escalation_reason = EscalationReason.B2B_QUALIFIED
    elif result.escalation_flag and result.escalation_reason is None:
        result.escalation_reason = EscalationReason.LOW_CONFIDENCE
    return result
