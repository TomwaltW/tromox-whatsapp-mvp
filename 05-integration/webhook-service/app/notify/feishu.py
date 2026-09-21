"""Feishu (Lark) group custom-bot notifier.

Signature (optional, when the bot has "signature verification" enabled), per Feishu's
custom-bot guide: sign = base64(HMAC-SHA256(key = f"{timestamp}\\n{secret}", msg = b"")).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Any, Callable

import httpx

from ._http import post_json
from .base import NotifyError
from .card import LeadCard


def feishu_sign(timestamp: int | str, secret: str) -> str:
    key = f"{timestamp}\n{secret}".encode("utf-8")
    return base64.b64encode(hmac.new(key, digestmod=hashlib.sha256).digest()).decode("utf-8")


class FeishuNotifier:
    name = "feishu"

    def __init__(self, webhook_url: str, signing_secret: str | None = None, *,
                 client: httpx.Client | None = None, clock: Callable[[], float] = time.time) -> None:
        self._url = webhook_url
        self._secret = signing_secret
        self._client = client
        self._clock = clock

    def build_body(self, card: LeadCard) -> dict[str, Any]:
        lines = [f"**{label}**：{value}" for label, value in card.fields]
        if card.summary:
            lines.append(f"**AI 摘要**：{card.summary}")
        elements: list[dict[str, Any]] = [{"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}}]
        if card.link_url:
            elements.append({"tag": "action", "actions": [{
                "tag": "button", "type": "primary", "url": card.link_url,
                "text": {"tag": "plain_text", "content": card.link_text},
            }]})
        if card.footer:
            elements.append({"tag": "note", "elements": [{"tag": "plain_text", "content": card.footer}]})
        body: dict[str, Any] = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {"template": "red" if card.priority == "high" else "blue",
                           "title": {"tag": "plain_text", "content": card.title}},
                "elements": elements,
            },
        }
        if self._secret:
            timestamp = str(int(self._clock()))
            body["timestamp"] = timestamp
            body["sign"] = feishu_sign(timestamp, self._secret)
        return body

    def send(self, card: LeadCard) -> None:
        data = post_json(self._url, self.build_body(card), channel=self.name, client=self._client)
        code = data.get("code", data.get("StatusCode", 0))
        if code not in (0, "0", None):
            raise NotifyError(f"feishu: API code {code}")
