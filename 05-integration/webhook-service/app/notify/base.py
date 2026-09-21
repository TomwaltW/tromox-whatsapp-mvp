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
