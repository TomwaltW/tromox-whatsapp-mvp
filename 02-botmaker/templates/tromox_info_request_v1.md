# 模板：tromox_info_request_v1（补充资料）

> 用途：B 端客户的资料没有收齐而 24 小时窗口已关闭时，请客户回复补充信息。读者：集成工程师（提交审核）、销售与运营（使用）。
> 假设：类别 utility；是否被 Meta 改判为 marketing【待核实】；译文与语种【待客户确认】。

## 1. 基本信息

| 项 | 值 |
|---|---|
| 模板名 | `tromox_info_request_v1` |
| 类别 | utility |
| 语种 | en（主稿）；es、de、fr、pt 占位 |
| 页眉 | 无 |
| 页脚 | Tromox |
| 档位 | 精简版、完整版 |

## 2. 正文（英文主稿）

```text
Hello {{1}}, thank you for contacting Tromox on {{2}}. To complete your dealership request we still need the following information: {{3}}. Please reply to this message and our team will continue from there.
```

## 3. 其他语种（占位）

| 语种 | 正文 | 状态 |
|---|---|---|
| es | {ES 译文待定} | 【待客户确认】 |
| de | {DE 译文待定} | 【待客户确认】 |
| fr | {FR 译文待定} | 【待客户确认】 |
| pt | {PT 译文待定} | 【待客户确认】 |

## 4. 变量与示例值

| 变量 | 含义 | 取值来源 | 提交审核用的示例值 |
|---|---|---|---|
| `{{1}}` | 客户称呼 | 线索字段 `contact_name`；为空时用通用称呼 | Mariana |
| `{{2}}` | 客户发起咨询的日期 | 线索字段 `first_message_ts` | 28 October 2026 |
| `{{3}}` | 还缺的信息，用一句自然语言写 | 对照 B 端必填项：业务类型、公司或联系人、国家或市场 | your company name and the country where you operate |

`{{3}}` 只写缺什么，不写任何报价、政策或承诺；变量值里不要换行，长度控制在一句话内。

## 5. 按钮（快捷回复）

| 按钮标题（EN） | 作用 |
|---|---|
| I'll reply now | 客户一点即回复，窗口重新打开 |
| No longer needed | 客户体面退出；收到后停止再触达 |

## 6. 使用说明

1. 适用于 AI 追问两次后仍缺必填项、客户当时没再回复的 B 端会话。
2. 客户补充后，AI 或销售把字段补全，线索状态按正常流程推进。
3. 同一咨询最多发 2 次，间隔不少于 3 天【待客户确认】。

## 7. 版本记录

| 版本 | 日期 | 变更 | 审核状态 |
|---|---|---|---|
| v1 | 2026-09-21 | 初稿，未提交 | 待提交 |
