"""Generic JSON webhook notifier (Slack-compatible relays, Zapier/Make, internal tools)."""
from __future__ import annotations

from typing import Any

import httpx

from ._http import post_json
from .card import LeadCard


class GenericWebhookNotifier:
    name = "generic"

    def __init__(self, webhook_url: str, *, client: httpx.Client | None = None) -> None:
        self._url = webhook_url
        self._client = client

    def build_body(self, card: LeadCard) -> dict[str, Any]:
        return {"event": "lead_escalated", "text": card.to_text(), "card": card.to_dict()}

    def send(self, card: LeadCard) -> None:
        post_json(self._url, self.build_body(card), channel=self.name, client=self._client)
