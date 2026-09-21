"""Helpers shared by the webhook-service tests (imported by name: tests/ is not a package,
and the module name is unique so it cannot collide with another sub-project's helpers)."""
from __future__ import annotations

import json
from pathlib import Path

from app.notify import LeadCard, NotifyError
from app.retry import RetryPolicy

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TOKEN = "test-token"
HEADERS = {"auth-bm-token": TOKEN}
NO_WAIT = RetryPolicy(attempts=3, base_delay=0.0)


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class RecordingNotifier:
    """Fails `fail_times` times, then records every card it is asked to send."""

    def __init__(self, name: str = "recording", fail_times: int = 0) -> None:
        self.name = name
        self.fail_times = fail_times
        self.calls = 0
        self.cards: list[LeadCard] = []
        self.on_send = None

    def send(self, card: LeadCard) -> None:
        self.calls += 1
        if self.on_send:
            self.on_send()
        if self.calls <= self.fail_times:
            raise NotifyError(f"{self.name}: simulated failure")
        self.cards.append(card)
