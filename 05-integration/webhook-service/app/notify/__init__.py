"""Sales notifications: one card, several channels."""
from __future__ import annotations

from ..config import Settings
from .base import Notifier, NotifyError
from .card import LeadCard, build_card
from .email_smtp import EmailNotifier
from .feishu import FeishuNotifier
from .generic import GenericWebhookNotifier
from .wecom import WeComNotifier

__all__ = [
    "EmailNotifier", "FeishuNotifier", "GenericWebhookNotifier", "LeadCard", "Notifier",
    "NotifyError", "WeComNotifier", "build_card", "build_notifiers",
]


def build_notifiers(settings: Settings) -> list[Notifier]:
    """Instantiate the channels named in NOTIFIERS; a named channel without its URL is a config error."""
    notifiers: list[Notifier] = []
    for name in settings.notifier_list:
        if name == "feishu":
            _require(settings.feishu_webhook_url, "FEISHU_WEBHOOK_URL")
            notifiers.append(FeishuNotifier(settings.feishu_webhook_url, settings.feishu_signing_secret or None))
        elif name == "wecom":
            _require(settings.wecom_webhook_url, "WECOM_WEBHOOK_URL")
            notifiers.append(WeComNotifier(settings.wecom_webhook_url))
        elif name == "generic":
            _require(settings.generic_webhook_url, "GENERIC_WEBHOOK_URL")
            notifiers.append(GenericWebhookNotifier(settings.generic_webhook_url))
        elif name == "email":
            _require(settings.smtp_host, "SMTP_HOST")
            _require(settings.email_from, "EMAIL_FROM")
            _require(settings.email_to, "EMAIL_TO")
            notifiers.append(EmailNotifier(
                host=settings.smtp_host, port=settings.smtp_port, username=settings.smtp_username or None,
                password=settings.smtp_password or None, sender=settings.email_from,
                recipients=settings.email_to_list,
            ))
        else:
            raise ValueError(f"unknown notifier: {name!r}")
    return notifiers


def _require(value: str, env_name: str) -> None:
    if not value:
        raise ValueError(f"{env_name} must be set for the selected notifier")
