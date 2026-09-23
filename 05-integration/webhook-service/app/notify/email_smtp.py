"""E-mail notifier via smtplib (STARTTLS on 587, implicit TLS on 465).

Both paths verify the server certificate and host name (`ssl.create_default_context()`):
without an explicit context smtplib encrypts but trusts any certificate, so a man in the
middle would receive SMTP_PASSWORD and the lead card. A failed verification is an OSError
(`ssl.SSLCertVerificationError`) and surfaces as `NotifyError("email: SSLCertVerificationError")`.

The module is deliberately not called `email.py`: that name would shadow the standard
library package `email` (which smtplib itself imports) for anyone running a script from
this directory.
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Callable

from .base import NotifyError
from .card import LeadCard

SmtpFactory = Callable[[str, int], smtplib.SMTP]


def _tls_context() -> ssl.SSLContext:
    """Certificate + host name verification (CERT_REQUIRED, check_hostname) with the system CAs."""
    return ssl.create_default_context()


def _default_factory(host: str, port: int) -> smtplib.SMTP:
    if port == 465:
        return smtplib.SMTP_SSL(host, port, timeout=15, context=_tls_context())
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
        return self._message(card.title, card.to_text())

    def build_text_message(self, title: str, text: str) -> EmailMessage:
        return self._message(title, text)

    def _message(self, subject: str, body: str) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._sender
        message["To"] = ", ".join(self._recipients)
        message.set_content(body)
        return message

    def _deliver(self, message: EmailMessage) -> None:
        try:
            with self._factory(self._host, self._port) as smtp:
                if self._port != 465:
                    smtp.starttls(context=_tls_context())
                if self._username:
                    smtp.login(self._username, self._password or "")
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            raise NotifyError(f"email: {type(exc).__name__}") from None

    def send(self, card: LeadCard) -> None:
        self._deliver(self.build_message(card))

    def send_text(self, title: str, text: str) -> None:
        self._deliver(self.build_text_message(title, text))
