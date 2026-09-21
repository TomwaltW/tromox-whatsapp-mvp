"""Configuration - environment variables only (names frozen in the integration contract).

Nothing secret lives in code. `.env` in the working directory is read when present.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

STORAGE_SINKS_AVAILABLE = ("sqlite", "csv", "feishu_bitable", "gsheets")
NOTIFIERS_AVAILABLE = ("feishu", "wecom", "generic", "email")


def _split(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False,
    )

    # --- inbound security -------------------------------------------------------------
    botmaker_webhook_token: str = ""          # must equal the `auth-bm-token` header
    allowed_ips: str = ""                     # optional comma list of IPs / CIDRs

    # --- storage ------------------------------------------------------------------------
    database_path: Path = Path("data/leads.db")
    csv_export_path: Path = Path("data/leads.csv")
    storage_backends: str = "sqlite,csv"
    keep_raw_payloads: bool = False           # trial only: keep raw callbacks to capture real samples

    # --- notifications ------------------------------------------------------------------
    notifiers: str = ""
    feishu_webhook_url: str = ""
    feishu_signing_secret: str = ""
    wecom_webhook_url: str = ""
    generic_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""
    notify_mask_phone: bool = True
    botmaker_chat_url_template: str = "https://go.botmaker.com/#/chats/{customer_id}"
    display_timezone: str = "Asia/Shanghai"

    # --- behaviour ----------------------------------------------------------------------
    tag_tier: Literal["full", "lite"] = "full"
    log_level: str = "INFO"

    @field_validator("tag_tier", mode="before")
    @classmethod
    def _v_tier(cls, value: object) -> object:
        return str(value).strip().lower() if isinstance(value, str) else value

    @property
    def storage_backend_list(self) -> list[str]:
        return _split(self.storage_backends)

    @property
    def notifier_list(self) -> list[str]:
        return _split(self.notifiers)

    @property
    def allowed_ip_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_ips.split(",") if item.strip()]

    @property
    def email_to_list(self) -> list[str]:
        return [item.strip() for item in self.email_to.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
