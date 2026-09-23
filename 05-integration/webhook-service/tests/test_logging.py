"""How JsonFormatter passes `extra` fields through, and how bot URLs are kept out of the log.

Contract: every `log.info(..., extra={...})` key whose value is str / int / float / bool / None
reaches the JSON line; string values are redacted; dict / list / objects are DROPPED, not turned
into strings (so a whole payload never lands in a log); standard LogRecord attributes and keys
starting with `_` are not passed through, nor is uvicorn's `color_message`.

The Feishu / WeCom bot URLs embed their secret. Layer 1: `setup_logging` keeps the httpx /
httpcore loggers at WARNING or above, so the request line (with the full URL) is never emitted,
not even at DEBUG. Layer 2: the formatter cuts path and query off any URL on those hosts.
"""
from __future__ import annotations

import io
import json
import logging
import sys

import httpx
import pytest

from app.logging_setup import JsonFormatter, mask_phone, redact, setup_logging
from app.notify import FeishuNotifier, WeComNotifier

PHONE = "+4917604069012"
FEISHU_TOKEN = "FEISHU-HOOK-TOKEN-4711"
WECOM_KEY = "WECOM-KEY-0815"
FEISHU_URL = f"https://open.feishu.cn/open-apis/bot/v2/hook/{FEISHU_TOKEN}"
LARK_URL = f"https://open.larksuite.com/open-apis/bot/v2/hook/{FEISHU_TOKEN}"
WECOM_URL = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WECOM_KEY}"
_PINNED = ("httpx", "httpcore", "uvicorn", "uvicorn.error", "uvicorn.access")


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


# ------------------------------------------------------------------ bot URLs and setup_logging
@pytest.fixture
def restore_logging():
    """setup_logging changes process-wide logger state; put it back so other tests are unaffected."""
    root = logging.getLogger()
    saved_root = (root.handlers[:], root.level)
    saved = {name: (logging.getLogger(name).handlers[:], logging.getLogger(name).level,
                    logging.getLogger(name).propagate) for name in _PINNED}
    yield
    root.handlers[:] = saved_root[0]
    root.setLevel(saved_root[1])
    for name, (handlers, level, propagate) in saved.items():
        logger = logging.getLogger(name)
        logger.handlers[:] = handlers
        logger.setLevel(level)
        logger.propagate = propagate


def _captured(level: str) -> io.StringIO:
    """setup_logging(level), then point our JSON handler at a buffer instead of stdout."""
    setup_logging(level)
    buf = io.StringIO()
    handlers = [h for h in logging.getLogger().handlers if getattr(h, "_tromox_json", False)]
    assert len(handlers) == 1
    handlers[0].setStream(buf)
    return buf


def _ok_client() -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={"code": 0, "errcode": 0, "StatusCode": 0})))


def _send_both(client: httpx.Client) -> None:
    WeComNotifier(WECOM_URL, client=client).send_text("t", "x")
    FeishuNotifier(FEISHU_URL, client=client).send_text("t", "x")


@pytest.mark.parametrize("level", ["INFO", "DEBUG"])
def test_notifier_requests_do_not_write_the_bot_secret_to_the_log(restore_logging, level):
    buf = _captured(level)
    _send_both(_ok_client())
    logging.getLogger("app.pipeline").log(logging.getLevelName(level), "card sent", extra={"channel": "feishu"})
    text = buf.getvalue()
    assert "card sent" in text                     # the handler did capture at this level
    assert FEISHU_TOKEN not in text and WECOM_KEY not in text
    assert "HTTP Request" not in text              # layer 1: httpx's request line is not emitted at all


@pytest.mark.parametrize(("level", "expected"), [
    ("DEBUG", logging.WARNING), ("INFO", logging.WARNING), ("WARNING", logging.WARNING), ("ERROR", logging.ERROR),
])
def test_http_client_loggers_stay_at_warning_or_above(restore_logging, level, expected):
    setup_logging(level)
    assert logging.getLogger("httpx").level == expected
    assert logging.getLogger("httpcore").level == expected


def test_a_request_line_that_does_get_through_is_cut_to_the_host(restore_logging):
    # Layer 2 on the real httpx path: undo the pin and let httpx log its INFO request lines.
    buf = _captured("INFO")
    logging.getLogger("httpx").setLevel(logging.INFO)
    _send_both(_ok_client())
    text = buf.getvalue()
    assert "HTTP Request" in text                  # httpx did log, with the URL in the message
    assert FEISHU_TOKEN not in text and WECOM_KEY not in text
    assert "https://open.feishu.cn/<redacted>" in text and "https://qyapi.weixin.qq.com/<redacted>" in text


def test_formatter_cuts_bot_urls_in_message_extras_and_traceback():
    try:
        raise RuntimeError(f"post to {WECOM_URL} failed")
    except RuntimeError:
        data = _format(f"posting to {FEISHU_URL} and {LARK_URL}", exc_info=sys.exc_info(),
                       note=f"retry {WECOM_URL}", other="https://hooks.example.com/relay/abc")
    blob = json.dumps(data, ensure_ascii=False)
    assert FEISHU_TOKEN not in blob and WECOM_KEY not in blob
    assert data["msg"] == "posting to https://open.feishu.cn/<redacted> and https://open.larksuite.com/<redacted>"
    assert data["note"] == "retry https://qyapi.weixin.qq.com/<redacted>"
    assert "https://qyapi.weixin.qq.com/<redacted> failed" in data["exc"]
    assert data["other"] == "https://hooks.example.com/relay/abc"    # other hosts are left as they are
    assert _format("base url https://open.feishu.cn")["msg"] == "base url https://open.feishu.cn"


def test_uvicorn_color_message_extra_is_dropped(restore_logging):
    data = _format("Uvicorn running", color_message="\x1b[36mUvicorn running\x1b[0m", leads=1)
    assert "color_message" not in data and data["leads"] == 1

    buf = _captured("INFO")
    logging.getLogger("uvicorn.error").info("Uvicorn running", extra={"color_message": "\x1b[36mX\x1b[0m"})
    line = json.loads(buf.getvalue().strip().splitlines()[-1])
    assert line["msg"] == "Uvicorn running" and "color_message" not in line
    assert "\x1b" not in buf.getvalue() and "\\u001b" not in buf.getvalue()
