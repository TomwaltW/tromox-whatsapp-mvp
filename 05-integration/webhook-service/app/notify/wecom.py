"""WeCom (企业微信) group-bot notifier - markdown message."""
from __future__ import annotations

from typing import Any

import httpx

from ._http import post_json
from .base import NotifyError
from .card import LeadCard

_MAX_BYTES = 4096  # WeCom markdown content limit


class WeComNotifier:
    name = "wecom"

    def __init__(self, webhook_url: str, *, client: httpx.Client | None = None) -> None:
        self._url = webhook_url
        self._client = client

    def build_body(self, card: LeadCard) -> dict[str, Any]:
        return self._markdown(card.to_markdown())

    def build_text_body(self, title: str, text: str) -> dict[str, Any]:
        return self._markdown(f"# {title}\n{text}")

    @staticmethod
    def _markdown(content: str) -> dict[str, Any]:
        encoded = content.encode("utf-8")
        if len(encoded) > _MAX_BYTES:
            content = encoded[: _MAX_BYTES - 3].decode("utf-8", errors="ignore") + "..."
        return {"msgtype": "markdown", "markdown": {"content": content}}

    def _post(self, body: dict[str, Any]) -> None:
        data = post_json(self._url, body, channel=self.name, client=self._client)
        if data.get("errcode", 0) not in (0, "0"):
            raise NotifyError(f"wecom: errcode {data.get('errcode')}")

    def send(self, card: LeadCard) -> None:
        self._post(self.build_body(card))

    def send_text(self, title: str, text: str) -> None:
        self._post(self.build_text_body(title, text))
