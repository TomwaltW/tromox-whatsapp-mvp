"""Shared lead schema and routing rules for the Tromox WhatsApp MVP."""
from .country import (
    AMBIGUOUS_CALLING_CODES,
    country_from_phone,
    effective_country,
    is_ambiguous_calling_code,
    normalize_e164,
)
from .enums import (
    LOW_CONFIDENCE_THRESHOLD,
    SOURCE_PREFIX_TO_CHANNEL,
    SUPPORTED_LANGUAGES,
    B2BType,
    B2CIntent,
    EscalationReason,
    LeadStatus,
    Segment,
    SourceChannel,
)
from .fields import (
    AI_EXTRACTION_FIELDS,
    BOTMAKER_VARIABLES,
    FIELD_SPECS,
    LABEL_COLUMNS,
    LABEL_ONLY_COLUMNS,
    LEAD_FIELDS,
    FieldSpec,
)
from .ids import contact_key, lead_id_for_contact, lead_id_for_phone
from .language import detect_language
from .products import PRODUCT_CATALOG, normalize_product, normalize_products
from .routing import apply_routing_rules, is_b2b_qualified
from .schema import AIExtraction, Lead, Referral
from .shortcode import build_prefill, parse_source_code, strip_source_code
from .tags import TAG_DIMENSIONS, TIER_FULL_DIMENSIONS, TIER_LITE_DIMENSIONS, build_tags

__all__ = [
    "AI_EXTRACTION_FIELDS", "AMBIGUOUS_CALLING_CODES", "AIExtraction", "B2BType", "B2CIntent",
    "BOTMAKER_VARIABLES", "EscalationReason", "FIELD_SPECS", "FieldSpec", "LABEL_COLUMNS",
    "LABEL_ONLY_COLUMNS", "LEAD_FIELDS", "LOW_CONFIDENCE_THRESHOLD", "Lead", "LeadStatus",
    "PRODUCT_CATALOG", "Referral", "SOURCE_PREFIX_TO_CHANNEL", "SUPPORTED_LANGUAGES", "Segment",
    "SourceChannel", "TAG_DIMENSIONS", "TIER_FULL_DIMENSIONS", "TIER_LITE_DIMENSIONS",
    "apply_routing_rules", "build_prefill", "build_tags", "contact_key", "country_from_phone",
    "detect_language", "effective_country", "is_ambiguous_calling_code", "is_b2b_qualified",
    "lead_id_for_contact", "lead_id_for_phone", "normalize_e164", "normalize_product", "normalize_products",
    "parse_source_code", "strip_source_code",
]
