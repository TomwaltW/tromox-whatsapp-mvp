# 模板：tromox_sales_followup_v1（销售跟进）

> 用途：B 端线索的 24 小时窗口已关闭，销售用这条模板请客户回复，以重新打开窗口继续沟通。读者：集成工程师（提交审核）、销售（使用）。
> 假设：类别 utility；是否被 Meta 改判为 marketing【待核实】；译文与语种【待客户确认】。

## 1. 基本信息

| 项 | 值 |
|---|---|
| 模板名 | `tromox_sales_followup_v1` |
| 类别 | utility |
| 语种 | en（主稿）；es、de、fr、pt 占位 |
| 页眉 | 无 |
| 页脚 | Tromox |
| 档位 | 精简版、完整版 |

## 2. 正文（英文主稿）

```text
Hello {{1}}, this is {{2}} from the Tromox sales team. I am following up on the dealership enquiry you sent us on {{3}}. Please reply to this message so that we can continue the conversation here.
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
| `{{1}}` | 客户称呼 | 线索字段 `contact_name`；为空时用当地语言的通用称呼（英文用 "there"） | Lars |
| `{{2}}` | 跟进销售的名字 | 发送人；不想露名字时用 "the team" | Chen Wei |
| `{{3}}` | 客户发起咨询的日期 | 线索字段 `first_message_ts`，按客户语言的习惯格式书写 | 4 November 2026 |

## 5. 按钮（快捷回复）

| 按钮标题（EN） | 作用 |
|---|---|
| Yes, let's continue | 客户一点即回复，窗口重新打开 |
| No longer needed | 客户体面退出；收到后停止再触达，线索状态记为 `closed_lost` |

## 6. 使用说明

1. 只在窗口已关闭时使用；窗口内直接自由回复。
2. 发送前确认这条线索确实由客户主动发起过咨询，且内容只针对那次咨询。
3. 客户回复后，销售在 Botmaker 坐席界面用公司号继续沟通；不要引导客户加个人 WhatsApp。
4. 同一咨询最多发 2 次，间隔不少于 3 天【待客户确认】。

## 7. 版本记录

| 版本 | 日期 | 变更 | 审核状态 |
|---|---|---|---|
| v1 | 2026-09-21 | 初稿，未提交 | 待提交 |
