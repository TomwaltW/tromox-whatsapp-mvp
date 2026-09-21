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
        content = card.to_markdown()
        encoded = content.encode("utf-8")
        if len(encoded) > _MAX_BYTES:
            content = encoded[: _MAX_BYTES - 3].decode("utf-8", errors="ignore") + "..."
        return {"msgtype": "markdown", "markdown": {"content": content}}

    def send(self, card: LeadCard) -> None:
        data = post_json(self._url, self.build_body(card), channel=self.name, client=self._client)
        if data.get("errcode", 0) not in (0, "0"):
            raise NotifyError(f"wecom: errcode {data.get('errcode')}")
