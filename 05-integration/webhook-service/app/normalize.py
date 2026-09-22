"""Payload -> lead normalisation. Pure functions, no I/O.

Every rule that touches lead semantics comes from the shared `tromox_lead` package, so the
webhook service behaves exactly like the offline eval: E.164 + country by phone prefix,
short-code parsing, language fallback, routing rules, tag generation.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from tromox_lead import (
    AI_EXTRACTION_FIELDS,
    TIER_FULL_DIMENSIONS,
    TIER_LITE_DIMENSIONS,
    AIExtraction,
    EscalationReason,
    Lead,
    LeadStatus,
    Referral,
    Segment,
    SourceChannel,
    apply_routing_rules,
    build_tags,
    contact_key,
    country_from_phone,
    detect_language,
    lead_id_for_contact,
    normalize_e164,
    parse_source_code,
    strip_source_code,
)

from .models import BotmakerEvent, BotmakerWebhook

log = logging.getLogger(__name__)

_NULLISH = {"", "null", "none", "undefined", "n/a", "na", "-"}
_TRUE = {"true", "1", "yes", "y", "si", "sí"}
_FALSE = {"false", "0", "no", "n"}
_KNOWN_VARIABLES = (*AI_EXTRACTION_FIELDS, "consent_marketing", "source_code", "lead_json")
_SQUASHED_TO_FIELD = {name.replace("_", ""): name for name in _KNOWN_VARIABLES}
_SQUASH_RE = re.compile(r"[^a-z0-9]")
_PHONE_LIKE_RE = re.compile(r"\+?[\d\s\-()]{7,24}")

# Conversation-close typification -> lead status. Names are placeholders until the client
# defines the close categories in Botmaker 【待核实】【待客户确认】 (see botmaker-api-notes.md).
TYPIFICATION_TO_STATUS: dict[str, LeadStatus] = {
    "qualified_followup": LeadStatus.CONTACTED,
    "won": LeadStatus.CLOSED_WON,
    "lost": LeadStatus.CLOSED_LOST,
    "nurture": LeadStatus.NURTURE,
    "not_a_lead": LeadStatus.INVALID,
}
CLOSE_EVENTS = {"conversation-close"}
ASSIGNMENT_EVENTS = {"assigned-to-agent", "queue-set"}  # 【待核实】 whether webhooks emit these
_SYSTEM_FORWARD = (LeadStatus.NEW, LeadStatus.QUALIFIED, LeadStatus.HANDED_OFF)


def squash(key: str) -> str:
    """'b2bType', 'b2b_type', 'B2B-Type' -> 'b2btype' (tolerant variable-name matching)."""
    return _SQUASH_RE.sub("", key.strip().lower())


def is_nullish(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip().lower() in _NULLISH)


def parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
    return None


def parse_ts(value: Any) -> datetime | None:
    """ISO 8601 (with 'Z') or epoch seconds / milliseconds -> aware UTC datetime."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
        number = float(value)
        if number > 1e11:  # milliseconds
            number /= 1000.0
        try:
            return datetime.fromtimestamp(number, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def map_variables(variables: dict[str, Any]) -> dict[str, Any]:
    """Botmaker chat variables -> schema field names (snake_case or camelCase accepted).

    Also accepts one optional `lead_json` variable holding the whole extraction block
    【待核实】; individual variables win over it. Nullish values are dropped so they can
    never overwrite something already known.
    """
    mapped: dict[str, Any] = {}
    direct: dict[str, Any] = {}
    for key, value in (variables or {}).items():
        name = _SQUASHED_TO_FIELD.get(squash(str(key)))
        if name is None or is_nullish(value):
            continue
        direct[name] = value
    blob = direct.pop("lead_json", None)
    if blob is not None:
        try:
            parsed = json.loads(blob) if isinstance(blob, str) else blob
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            for key, value in parsed.items():
                name = _SQUASHED_TO_FIELD.get(squash(str(key)))
                if name and name != "lead_json" and not is_nullish(value):
                    mapped[name] = value
    mapped.update(direct)
    products = mapped.get("product_interest")
    if isinstance(products, str) and products.strip().startswith("["):
        try:
            mapped["product_interest"] = json.loads(products)
        except ValueError:
            pass
    return mapped


def _phone_like(value: str | None) -> str | None:
    """Digits with optional +, spaces, dashes, brackets - and nothing else.

    Guards against ids that merely *contain* digits (e.g. a business-scoped user id, which
    Botmaker's API already models as BSUID 【待核实】) being mistaken for a phone number.
    """
    if not value:
        return None
    text = str(value).strip()
    return normalize_e164(text) if _PHONE_LIKE_RE.fullmatch(text) else None


def extract_phone(payload: BotmakerWebhook) -> str | None:
    """E.164 of the customer. Only WhatsApp contact ids are phone numbers."""
    platform = (payload.chat_platform or "whatsapp").lower()
    if platform != "whatsapp":
        return None
    phone = _phone_like(payload.contact_id)
    if phone:
        return phone
    fallback = _phone_like(payload.whatsapp_number)
    if fallback and payload.chat_channel_id and fallback.lstrip("+") in payload.chat_channel_id:
        return None  # that is the company's own line, never a customer
    return fallback


def profile_name(payload: BotmakerWebhook) -> str | None:
    name = " ".join(part.strip() for part in (payload.first_name, payload.last_name) if part and part.strip())
    return name or None


def find_referral(payload: BotmakerWebhook) -> Referral | None:
    """CTWA ad referral, if Botmaker passes it through 【待核实】 (top level or per message)."""
    candidates: list[dict[str, Any]] = []
    if payload.referral:
        candidates.append(payload.referral)
    candidates.extend(m.referral for m in payload.messages if m.referral)
    for raw in candidates:
        data = {squash(str(k)): v for k, v in raw.items() if not is_nullish(v)}
        referral = Referral(
            source_type=data.get("sourcetype"), source_id=data.get("sourceid"),
            source_url=data.get("sourceurl"), headline=data.get("headline"),
            body=data.get("body"), ctwa_clid=data.get("ctwaclid"),
        )
        if any(referral.model_dump().values()):
            return referral
    return None


@dataclass
class MessageFacts:
    """What one message callback tells us, before it is merged into the stored lead."""

    user_messages: list[tuple[datetime | None, str]] = field(default_factory=list)
    agent: str | None = None
    agent_message_count: int = 0  # `from: agent` messages, whether or not the operator is named
    variables: dict[str, Any] = field(default_factory=dict)
    referral: Referral | None = None
    profile_name: str | None = None

    @property
    def agent_initiated(self) -> bool:
        """Only the salesperson spoke (e.g. a template sent after the 24 h window closed)."""
        return self.agent_message_count > 0 and not self.user_messages

    @property
    def first_user_text(self) -> str | None:
        if not self.user_messages:
            return None
        dated = [item for item in self.user_messages if item[0] is not None]
        return (min(dated, key=lambda item: item[0]) if dated else self.user_messages[0])[1]

    @property
    def user_timestamps(self) -> list[datetime]:
        return [ts for ts, _ in self.user_messages if ts is not None]


def collect_message_facts(payload: BotmakerWebhook) -> MessageFacts:
    facts = MessageFacts(variables=map_variables(payload.variables), referral=find_referral(payload),
                         profile_name=profile_name(payload))
    for message in payload.messages:
        sender = (message.sender or "").lower()
        if sender == "user":
            facts.user_messages.append((parse_ts(message.date), message.message or ""))
        elif sender == "agent":
            facts.agent_message_count += 1
            facts.agent = message.operator_id or message.from_name or facts.agent
    return facts


def resolve_contact(payload: BotmakerWebhook) -> tuple[str | None, str | None]:
    """(phone, contact key) of a WhatsApp customer.

    The key is the E.164 phone. When Botmaker delivers no phone number - a customer who
    reaches the business through a WhatsApp username only exposes a business-scoped user id
    【待核实】 - the lead is still recorded, keyed by Botmaker's customer id, with `phone`
    left empty. A B2B lead must never be dropped just because its number is unknown.
    """
    if (payload.chat_platform or "whatsapp").lower() != "whatsapp":
        return None, None
    phone = extract_phone(payload)
    return phone, contact_key(phone, payload.customer_id)


def new_lead(phone: str | None, key: str | None = None) -> Lead:
    identity = key or phone
    if not identity:
        raise ValueError("a lead needs a phone number or a platform contact key")
    return Lead(lead_id=lead_id_for_contact(identity), phone=phone, country_by_phone=country_from_phone(phone))


def _validated_extraction(base: dict[str, Any], present: dict[str, Any]) -> AIExtraction:
    """Validate known values + new variables; one bad variable must not discard the others."""
    try:
        return AIExtraction.model_validate({**base, **present})
    except ValidationError as exc:
        bad = {str(err["loc"][0]) for err in exc.errors() if err.get("loc")}
        log.warning("dropping invalid extraction variables: %s", sorted(bad))
        kept = {k: v for k, v in present.items() if k not in bad}
        return AIExtraction.model_validate({**base, **kept})


def merge_message(existing: Lead | None, phone: str | None, facts: MessageFacts, tag_tier: str = "full",
                  key: str | None = None) -> Lead:
    """Merge one message callback into the lead (creating it on first contact)."""
    lead = existing.model_copy(deep=True) if existing is not None else new_lead(phone, key)
    if lead.phone is None and phone:  # the number became known later: keep the lead, add the number
        lead.phone, lead.country_by_phone = phone, country_from_phone(phone)
    present = {k: v for k, v in facts.variables.items() if k in AI_EXTRACTION_FIELDS}

    # --- source: first touch wins --------------------------------------------------------
    # The short code lives in the customer's FIRST message only (wa.me prefilled text). Later
    # messages are never scanned, so "my old AD-2023 scooter" cannot be mistaken for a source.
    first_text = facts.first_user_text
    if lead.source_code is None:
        code, channel = (None, SourceChannel.UNKNOWN)
        if lead.first_message_ts is None:
            code, channel = parse_source_code(first_text)
        if code is None and "source_code" in facts.variables:  # the flow may have captured it itself
            code, channel = parse_source_code(str(facts.variables["source_code"]))
        if code is not None:
            lead.source_code, lead.source_channel = code, channel
    if facts.referral is not None and lead.referral is None:
        lead.referral = facts.referral
        if lead.source_channel is SourceChannel.UNKNOWN:
            lead.source_channel = SourceChannel.CTWA_AD

    # --- language: AI variable first, deterministic detector as fallback ----------------
    if "language" not in present and lead.language == "und" and first_text:
        detected = detect_language(strip_source_code(first_text))
        if detected != "und":
            lead.language = detected

    # --- AI extraction: values already known are carried over, never blanked ------------
    base: dict[str, Any] = {name: getattr(lead, name) for name in AI_EXTRACTION_FIELDS}
    if lead.segment is not Segment.UNKNOWN and str(present.get("segment", "")).strip().upper() not in ("B2B", "B2C"):
        present.pop("segment", None)  # "unknown" never downgrades a known B2B / B2C
    extraction = _validated_extraction(base, present)

    confidence_known = "ai_confidence" in present or lead.ai_confidence > 0
    rules_input = extraction if confidence_known else extraction.model_copy(update={"ai_confidence": 1.0})
    routed = apply_routing_rules(rules_input, lead.country_by_phone)
    if not confidence_known:  # a button press alone must not look like a low-confidence case
        routed.ai_confidence = extraction.ai_confidence
    lead.apply_extraction(routed)
    lead.escalation_flag = routed.escalation_flag
    lead.escalation_reason = routed.escalation_reason if routed.escalation_flag else None
    if lead.segment is not Segment.B2B:
        lead.b2b_type = None
    if lead.segment is not Segment.B2C:
        lead.b2c_intent = None

    # --- consent, contact fallback, timestamps -------------------------------------------
    consent = parse_bool(facts.variables.get("consent_marketing"))
    if consent is not None:
        lead.consent_marketing = consent
    # The WhatsApp profile name is kept apart from `contact_name`: it is shown on the card when
    # the AI extracted no name, but it never makes a B2B lead look qualified (routing.py).
    if facts.profile_name:
        lead.profile_name = facts.profile_name
    stamps = facts.user_timestamps
    if stamps:
        lead.first_message_ts = min([*stamps, lead.first_message_ts] if lead.first_message_ts else stamps)
        lead.last_message_ts = max([*stamps, lead.last_message_ts] if lead.last_message_ts else stamps)

    # --- status: the system only moves forward --------------------------------------------
    if lead.status is LeadStatus.NEW and lead.escalation_reason is EscalationReason.B2B_QUALIFIED:
        lead.status = LeadStatus.QUALIFIED
    if facts.agent:
        lead.assigned_to = facts.agent
        if lead.status in _SYSTEM_FORWARD:
            lead.status = LeadStatus.CONTACTED

    lead.tags = build_tags(lead, tier_dimensions(tag_tier))
    return lead


_HANDED_OVER = (LeadStatus.HANDED_OFF, LeadStatus.CONTACTED)


def notification_suppressed(lead: Lead, facts: MessageFacts) -> str | None:
    """Why this message callback must NOT claim a card although `escalation_flag` is set.

    Evaluated on the merged lead (the stored flag / reason are written as the rules say; only
    the card is withheld). Returns None when the normal once-per-session claim applies.

    * `agent_initiated`: the callback carries agent messages and no customer message (the
      salesperson sent a template after the window closed). The stored flag is irrelevant.
      A bot-only callback, or one without messages, is NOT suppressed: whether the flow
      delivers its variables on a bot message is still open (README section 8, item 2).
    * `handed_over_b2b`: the lead is already with sales (`handed_off` / `contacted`) and the
      reason is `b2b_qualified` again (from the AI or re-derived by the rules). Any other
      reason still notifies: a customer asking for a person after hand-off gets a card.
      A lead whose conversation was already classified (closed_*, nurture, invalid) is a new
      enquiry and notifies as usual.
    """
    if facts.agent_initiated:
        return "agent_initiated"
    if lead.status in _HANDED_OVER and lead.escalation_reason is EscalationReason.B2B_QUALIFIED:
        return "handed_over_b2b"
    return None


def normalise_typification(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def merge_events(existing: Lead | None, phone: str | None, events: list[BotmakerEvent], tag_tier: str = "full",
                 key: str | None = None) -> tuple[Lead, list[str]]:
    """Apply event callbacks. Returns the lead and the typifications that had no mapping."""
    lead = existing.model_copy(deep=True) if existing is not None else new_lead(phone, key)
    unmapped: list[str] = []
    for event in events:
        name = (event.name or "").strip().lower()
        agent = event.info_value("agentName", "agentId", "agent", "operatorId", "operatorName")
        if name in CLOSE_EVENTS:
            if agent and not lead.assigned_to:
                lead.assigned_to = agent
            typification = event.info_value("typification")
            if typification:
                status = TYPIFICATION_TO_STATUS.get(normalise_typification(typification))
                if status is None:
                    unmapped.append(typification)
                else:
                    lead.status = status
        elif name in ASSIGNMENT_EVENTS:
            target = agent or event.info_value("queueId", "queue", "queueName")
            if target:
                lead.assigned_to = target
            if lead.status in (LeadStatus.NEW, LeadStatus.QUALIFIED):
                lead.status = LeadStatus.HANDED_OFF
    lead.tags = build_tags(lead, tier_dimensions(tag_tier))
    return lead, unmapped


def tier_dimensions(tag_tier: str) -> tuple[str, ...]:
    return TIER_LITE_DIMENSIONS if tag_tier == "lite" else TIER_FULL_DIMENSIONS
