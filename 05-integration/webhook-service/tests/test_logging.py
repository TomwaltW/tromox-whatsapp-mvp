"""How JsonFormatter passes `extra` fields through.

Contract: every `log.info(..., extra={...})` key whose value is str / int / float / bool / None
reaches the JSON line; string values are redacted; dict / list / objects are DROPPED, not turned
into strings (so a whole payload never lands in a log); standard LogRecord attributes and keys
starting with `_` are not passed through.
"""
from __future__ import annotations

import json
import logging
import sys

from app.logging_setup import JsonFormatter, mask_phone, redact

PHONE = "+4917604069012"


def _format(msg: str = "hello", *, exc_info=None, **extra) -> dict:
    record = logging.getLogger("tromox.test").makeRecord(
        "tromox.test", logging.INFO, __file__, 42, msg, (), exc_info, extra=extra or None
    )
    return json.loads(JsonFormatter().format(record))


def test_header_keys_are_fixed_and_first():
    data = _format("lead upserted")
    assert list(data)[:4] == ["ts", "level", "logger", "msg"]
    assert data["level"] == "INFO" and data["logger"] == "tromox.test"


def test_simple_extra_values_pass_through():
    data = _format("forget done", leads=1, raw_events=0, ratio=0.5, flag=True, none=None)
    assert data["leads"] == 1
    assert data["raw_events"] == 0
    assert data["ratio"] == 0.5
    assert data["flag"] is True
    assert "none" in data and data["none"] is None


def test_string_extra_and_message_are_redacted():
    data = _format(f"lead forgotten, phone {PHONE} in msg", note=f"call {PHONE} back")
    assert data["note"] == "call ***9012 back"
    assert mask_phone(PHONE) in data["msg"]
    assert "4917604069012" not in json.dumps(data)


def test_standard_record_attributes_are_not_leaked():
    data = _format("hello", leads=1)
    leaked = {"pathname", "lineno", "args", "created", "thread", "process", "levelname", "name",
              "funcName", "module", "filename", "msecs", "relativeCreated", "processName",
              "threadName", "exc_text", "stack_info", "message", "asctime"} & set(data)
    assert not leaked, f"standard LogRecord attributes leaked into the log line: {sorted(leaked)}"


def test_known_keys_come_before_custom_keys_which_are_sorted():
    data = _format("done", leads=1, lead_id="L-x", alpha=2, outcome="lead_upserted", zulu=3)
    keys = list(data)
    # _EXTRA_KEYS order: outcome before lead_id; the custom keys follow, sorted by name
    assert keys[4:] == ["outcome", "lead_id", "alpha", "leads", "zulu"]


def test_container_and_private_extras_are_dropped():
    data = _format("done", payload={"a": 1}, items=[1, 2], obj=object(), _secret="x", leads=1)
    assert "payload" not in data and "items" not in data and "obj" not in data
    assert "_secret" not in data
    assert data["leads"] == 1  # simple values on the same record are unaffected


def test_custom_extra_cannot_overwrite_the_fixed_header_keys():
    data = _format("hello", level="bogus", logger="bogus", ts="bogus")
    assert data["level"] == "INFO" and data["logger"] == "tromox.test"
    assert data["ts"].endswith("+00:00")


def test_exception_line_is_still_redacted():
    try:
        raise ValueError(f"boom {PHONE}")
    except ValueError:
        data = _format("failed", exc_info=sys.exc_info(), error_type="ValueError")
    assert data["error_type"] == "ValueError"
    assert "4917604069012" not in data["exc"]
    assert redact(f"boom {PHONE}") in data["exc"]
