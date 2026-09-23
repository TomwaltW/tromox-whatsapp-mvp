"""Turn raw model text into a validated tromox_lead.AIExtraction.

Tolerates what models really do (markdown fences, a sentence before or after the JSON,
"null" written as a string) and rejects what production cannot use (no JSON object,
truncated JSON, b2b_type / b2c_intent / escalation_reason values outside their enums).
A `segment` value other than B2B / B2C is not rejected: the shared model maps it to unknown,
exactly as production does, so it counts as parsed (and a gold-B2B sample still counts as a miss).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import ValidationError

from tromox_lead import AI_EXTRACTION_FIELDS, AIExtraction

_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*\n?(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class ParseResult:
    extraction: AIExtraction | None
    error: str | None = None
    missing_keys: tuple[str, ...] = ()
    extra_keys: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.extraction is not None


def _balanced_objects(text: str):
    """Yield every top-level {...} substring, honouring JSON string quoting."""
    depth = 0
    start = -1
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"' and depth > 0:
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                yield text[start : index + 1]
                start = -1


def extract_json_object(text: str) -> dict | None:
    """First JSON object found in `text` (fenced blocks are tried first), or None."""
    if not text or not text.strip():
        return None
    candidates = [m.group(1) for m in _FENCE_RE.finditer(text)] + [text]
    for candidate in candidates:
        for chunk in _balanced_objects(candidate):
            try:
                value = json.loads(chunk)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
    return None


def parse_extraction(text: str) -> ParseResult:
    obj = extract_json_object(text)
    if obj is None:
        return ParseResult(None, error="no valid JSON object in the model output")
    missing = tuple(k for k in AI_EXTRACTION_FIELDS if k not in obj)
    extra = tuple(k for k in obj if k not in AI_EXTRACTION_FIELDS)
    if len(missing) == len(AI_EXTRACTION_FIELDS):
        return ParseResult(None, error="JSON object has none of the expected keys", extra_keys=extra)
    try:
        extraction = AIExtraction.model_validate(obj)
    except ValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(p) for p in first["loc"]) or "object"
        return ParseResult(None, error=f"schema validation failed at {location}: {first['msg']}",
                           missing_keys=missing, extra_keys=extra)
    return ParseResult(extraction, missing_keys=missing, extra_keys=extra)
