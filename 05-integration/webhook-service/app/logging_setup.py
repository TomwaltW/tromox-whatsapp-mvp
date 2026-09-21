"""Structured JSON logs without personal data.

Rules: log `lead_id` (a hash) instead of the phone number; never log message text or
webhook URLs. As a safety net every log line is scrubbed of phone-like digit runs.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone

_PHONE_RE = re.compile(r"(?<![\dA-Za-z])\+?\d{9,15}(?!\d)")
_EXTRA_KEYS = (
    "event_key", "kind", "outcome", "lead_id", "notification_id", "channel", "attempts",
    "status_code", "reason", "typification", "client_ip", "session_id", "error_type",
)


def mask_phone(phone: str | None) -> str:
    """'+4917604069012' -> '***9012'. Used in logs and, by default, in sales notifications."""
    if not phone:
        return ""
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"***{digits[-4:]}" if len(digits) >= 4 else "***"


def redact(text: str) -> str:
    return _PHONE_RE.sub(lambda m: mask_phone(m.group(0)), text)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": redact(record.getMessage()),
        }
        for key in _EXTRA_KEYS:
            if key in record.__dict__:
                payload[key] = record.__dict__[key]
        if record.exc_info:
            payload["exc"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._tromox_json = True  # type: ignore[attr-defined]  # marker: replace only our own handler
    root = logging.getLogger()
    root.handlers[:] = [h for h in root.handlers if not getattr(h, "_tromox_json", False)]
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # uvicorn access logs contain no personal data for this service (token is a header).
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers[:] = []
        logging.getLogger(name).propagate = True
