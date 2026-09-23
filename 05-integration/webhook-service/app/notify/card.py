"""The sales summary card - built once, rendered per channel.

Privacy: the phone number is masked by default (last 4 digits only); the salesperson opens
the chat inside Botmaker, on the company number, to see the rest.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tromox_lead import EscalationReason, Lead, Segment, effective_country

from ..logging_setup import mask_phone

WINDOW = timedelta(hours=24)

log = logging.getLogger(__name__)

REASON_ZH: dict[EscalationReason, str] = {
    EscalationReason.HUMAN_REQUESTED: "客户要求人工",
    EscalationReason.B2B_QUALIFIED: "B 端信息已收集完成",
    EscalationReason.LOW_CONFIDENCE: "AI 把握不足，需人工判断",
    EscalationReason.COMPLAINT_WARRANTY_LEGAL_SAFETY: "投诉 / 质保争议 / 法律 / 安全",
    EscalationReason.PRICE_NEGOTIATION: "价格或合作条款谈判",
    EscalationReason.NOT_UNDERSTOOD_TWICE: "AI 连续两次未理解",
}
SEGMENT_ZH = {Segment.B2B: "B 端", Segment.B2C: "C 端", Segment.UNKNOWN: "未分类"}


@dataclass(frozen=True)
class LeadCard:
    lead_id: str
    title: str
    priority: str                      # "high" | "normal" | ""
    fields: list[tuple[str, str]] = field(default_factory=list)
    summary: str = ""
    footer: str = ""
    link_url: str | None = None
    link_text: str = "在 Botmaker 中用公司号接手"

    def to_markdown(self) -> str:
        lines = [f"**{self.title}**", ""]
        lines += [f"**{label}**：{value}" for label, value in self.fields]
        if self.summary:
            lines += ["", f"**AI 摘要**：{self.summary}"]
        if self.link_url:
            lines += ["", f"[{self.link_text}]({self.link_url})"]
        if self.footer:
            lines += ["", self.footer]
        return "\n".join(lines)

    def to_text(self) -> str:
        lines = [self.title, ""]
        lines += [f"{label}：{value}" for label, value in self.fields]
        if self.summary:
            lines += ["", f"AI 摘要：{self.summary}"]
        if self.link_url:
            lines += ["", f"{self.link_text}：{self.link_url}"]
        if self.footer:
            lines += ["", self.footer]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        return {
            "lead_id": self.lead_id, "title": self.title, "priority": self.priority,
            "fields": [{"label": label, "value": value} for label, value in self.fields],
            "summary": self.summary, "footer": self.footer, "link_url": self.link_url,
        }


def _tz(name: str) -> tuple[ZoneInfo | timezone, str]:
    """The zone for the window deadline and the label printed next to it.

    Settings refuses an unknown DISPLAY_TIMEZONE at startup, so the fallback is defence only:
    an unknown name renders the deadline in UTC, labels it (UTC) -- never the name that was not
    used -- and logs a WARNING on every card built that way.
    """
    try:
        return ZoneInfo(name), name
    except (ZoneInfoNotFoundError, ValueError, OSError):
        log.warning("unknown display timezone %r, card deadline shown in UTC", name)
        return timezone.utc, "UTC"


def window_deadline(lead: Lead) -> datetime | None:
    """End of the 24-hour customer service window = customer's last message + 24 h."""
    return lead.last_message_ts + WINDOW if lead.last_message_ts else None


def build_card(lead: Lead, *, customer_id: str | None, mask: bool, chat_url_template: str,
               display_timezone: str, now: datetime | None = None) -> LeadCard:
    now = now or datetime.now(timezone.utc)
    zone, zone_label = _tz(display_timezone)
    country = effective_country(lead.country_stated, lead.country_by_phone) or "未知"
    kind = lead.b2b_type.value if lead.b2b_type else (lead.b2c_intent.value if lead.b2c_intent else "")
    segment_label = SEGMENT_ZH[lead.segment] + (f" / {kind}" if kind else "")
    priority = next((t.removeprefix("prio_") for t in lead.tags if t.startswith("prio_")), "")
    reason = REASON_ZH.get(lead.escalation_reason, "") if lead.escalation_reason else ""

    # AI-extracted company / contact first; the WhatsApp profile name only when both are missing
    # (it is a display fallback, never a qualification signal).
    name = lead.contact_name or (lead.profile_name if not lead.company else None)
    who = " / ".join(part for part in (lead.company, name, lead.role) if part) or "未提供"
    source = lead.source_code or ""
    if lead.source_channel.value != "unknown":
        source = f"{lead.source_channel.value}" + (f"（{lead.source_code}）" if lead.source_code else "")

    fields: list[tuple[str, str]] = [
        ("接管原因", reason or "未注明"),
        ("国家", country + ("（客户自述）" if lead.country_stated else "（按号码国家码）" if lead.country_by_phone else "")),
        ("类型", segment_label),
        ("公司 / 联系人", who),
    ]
    if lead.city_region:
        fields.append(("城市 / 地区", lead.city_region))
    fields.append(("意向产品", "、".join(lead.product_interest) or "未提及"))
    if lead.volume:
        fields.append(("数量", lead.volume))
    if lead.existing_dealer_relationship:
        fields.append(("现有经销关系", lead.existing_dealer_relationship))
    fields.append(("来源", source or "未知"))
    fields.append(("语言", lead.language if lead.language != "und" else "未知"))
    if priority:
        fields.append(("优先级", "高" if priority == "high" else "普通"))
    if lead.phone is None:
        fields.append(("号码", "平台未提供号码，请在 Botmaker 会话内查看；国家需向客户确认"))
    else:
        fields.append(("号码", f"尾号 {mask_phone(lead.phone).lstrip('*')}" if mask else lead.phone))

    deadline = window_deadline(lead)
    if deadline is not None:
        remaining = (deadline - now).total_seconds() / 3600
        local = deadline.astimezone(zone).strftime("%Y-%m-%d %H:%M")
        state = f"剩余约 {remaining:.1f} 小时" if remaining > 0 else "已关闭，只能发已审核的模板消息"
        fields.append(("24 小时窗口截止", f"{local}（{zone_label}），{state}"))

    link = None
    if customer_id and chat_url_template:
        link = chat_url_template.replace("{customer_id}", customer_id)

    title = " | ".join(part for part in ("新线索待接手", segment_label, country) if part)
    footer = "请在窗口截止前，在 Botmaker 内用公司号回复；不要转到个人 WhatsApp。"
    return LeadCard(lead_id=lead.lead_id, title=title, priority=priority, fields=fields,
                    summary=lead.ai_summary, footer=footer, link_url=link)
