"""Configuration - environment variables only (names frozen in the integration contract).

Nothing secret lives in code. `.env` in the working directory is read when present.
"""
from __future__ import annotations

import ipaddress
from functools import lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

STORAGE_SINKS_AVAILABLE = ("sqlite", "csv", "feishu_bitable", "gsheets")
NOTIFIERS_AVAILABLE = ("feishu", "wecom", "generic", "email")


def _split(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def check_timezone(value: str) -> str:
    """Return `value` when ZoneInfo can load it; otherwise ValueError naming the value and an example.

    Used for DISPLAY_TIMEZONE and for `app.demo --timezone`: a typo such as `Asia/Shangai` is
    refused up front instead of every card silently showing UTC.
    """
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        raise ValueError(f"unknown time zone {value!r}; use an IANA name such as Asia/Shanghai") from None
    return value


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
    csv_export_min_interval_s: float = 5.0    # CSV mirror write-behind: one rewrite per interval; 0 = every callback
    storage_backends: str = "sqlite,csv"
    keep_raw_payloads: bool = False           # trial only: keep raw callbacks to capture real samples
    feishu_app_id: str = ""                   # feishu_bitable sink: self-built app credentials
    feishu_app_secret: str = ""
    feishu_bitable_app_token: str = ""        # feishu_bitable sink: which base and which table
    feishu_bitable_table_id: str = ""
    feishu_base_url: str = "https://open.feishu.cn"   # feishu_bitable sink: open platform origin; Lark tenants use https://open.larksuite.com

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

    @field_validator("display_timezone")
    @classmethod
    def _v_display_timezone(cls, value: str) -> str:
        # `DISPLAY_TIMEZONE=` left empty means the default, like FEISHU_BASE_URL; a typo still refuses to start
        return check_timezone(value.strip() or "Asia/Shanghai")

    @field_validator("allowed_ips")
    @classmethod
    def _v_allowed_ips(cls, value: str) -> str:
        """Every comma-separated entry must be an IP or CIDR; empty means no allowlist.

        A bad entry used to be skipped silently when matching, so a space-separated list
        matched nobody and every callback got 403 as if the caller were at fault.
        """
        for item in (part.strip() for part in value.split(",")):
            if not item:
                continue
            try:
                ipaddress.ip_network(item, strict=False)
            except ValueError:
                raise ValueError(
                    f"ALLOWED_IPS entry {item!r} is not an IP address or CIDR; "
                    "多个地址用英文逗号分隔, e.g. 203.0.113.0/24,198.51.100.7"
                ) from None
        return value

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
