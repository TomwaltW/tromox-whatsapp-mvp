"""Source short-code parsing: "Hi Tromox! [IG-2609]" -> ("IG-2609", instagram).

Format (01-design/source-tracking.md): [<PREFIX>-<YYMM><optional 1-3 char suffix>]
Brackets are optional when parsing because users sometimes edit the prefilled text.
"""
from __future__ import annotations

import re

from .enums import SOURCE_PREFIX_TO_CHANNEL, SourceChannel

_PREFIXES = "|".join(sorted(SOURCE_PREFIX_TO_CHANNEL, key=len, reverse=True))
_CODE_RE = re.compile(
    rf"(?<![A-Za-z0-9])\[?\s*(?P<prefix>{_PREFIXES})-(?P<yymm>\d{{4}})(?P<suffix>[A-Za-z0-9]{{0,3}})\s*\]?(?![A-Za-z0-9])",
    re.IGNORECASE,
)


def parse_source_code(text: str | None) -> tuple[str | None, SourceChannel]:
    """Return (normalised code or None, channel). Channel is UNKNOWN without a code."""
    if not text:
        return None, SourceChannel.UNKNOWN
    match = _CODE_RE.search(text)
    if not match:
        return None, SourceChannel.UNKNOWN
    prefix = match.group("prefix").upper()
    code = f"{prefix}-{match.group('yymm')}{match.group('suffix').upper()}"
    return code, SOURCE_PREFIX_TO_CHANNEL[prefix]


def strip_source_code(text: str) -> str:
    """Remove the short code so it does not pollute language detection / AI input."""
    return re.sub(r"\s{2,}", " ", _CODE_RE.sub("", text)).strip()


def build_prefill(code: str, greeting: str = "Hi Tromox!") -> str:
    return f"{greeting} [{code.upper()}]"
