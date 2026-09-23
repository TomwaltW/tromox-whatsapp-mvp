"""Structured JSON logs without personal data or bot secrets.

Rules: log `lead_id` (a hash) instead of the phone number; never log message text or
webhook URLs. As a safety net every log line is scrubbed of phone-like digit runs.

The Feishu / WeCom bot URLs carry their secret in the URL itself (the hook token path segment,
the `key=` query value). Two layers keep them out of the log:

1. `setup_logging` pins the `httpx` and `httpcore` loggers at max(WARNING, root level). httpx
   logs `HTTP Request: POST <full URL> ...` at INFO, so without the pin every notification
   would write its URL; with it, not even `LOG_LEVEL=DEBUG` prints request lines.
2. `JsonFormatter` scrubs the message, the string extras and the traceback: a URL on one of
   `SECRET_URL_HOSTS` keeps only scheme and host, its path and query become `<redacted>`
   (`https://qyapi.weixin.qq.com/<redacted>`).
   This catches a URL that reaches a log line any other way (a library logging at WARNING,
   an exception text).

uvicorn's `color_message` extra (the same text with ANSI colour codes) is dropped.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone

_PHONE_RE = re.compile(r"(?<![\dA-Za-z])\+?\d{9,15}(?!\d)")
# Hosts whose URLs embed a secret (bot hook token / key); only scheme + host survive in a log line.
SECRET_URL_HOSTS = ("open.feishu.cn", "open.larksuite.com", "qyapi.weixin.qq.com")
_SECRET_URL_RE = re.compile(
    r"(?P<origin>https?://(?:" + "|".join(re.escape(h) for h in SECRET_URL_HOSTS) + r")(?::\d+)?)"
    r"(?P<rest>[/?#][^\s\"'<>]*)",
    re.IGNORECASE,
)
REDACTED = "<redacted>"
# Extras that never reach the JSON line: uvicorn's ANSI-coloured copy of the message.
_DROPPED_EXTRAS = frozenset({"color_message"})
# These keys always come before the other extras, so the common fields keep a stable order.
_EXTRA_KEYS = (
    "event_key", "kind", "outcome", "lead_id", "notification_id", "channel", "attempts",
    "status_code", "reason", "typification", "client_ip", "session_id", "error_type",
)
# Attributes LogRecord brings itself (name / msg / args / pathname / lineno / created / thread ...),
# taken from a blank record so the list cannot drift with the Python version. `message` and
# `asctime` are added by logging.Formatter during formatting and are not caller-supplied extras.
_STANDARD_RECORD_ATTRS = frozenset(
    logging.LogRecord("", logging.NOTSET, "", 0, "", (), None).__dict__
) | {"message", "asctime"}
# Only simple scalars reach the JSON line: dict / list / objects are dropped, not stringified,
# so a whole payload (which may carry the phone number or the message text) never lands in a log.
_SIMPLE_VALUE_TYPES = (str, int, float, bool, type(None))


def mask_phone(phone: str | None) -> str:
    """'+4917604069012' -> '***9012'. Used in logs and, by default, in sales notifications."""
    if not phone:
        return ""
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"***{digits[-4:]}" if len(digits) >= 4 else "***"


def redact(text: str) -> str:
    return _PHONE_RE.sub(lambda m: mask_phone(m.group(0)), text)


def redact_secret_urls(text: str) -> str:
    """'https://open.feishu.cn/open-apis/bot/v2/hook/abc' -> 'https://open.feishu.cn/<redacted>'."""
    return _SECRET_URL_RE.sub(lambda m: f"{m.group('origin')}/{REDACTED}", text)


def _scrub(text: str) -> str:
    """What every string in a JSON log line goes through: bot URLs first, then phone numbers."""
    return redact(redact_secret_urls(text))


def _extra_fields(record: logging.LogRecord) -> dict[str, object]:
    """The `log.info(..., extra={...})` keys that belong in the JSON line, ordered.

    Order: the `_EXTRA_KEYS` that are present first, then the remaining keys sorted by name.
    Dropped: the standard LogRecord attributes, keys starting with `_`, `color_message`, and any
    value that is not str / int / float / bool / None (dict, list and objects are dropped, not
    stringified). String values go through `redact_secret_urls()` and `redact()`.
    """
    extras = {
        key: value
        for key, value in record.__dict__.items()
        if key not in _STANDARD_RECORD_ATTRS
        and key not in _DROPPED_EXTRAS
        and not key.startswith("_")
        and isinstance(value, _SIMPLE_VALUE_TYPES)
    }
    ordered = [key for key in _EXTRA_KEYS if key in extras]
    ordered += sorted(key for key in extras if key not in _EXTRA_KEYS)
    return {
        key: _scrub(extras[key]) if isinstance(extras[key], str) else extras[key]
        for key in ordered
    }


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": _scrub(record.getMessage()),
        }
        for key, value in _extra_fields(record).items():
            if key not in payload:  # a custom key never overwrites one of the four header keys
                payload[key] = value
        if record.exc_info:
            payload["exc"] = _scrub(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._tromox_json = True  # type: ignore[attr-defined]  # marker: replace only our own handler
    root = logging.getLogger()
    root.handlers[:] = [h for h in root.handlers if not getattr(h, "_tromox_json", False)]
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # httpx logs every request with its full URL at INFO, and the bot URLs embed their secret:
    # keep the HTTP client loggers at WARNING or above, whatever LOG_LEVEL says (layer 1 above).
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(max(logging.WARNING, root.level))
    # uvicorn access logs contain no personal data for this service (token is a header).
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers[:] = []
        logging.getLogger(name).propagate = True
