"""E-mail notifier via smtplib (STARTTLS on 587, implicit TLS on 465).

The module is deliberately not called `email.py`: that name would shadow the standard
library package `email` (which smtplib itself imports) for anyone running a script from
this directory.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Callable

from .base import NotifyError
from .card import LeadCard

SmtpFactory = Callable[[str, int], smtplib.SMTP]


def _default_factory(host: str, port: int) -> smtplib.SMTP:
    if port == 465:
        return smtplib.SMTP_SSL(host, port, timeout=15)
    return smtplib.SMTP(host, port, timeout=15)


class EmailNotifier:
    name = "email"

    def __init__(self, *, host: str, port: int, sender: str, recipients: list[str],
                 username: str | None = None, password: str | None = None,
                 smtp_factory: SmtpFactory = _default_factory) -> None:
        self._host, self._port = host, port
        self._sender, self._recipients = sender, recipients
        self._username, self._password = username, password
        self._factory = smtp_factory

    def build_message(self, card: LeadCard) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = card.title
        message["From"] = self._sender
        message["To"] = ", ".join(self._recipients)
        message.set_content(card.to_text())
        return message

    def send(self, card: LeadCard) -> None:
        try:
            with self._factory(self._host, self._port) as smtp:
                if self._port != 465:
                    smtp.starttls()
                if self._username:
                    smtp.login(self._username, self._password or "")
                smtp.send_message(self.build_message(card))
        except (smtplib.SMTPException, OSError) as exc:
            raise NotifyError(f"email: {type(exc).__name__}") from None
