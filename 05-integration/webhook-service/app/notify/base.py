"""Notifier interface."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .card import LeadCard


class NotifyError(Exception):
    """Delivery failed. The message must never contain the webhook URL (it embeds a secret)."""


@runtime_checkable
class Notifier(Protocol):
    name: str

    def send(self, card: LeadCard) -> None:  # raises NotifyError (or a transport error) on failure
        ...

    def send_text(self, title: str, text: str) -> None:
        """Send a plain text message (weekly report summary, alerts) - no card, no lead details.

        `text` is already rendered, one item per line. Raises NotifyError on failure; as with
        `send`, the error message must never contain the webhook URL. Callers pass summaries
        only, so the message carries no phone number and no URL.
        """
        ...
