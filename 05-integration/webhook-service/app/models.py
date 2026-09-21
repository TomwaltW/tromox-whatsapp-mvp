"""Botmaker webhook payload models (format v1.1).

【待核实】 The structure follows the example in Botmaker's help centre (SOURCES S-B6) and has
NOT been confirmed against a real callback yet. The models are therefore deliberately
tolerant: every field is optional, unknown keys are ignored, dates stay strings and are
parsed later. Capture a real sample during the trial (KEEP_RAW_PAYLOADS=true) and update
`fixtures/` plus this module if anything differs.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PayloadKind = Literal["message", "event", "status", "unknown"]


class _Tolerant(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class BotmakerMessage(_Tolerant):
    id: str | None = Field(default=None, alias="_id_")
    date: str | None = None
    sender: str | None = Field(default=None, alias="from")        # bot | user | agent
    from_name: str | None = Field(default=None, alias="fromName")
    message: str | None = None
    operator_id: str | None = Field(default=None, alias="operatorId")
    client_payload: str | None = Field(default=None, alias="clientPayload")
    referral: dict[str, Any] | None = None                          # 【待核实】 CTWA passthrough


class BotmakerEventInfo(_Tolerant):
    name: str | None = None
    value: Any = None


class BotmakerEvent(_Tolerant):
    name: str | None = None
    info: list[BotmakerEventInfo] = Field(default_factory=list)

    def info_value(self, *names: str) -> str | None:
        wanted = {n.lower() for n in names}
        for item in self.info:
            if item.name and item.name.lower() in wanted and item.value not in (None, ""):
                return str(item.value)
        return None


class BotmakerWebhook(_Tolerant):
    v: str | None = None
    type: str | None = None
    chat_platform: str | None = Field(default=None, alias="chatPlatform")
    contact_id: str | None = Field(default=None, alias="contactId")
    customer_id: str | None = Field(default=None, alias="customerId")
    session_id: str | None = Field(default=None, alias="sessionId")
    whatsapp_number: str | None = Field(default=None, alias="whatsappNumber")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    chat_channel_id: str | None = Field(default=None, alias="chatChannelId")
    customer_creation_time: str | None = Field(default=None, alias="customerCreationTime")
    session_creation_time: str | None = Field(default=None, alias="sessionCreationTime")
    variables: dict[str, Any] = Field(default_factory=dict)
    messages: list[BotmakerMessage] = Field(default_factory=list)
    events: list[BotmakerEvent] = Field(default_factory=list)
    referral: dict[str, Any] | None = None                          # 【待核实】
    # status callbacks (v1.0)
    status: str | None = None
    status_change_time: str | None = Field(default=None, alias="statusChangeTime")
    message_id: str | None = Field(default=None, alias="messageId")
    error: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def kind(self) -> PayloadKind:
        declared = (self.type or "").lower()
        if declared == "message" or self.messages:
            return "message"
        if declared == "event" or self.events:
            return "event"
        if self.status:
            return "status"
        return "unknown"
