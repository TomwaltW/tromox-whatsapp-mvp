"""Deterministic identifiers."""
from __future__ import annotations

import hashlib

PLATFORM_KEY_PREFIX = "bm:"


def contact_key(phone_e164: str | None, customer_id: str | None) -> str | None:
    """Dedupe key of a contact: the E.164 phone, else "bm:<platform customer id>", else None."""
    if phone_e164:
        return phone_e164
    if customer_id and str(customer_id).strip():
        return f"{PLATFORM_KEY_PREFIX}{str(customer_id).strip()}"
    return None


def lead_id_for_contact(key: str) -> str:
    """Stable per contact key, so re-processing the same webhook is idempotent."""
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"L-{digest}"


def lead_id_for_phone(phone_e164: str) -> str:
    """Same as lead_id_for_contact; kept as the readable name for the common case."""
    return lead_id_for_contact(phone_e164)
