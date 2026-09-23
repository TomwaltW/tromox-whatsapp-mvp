"""Botmaker webhook payload models (format v1.1).

【待核实】 The structure follows the example in Botmaker's help centre (SOURCES S-B6) and has
NOT been confirmed against a real callback yet (how to capture one: README section 9), so type drift is absorbed:
fields are optional, unknown keys ignored, a number sent for a text field becomes a string, `messages[].date` may be
ISO or epoch s / ms (`normalize.parse_ts`), `clientPayload` any JSON value, `null` for a list / object field = empty.
A different shape (`messages` not a list, `variables` not an object) still fails: `Pipeline.handle` then keeps the
raw callback unprocessed ("validation: <field paths>" in raw_events.error, health alert degraded) for `app.replay`."""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationInfo, field_validator

PayloadKind = Literal["message", "event", "status", "unknown"]


class _Tolerant(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True, coerce_numbers_to_str=True)


class BotmakerMessage(_Tolerant):
    id: str | None = Field(default=None, alias="_id_")
    date: str | int | float | None = None                           # ISO 8601, or epoch seconds / milliseconds
    sender: str | None = Field(default=None, alias="from")        # bot | user | agent
    from_name: str | None = Field(default=None, alias="fromName")
    message: str | None = None
    operator_id: str | None = Field(default=None, alias="operatorId")
    client_payload: Any = Field(default=None, alias="clientPayload")    # button payload: text or an object
    referral: dict[str, Any] | None = None                          # 【待核实】 CTWA passthrough


class BotmakerEventInfo(_Tolerant):
    name: str | None = None
    value: Any = None


class BotmakerEvent(_Tolerant):
    name: str | None = None
    info: Annotated[list[BotmakerEventInfo], BeforeValidator(lambda v: [] if v is None else v)] = Field(default_factory=list)

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

    @field_validator("variables", "messages", "events", "error", mode="before")
    @classmethod
    def _null_means_empty(cls, value: Any, info: ValidationInfo) -> Any:
        """A list / object field sent as `null` means "none", exactly as if the key were missing."""
        if value is None:
            return {} if info.field_name == "variables" else []
        return value

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
