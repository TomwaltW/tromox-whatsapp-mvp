"""Field registry: name, type, source, description. Drives every generated artefact."""
from __future__ import annotations

from dataclasses import dataclass

# Source categories used in 01-design/lead-schema.md
SRC_BUTTON = "按钮"
SRC_AI = "AI 抽取"
SRC_RULE = "规则"
SRC_SYSTEM = "系统"
SRC_HUMAN = "人工"


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type_label: str
    source: str
    description: str
    ai_extracted: bool = False
    label_column: bool = False


FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec("lead_id", "string", SRC_SYSTEM, "线索主键，由号码哈希生成（同一号码恒定，保证幂等）；平台未给出号码时改用平台客户 ID 哈希"),
    FieldSpec("phone", "string (E.164) | null", SRC_SYSTEM, "客户 WhatsApp 号码，统一为 E.164（如 +4915112345678）；客户以用户名联系、平台只给出业务范围用户 ID 时为空【待核实】", label_column=True),
    FieldSpec("country_by_phone", "string (ISO 3166-1 alpha-2)", SRC_RULE, "由号码国家码判定的国家，不让 AI 猜"),
    FieldSpec("country_stated", "string (ISO 3166-1 alpha-2) | null", SRC_AI, "客户自述的国家/市场；仅对 B 端追问确认", ai_extracted=True),
    FieldSpec("language", "string (ISO 639-1)", f"{SRC_AI}（{SRC_RULE}兜底）", "客户首条消息的语言", ai_extracted=True, label_column=True),
    FieldSpec("contact_name", "string | null", f"{SRC_AI}（{SRC_SYSTEM}兜底：WhatsApp 昵称）", "联系人姓名", ai_extracted=True),
    FieldSpec("company", "string | null", SRC_AI, "公司/门店名称", ai_extracted=True),
    FieldSpec("role", "string | null", SRC_AI, "职位或身份（如 owner、purchasing manager）", ai_extracted=True),
    FieldSpec("segment", "enum: B2B | B2C | unknown", f"{SRC_BUTTON}（自由文本时 {SRC_AI}）", "B 端 / C 端 / 未知", ai_extracted=True, label_column=True),
    FieldSpec("b2b_type", "enum: dealer | distributor | fleet | importer | other | null", SRC_AI, "B 端类型；非 B 端为 null", ai_extracted=True, label_column=True),
    FieldSpec("b2c_intent", "enum: buy | support | parts | warranty | test_ride | other | null", SRC_AI, "C 端意图；非 C 端为 null", ai_extracted=True, label_column=True),
    FieldSpec("product_interest", "string[]（产品代码）", SRC_AI, "感兴趣的车型代码，按产品目录归一化", ai_extracted=True, label_column=True),
    FieldSpec("volume", "string | null", SRC_AI, "意向数量/频次的原话摘要（如 \"20 units / quarter\"）", ai_extracted=True),
    FieldSpec("city_region", "string | null", SRC_AI, "城市或地区", ai_extracted=True),
    FieldSpec("existing_dealer_relationship", "string | null", SRC_AI, "现有经销关系简述（已代理品牌、是否已是摩兽经销商等）", ai_extracted=True),
    FieldSpec("source_channel", "enum: instagram | facebook | tiktok | youtube | website | ctwa_ad | offline_qr | other | unknown", SRC_RULE, "来源渠道，由短码前缀或广告 referral 判定"),
    FieldSpec("source_code", "string | null", SRC_RULE, "首条消息中的来源短码（如 IG-2609）"),
    FieldSpec("referral", "object | null", SRC_SYSTEM, "Click-to-WhatsApp 广告 referral（source_id、source_url、headline 等）；是否透传【待核实】"),
    FieldSpec("first_message_ts", "datetime (UTC, ISO 8601)", SRC_SYSTEM, "首条消息时间"),
    FieldSpec("last_message_ts", "datetime (UTC, ISO 8601)", SRC_SYSTEM, "客户最后一条消息时间；24 小时客服窗口以此起算"),
    FieldSpec("ai_summary", "string", SRC_AI, "给销售看的一两句话摘要（默认简体中文【待客户确认】）", ai_extracted=True),
    FieldSpec("ai_confidence", "number 0-1", SRC_AI, "模型对 segment 判断的自评置信度；低于 0.6 触发人工", ai_extracted=True),
    FieldSpec("escalation_flag", "boolean", f"{SRC_AI} + {SRC_RULE}", "是否需要人工接管", ai_extracted=True, label_column=True),
    FieldSpec("escalation_reason", "enum: human_requested | b2b_qualified | low_confidence | complaint_warranty_legal_safety | price_negotiation | not_understood_twice | null", f"{SRC_AI} + {SRC_RULE}", "接管原因", ai_extracted=True, label_column=True),
    FieldSpec("assigned_to", "string | null", SRC_SYSTEM, "接手的销售/坐席（来自 Botmaker 分配事件）"),
    FieldSpec("status", "enum: new | qualified | handed_off | contacted | closed_won | closed_lost | nurture | invalid", f"{SRC_SYSTEM} + {SRC_HUMAN}", "线索状态；销售结束会话时回写"),
    FieldSpec("tags", "string[]", SRC_RULE, "按 tag-taxonomy.md 由字段生成的标签"),
    FieldSpec("consent_marketing", "boolean | null", SRC_BUTTON, "是否同意接收营销类消息；未询问为 null"),
    FieldSpec("notes", "string | null", SRC_HUMAN, "销售备注"),
)

LEAD_FIELDS: tuple[str, ...] = tuple(f.name for f in FIELD_SPECS)
AI_EXTRACTION_FIELDS: tuple[str, ...] = (
    "language", "segment", "b2b_type", "b2c_intent", "country_stated", "city_region",
    "contact_name", "company", "role", "product_interest", "volume",
    "existing_dealer_relationship", "ai_summary", "ai_confidence",
    "escalation_flag", "escalation_reason",
)

# Labeling template: schema-aligned columns + label-only helper columns.
LABEL_ONLY_COLUMNS: tuple[str, ...] = (
    "sample_id", "data_origin", "conversation_text", "country_gold",
    "is_valid_lead", "annotator", "label_notes",
)
LABEL_COLUMNS: tuple[str, ...] = (
    "sample_id", "data_origin", "phone", "conversation_text",
    "language", "segment", "b2b_type", "b2c_intent", "country_gold",
    "product_interest", "escalation_flag", "escalation_reason",
    "is_valid_lead", "annotator", "label_notes",
)

# Botmaker chat variables written by the flow / AI Agent use the same names as the schema.
BOTMAKER_VARIABLES: tuple[str, ...] = AI_EXTRACTION_FIELDS + ("consent_marketing", "source_code")
