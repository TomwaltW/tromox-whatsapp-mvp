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
        return self._signed({
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {"template": "red" if card.priority == "high" else "blue",
                           "title": {"tag": "plain_text", "content": card.title}},
                "elements": elements,
            },
        })

    def build_text_body(self, title: str, text: str) -> dict[str, Any]:
        """富文本消息（msg_type: post）：标题 + 每行一段，飞书群里换行不会被吞掉。"""
        content = [[{"tag": "text", "text": line}] for line in text.split("\n")]
        return self._signed({
            "msg_type": "post",
            "content": {"post": {"zh_cn": {"title": title, "content": content}}},
        })

    def _signed(self, body: dict[str, Any]) -> dict[str, Any]:
        if self._secret:
            timestamp = str(int(self._clock()))
            body["timestamp"] = timestamp
            body["sign"] = feishu_sign(timestamp, self._secret)
        return body

    def _post(self, body: dict[str, Any]) -> None:
        data = post_json(self._url, body, channel=self.name, client=self._client)
        code = data.get("code", data.get("StatusCode", 0))
        if code not in (0, "0", None):
            raise NotifyError(f"feishu: API code {code}")

    def send(self, card: LeadCard) -> None:
        self._post(self.build_body(card))

    def send_text(self, title: str, text: str) -> None:
        self._post(self.build_text_body(title, text))
