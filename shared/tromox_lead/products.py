"""Product catalogue codes and alias normalisation.

Codes come from Tromox public websites (see SOURCES.md, item 3.3-8). They are model
*family names only* - no specs, prices or warranty terms live here. The current
line-up must be confirmed by the client 【待客户确认】.
"""
from __future__ import annotations

import re
from typing import Iterable

PRODUCT_CATALOG: tuple[str, ...] = ("MC10", "UKKO", "M05", "MINO", "M03", "PESGO")

# Lower-cased alias (spaces / dashes removed) -> canonical code.
_ALIASES: dict[str, str] = {
    "mc10": "MC10",
    "mc10trailx": "MC10",
    "mc10streetx": "MC10",
    "trailx": "MC10",
    "streetx": "MC10",
    "ukko": "UKKO",
    "ukkos": "UKKO",
    "ukkos+": "UKKO",
    "ukkosplus": "UKKO",
    "ukkopro": "UKKO",
    "m05": "M05",
    "m05pro": "M05",
    "mino": "MINO",
    "minob": "MINO",
    "m03": "M03",
    "pesgo": "PESGO",
    "pesgoplus": "PESGO",
    "pesgoc": "PESGO",
}

_SPLIT_RE = re.compile(r"[;,/|]+")
_CLEAN_RE = re.compile(r"[\s\-_.]+")


def normalize_product(raw: str) -> str | None:
    """Map a free-text model mention to a catalogue code, or None if unknown."""
    key = _CLEAN_RE.sub("", raw.strip().lower())
    if not key:
        return None
    if key in _ALIASES:
        return _ALIASES[key]
    # Longest-prefix match so "ukko s+ 2026" still resolves to UKKO.
    for alias in sorted(_ALIASES, key=len, reverse=True):
        if key.startswith(alias):
            return _ALIASES[alias]
    return None


def normalize_products(raw: str | Iterable[str] | None) -> list[str]:
    """Normalise a list (or a ';'/','-separated string) into sorted unique codes."""
    if raw is None:
        return []
    items: Iterable[str] = _SPLIT_RE.split(raw) if isinstance(raw, str) else raw
    found = {code for item in items if item and (code := normalize_product(str(item)))}
    return sorted(found)
