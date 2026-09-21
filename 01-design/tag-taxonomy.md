# 标签体系

> 用途：定义 Botmaker 会话标签与线索库 `tags` 字段的维度、取值与命名规范，是标签字符串的唯一源头（机器实现：`shared/tromox_lead/tags.py`）。读者：集成工程师、客户运营。
> 假设：Botmaker 标签名可使用小写字母、数字与下划线【待核实】；若不支持下划线，统一去掉下划线改驼峰，映射关系不变。

## 1. 命名规范

1. 格式：`<维度>_<取值>`，全小写 ASCII，只用字母、数字、下划线；例：`country_de`、`seg_b2b`。
2. 一个维度一个前缀，禁止无前缀标签；运营新增标签前先在本文件登记。
3. 标签由规则从线索字段生成，不让 AI 自由发挥；AI 只负责产出字段（见 `lead-schema.md`）。
4. 标签只增不改名：改名会打断历史报表。确需调整，在第 4 节登记映射。

## 2. 维度与取值

| 维度 | 前缀 | 取值来源 | 示例 | 精简版 | 完整版 |
|---|---|---|---|---|---|
| 国家 | `country_` | 客户自述国家，没有则取号码国家码（ISO 3166-1 alpha-2 小写） | `country_de` | 上 | 上 |
| 客户类型 | `seg_` | `segment`：`b2b` / `b2c` / `unknown` | `seg_b2b` | 上 | 上 |
| B 端类型 | `b2b_` | `b2b_type`：`dealer` / `distributor` / `fleet` / `importer` / `other` | `b2b_distributor` | | 上 |
| 产品 | `prod_` | `product_interest` 中的产品代码小写；目录见 `shared/tromox_lead/products.py`【待客户确认】 | `prod_mc10` | | 上 |
| 意图 | `intent_` | `b2c_intent`：`buy` / `support` / `parts` / `warranty` / `test_ride` / `other` | `intent_test_ride` | | 上 |
| 阶段 | `stage_` | `status`：`new` / `qualified` / `handed_off` / `contacted` / `closed_won` / `closed_lost` / `nurture` / `invalid` | `stage_handed_off` | | 上 |
| 来源 | `src_` | `source_channel`：`instagram` / `facebook` / `tiktok` / `youtube` / `website` / `ctwa_ad` / `offline_qr` / `other` | `src_instagram` | | 上 |
| 语言 | `lang_` | `language`（ISO 639-1） | `lang_es` | | 上 |
| 优先级 | `prio_` | 规则：B 端且类型为 distributor / importer / fleet 为 `high`，其余 B 端为 `normal`；C 端仅在投诉、质保争议、法律、安全类升级时为 `high`【待客户确认】 | `prio_high` | | 上 |

MVP 精简版只上前两个维度；完整版九个维度全上。来源短码本身（如 `IG-2609`）存字段 `source_code`，不做成标签，避免标签数量随帖子无限增长。

## 3. 标签在哪里用

| 位置 | 用法 |
|---|---|
| Botmaker 会话标签 | 运营在后台按标签筛会话、看分布；由流程或 Code Action 写入 |
| 线索库 `tags` 字段 | 集成服务按本文件规则生成，用于导出与报表 |
| 销售群通知卡片 | 展示国家、类型、优先级三个标签 |
| 第二阶段 | CRM 对接时映射为 CRM 的字段或标签（见 `07-project/phase-2-outline.md`） |

## 4. 变更登记

| 日期 | 变更 | 旧值 | 新值 | 登记人 |
|---|---|---|---|---|
| 2026-09-21 | 初版 | | | 集成工程师 |
