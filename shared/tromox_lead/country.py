"""Country resolution from the phone number (E.164 prefix) - never guessed by the AI.

See 01-design/routing-rules.md section 1. Uses Google's libphonenumber port.
"""
from __future__ import annotations

import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

# Calling codes shared by several territories: the prefix alone is not conclusive, so the
# bot should confirm the market with B2B leads (country_stated).
AMBIGUOUS_CALLING_CODES: frozenset[int] = frozenset({1, 7, 44, 47, 61, 212, 262, 358, 590, 599})


def normalize_e164(raw: str | None, default_region: str | None = None) -> str | None:
    """Return the number in E.164 (+4915112345678) or None when it cannot be parsed.

    WhatsApp / Botmaker deliver numbers without '+', e.g. "551150392540".
    """
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    candidate = text if text.startswith("+") else (f"+{digits}" if default_region is None else text)
    try:
        number = phonenumbers.parse(candidate, default_region)
    except NumberParseException:
        return None
    if not phonenumbers.is_possible_number(number):
        return None
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def country_from_phone(phone_e164: str | None) -> str | None:
    """ISO 3166-1 alpha-2 region for an E.164 number, or None."""
    if not phone_e164:
        return None
    try:
        number = phonenumbers.parse(phone_e164, None)
    except NumberParseException:
        return None
    region = phonenumbers.region_code_for_number(number)
    if region:
        return region
    # Number not valid for any specific region (e.g. test ranges): fall back to the main
    # region of the calling code so the prefix rule still yields an answer.
    fallback = phonenumbers.region_code_for_country_code(number.country_code)
    return fallback if fallback and fallback != "ZZ" else None


def is_ambiguous_calling_code(phone_e164: str | None) -> bool:
    if not phone_e164:
        return False
    try:
        number = phonenumbers.parse(phone_e164, None)
    except NumberParseException:
        return False
    return number.country_code in AMBIGUOUS_CALLING_CODES


def effective_country(country_stated: str | None, country_by_phone: str | None) -> str | None:
    """What the customer says (asked of B2B leads only) wins over the phone prefix."""
    return (country_stated or country_by_phone or None)
