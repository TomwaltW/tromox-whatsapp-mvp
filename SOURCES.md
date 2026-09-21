# 事实核实记录（SOURCES）

> 用途：记录平台、政策、价格类事实的核实结论与出处，是全仓库此类事实的唯一源头；其他文档引用本文件的条目编号，不重复贴链接。读者：集成工程师、张宝文。
> 核实日期：2026-09-21。核实方式：公开网页与公开 API 描述文件（未登录、未创建任何账号、未调用任何真实 API）。
> 结论标记：**已复核**＝在一手来源读到原文；**部分复核**＝仅第三方来源一致；**未能复核**＝未找到可靠来源，沿用原数字并标【待核实】；**有更新**＝与开工前掌握的信息不同。

## 0. 影响设计的五条结论

| # | 结论 | 影响 |
|---|---|---|
| 1 | Botmaker **官方支持 Coexistence**（同一号码 App 与平台并存），帮助中心有专门文章（S-B4）。 | 号码策略 b 路线成立，不必为共存换平台；备选 BSP 表仅作兜底。见 `01-design/adr/0002-number-strategy.md`。 |
| 2 | Meta 官方文档确认 2026-10-01 起客服窗口内的自由回复按条计费，第三方 AI 回复同样计费，单价与各市场 utility 费率相同（S-M1）。 | 成本模型按新规则算；话术设计以"一条说清、多用按钮"为硬约束。 |
| 3 | "每号码每月前 1,000 条免费"**只在 BSP 文章里出现**（360dialog、SendPulse），在抓取到的 Meta 官方页面上没有读到（S-M1、S-M3）。 | 成本模型把免费额度做成参数，同时给出 0 条的保守情景。【待核实】 |
| 4 | Botmaker 的生成式 AI **按 token 另行计费**，单价未公开；默认模型在帮助中心写作 "GPT-4 Mini"，可按 Bot 或按 Agent 切换（S-B7、S-B8）。 | 路线 A 不是"零模型成本"；成本模型给区间并标【待核实】。 |
| 5 | Botmaker webhook 的鉴权头是 `auth-bm-token`，帮助中心给出了 v1.1 消息回调示例（S-B5、S-B6）；公开 API 描述文件给出了逐端点限流（S-B2）。 | 集成服务的 fixture 按该示例建模；真实样本到手前字段仍标【待核实】。 |

## 1. Botmaker（对应任务书 3.1）

| 编号 | 事实 | 结论 | 出处 |
|---|---|---|---|
| S-B1 | Meta 官方 WhatsApp BSP（页面页脚 "WhatsApp BSP — Meta Official"）。渠道含 WhatsApp、Instagram、Facebook Messenger、Telegram、Webchat 等；有服务队列（Service queues）与人工升级。 | 已复核 | https://botmaker.com/en/platform/chatbots-platform/ |
| S-B2 | API v2.0：Base URL `https://api.botmaker.com/v2.0`；鉴权为请求头 `access-token`（在 `https://go.botmaker.com/#/integrations/api` 生成）；资源含 chats、chats-actions、messages、channels、agents、roles、billing、whatsapp accounts / templates、intents、contacts、webhooks、bot config（variables / constants / typifications）、knowledge-bases、attention-queues、tickets、notifications、entities、dashboards、sessions。限流写在各端点 429 说明里，例如 `GET /chats` 3 次/秒、`PATCH /chats/{chatReference}` 3 次/秒、`POST /chats-actions/send-messages` 350 次/秒、`/tickets` 60 次/分钟、`GET /attention-queues` 5 次/分钟。 | 已复核 | https://api.botmaker.com/v2.0/ （描述文件 https://api.botmaker.com/v2.0/openapi.json ） |
| S-B3 | 套餐（USD/月）：Standard 149（3,000 个对话、10 个坐席）；Scale 249（5,000 个对话、20 个坐席）；Pro 499（10,000 个对话、50 个坐席）；Enterprise 面议。"Up to 300 free initial conversations"。通知类消息 "transparent cost of WhatsApp + 20% service fee"。开通 WhatsApp 商业平台账户一次性 99 USD。超出套餐 "$0.025 USD per additional user"。开 Botmaker 账号本身免费；支付方式为信用卡/借记卡。 | 已复核；Scale/Pro 的额度与超量单价为**有更新** | https://botmaker.com/prices ； https://botmaker.com/en/faqs |
| S-B4 | **Coexistence 支持**：在 Settings > Channels > WhatsApp 中 "Add WhatsApp account"，勾选 "Connect with a WhatsApp Business app"，输入现用号码，手机扫码授权，可同步近 6 个月联系人与聊天；之后需**至少每 14 天打开一次** WhatsApp Business App，否则连接自动断开；模板只能从 Botmaker 发；平台不支持群聊；语音/视频通话仅限手机端；接入时要填账户名与时区。文章未提及计费。 | 已复核，**有更新**（原先为"公开资料未找到"） | https://help.botmaker.com/en/help/6812922591331465063 |
| S-B5 | Webhook 在 Settings > Integrations > Botmaker API 中配置：回调 URL、可选安全 Token（随每次回调放在请求头 `auth-bm-token`）、渠道选择、消息类型勾选（Bot / 用户 / 坐席消息、消息状态、仅 HSM 状态、事件消息）、"包含变量"开关。重试与超时策略文章未写。【待核实】 | 已复核（配置与鉴权）；重试策略未能复核 | https://help.botmaker.com/en/help/3502316744427746581 ；API 描述文件中 `WebhookFullResponse.token` 的说明 |
| S-B6 | Webhook 回调示例（v1.1 消息）：顶层 `v`、`type`（message / event）、`chatPlatform`、`contactId`、`customerId`、`sessionId`、`whatsappNumber`、`firstName`、`lastName`、`chatChannelId`、`customerCreationTime`、`sessionCreationTime`、`variables`；`messages[]` 内 `_id_`、`date`、`from`（bot / user / agent）、`fromName`、`message`、`operatorId`、`clientPayload`。事件回调为 `type: "event"` + `events[].name`（如 `conversation-close`）+ `events[].info[]`（如 `typification`、`agentName`）。状态回调含 `status`、`messageId`、`error[]`。示例经摘要工具转述，字段以真实回调样本为准。【待核实】 | 部分复核 | https://help.botmaker.com/es/help/5976723636536441591 |
| S-B7 | 生成式 AI 计费：按 token 计，"fixed price per block of 1,000,000 tokens"，单价随模型不同，文章未给数字；每次回复约带最近 20 条消息、指令、知识库命中段落；消耗明细在 Settings > Account > "Products and consumption"。建 Agent、编排本身不收费。【待核实】单价 | 已复核（计费方式），单价未能复核，**有更新** | https://help.botmaker.com/en/help/6076338799961441365 |
| S-B8 | 模型选择：Bot Designer 左侧工具栏 "Generative model"；AI Agent 配置最后一步可 "Use a different model"；未指定时默认 "GPT-4 Mini"（原文如此）；可选模型清单未公开。 | 已复核 | https://help.botmaker.com/en/help/4974240524357382433 |
| S-B9 | AI Agent 可按指令把用户信息写入变量，官方示例写法为 "store it in ${fullName}"。是否支持结构化（JSON）输出：文章未提。【待核实】需在试用账号验证（见 `02-botmaker/trial-test-plan.md`）。 | 部分复核 | https://help.botmaker.com/en/help/4549050893086913048 |
| S-B10 | Code Actions：运行时 Node.js v22；外部 HTTP 用内置 `rp`（request-promise）；单次执行超时 90 秒；单次最多 200 个用户变量、每个变量值最大 100 KB；用 `user.set / user.get` 读写变量，`result.text / result.gotoRule / result.done` 返回；在 Bot Designer 的 "More > Action > Code Actions" 里挂到流程上。调用频率上限未写。【待核实】 | 已复核（西语文章） | https://help.botmaker.com/es/help/8528871986058021382 |
| S-B11 | Botmaker 对外请求（webhook、Code Action）来自一份固定 IP 清单，可用于回调服务白名单。 | 已复核 | https://help.botmaker.com/en/help/2547162551316035755 |
| S-B12 | CTWA：Botmaker 有 "Click to WhatsApp Dashboards" 功能，会识别来源为广告 referral 的会话；Google Ads 集成文章提到变量 `sourceId` "与 Meta Ads 的 Referral source ID 同理"。referral 明细（source_url、headline 等）是否进入 webhook 回调：未找到说明。【待核实】 | 部分复核（仅搜索摘要，未打开原文） | Botmaker 帮助中心 "What is the Click to WhatsApp Dashboards functionality?" |
| S-B13 | 10/1 之后 Botmaker 如何向客户结算客服消息（是否加 20%、是否计入套餐对话数）：FAQ 仍写"24 小时窗口内消息免费"，属旧口径。【待核实】需向 Botmaker 销售书面确认。 | 未能复核 | https://botmaker.com/en/faqs |
| S-B14 | 官网与帮助中心为英/西/葡三语；后台界面语言、发票与合同主体：未找到公开说明。【待核实】 | 未能复核 | 同上 |
| S-B15 | 从中国大陆访问 Botmaker 后台与 API 的稳定性：无法从本机验证。其对外 IP 属 Google Cloud 网段（推断），大陆直连大概率不稳定，需客户现有的合规跨境网络。【待核实】 | 未能复核（推断） | S-B11 |

## 2. Meta / WhatsApp Business Platform（对应任务书 3.2）

| 编号 | 事实 | 结论 | 出处 |
|---|---|---|---|
| S-M1 | 计费变化原文："Effective October 1, 2026, Meta will charge for service messages"；同日起客服窗口内回复用户的 utility 消息也收费；"By market, rates for service messages are the same as the rates for utility and authentication messages"；服务消息 "can be powered by a person ... or by a 3rd-party AI solution"；巴西示例 0.68 美分/条；72 小时免费入口窗口内的消息继续免费。另：Meta 自家的 Business Agent 自 2026-08-01 起按 2.00 USD / 百万 token 计费（本项目不使用）。 | 已复核 | https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/non-template-messages |
| S-M2 | 现行规则（10/1 之前）：只对送达的模板消息按条收费，按模板类别与收件人国家码定价；窗口内非模板消息免费；由 Click-to-WhatsApp 广告或 Facebook 主页按钮进入的会话开 72 小时免费窗口；utility / authentication 有月度阶梯价；费率卡在 WhatsApp Business 官网定价页。 | 已复核 | https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing |
| S-M3 | "每个号码每月前 1,000 条服务消息免费、按月重置不累计"：360dialog 称出自 Meta 定价文档 2026-08-05 更新；SendPulse 写 "Meta confirmed"；但 S-M1、S-M2 两个官方页面以及 Zendesk、Courier 的公告中均未读到。【待核实】 | 部分复核 | https://360dialog.com/blog/whatsapp-service-message-charging-october-2026/ ； https://sendpulse.com/blog/whatsapp-service-message-pricing |
| S-M4 | 费率示例（Meta 基础价，USD/条，不含 BSP 加价）：德国 0.0550、荷兰 0.0500、巴西 0.0068、美国/加拿大 0.0034、印度 0.0014、哥伦比亚 0.0008。德国与巴西两个数字与开工前掌握的一致。法、意、西、英等其余市场**未取得官方数字**，成本模型中相应行标【待核实】。 | 部分复核（巴西为官方原文，其余为 BSP 文章） | S-M1； https://360dialog.com/blog/whatsapp-service-message-charging-october-2026/ ； https://www.courier.com/blog/whatsapp-pricing-changes-october-2026 |
| S-M5 | 限定用途 AI 政策，官方条款原文（WhatsApp Business Solution Terms，"AI Providers" 条款）：AI 提供方不得把通用 AI 助手作为"主要功能"经由 WhatsApp Business Solution 提供；企业可以把 AI 提供方作为第三方服务商使用；**不得让 Business Solution Data 被用于训练或改进任何 AI 模型**（仅限为自己专用而微调的除外）；条款另对欧洲经济区与巴西号码的用户留有例外。生效节点：新接入用户 2025-10-15，全部用户 2026-01-15（第三方来源一致）。客服、销售、线索筛选类机器人明确允许。 | 已复核（条款原文）；日期为部分复核 | https://www.whatsapp.com/legal/business-solution-terms ； https://respond.io/blog/whatsapp-general-purpose-chatbots-ban |
| S-M6 | Coexistence 官方要求：WhatsApp Business App 版本 2.24.17 及以上；同步接入前 180 天内的消息；并存号码吞吐固定 20 条/秒；"Messages sent by the business via the WhatsApp Business app will continue to be free, but messages sent via Cloud API will be subject to Cloud API pricing"；接入后 1:1 聊天的阅后即焚、一次性查看、实时位置被关闭，广播列表停用；除 Windows 版与 WearOS 版外的伴侣设备均支持。 | 已复核 | https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users |
| S-M7 | Coexistence 的国家限制：多篇第三方文章称部分国家码的号码不支持（曾列出欧盟/欧洲经济区、英国、印度、日本、韩国、澳大利亚、菲律宾、俄罗斯、土耳其、南非、尼日利亚），但 S-M6 官方页面当前未见该清单。以客户实际号码的国家码在接入流程中的结果为准。【待核实】 | 未能复核 | 第三方文章（respond.io、YCloud 博客等），未采信 |
| S-M8 | 账号类通用规则（号码注册在客户自己的商务账户下、接入时收验证码、商家认证、显示名审核、发送量分级与质量评级）：属平台长期规则，本次未逐条重新核对原文；分级的具体数值与"未认证可否先承接入站会话"标【待核实】，见 `03-whatsapp/meta-onboarding-checklist.md`。 | 未逐条复核 | Meta 官方 Business Verification 与 Messaging Limits 文档 |

## 3. 任务书 3.3 的八个问题

| # | 问题 | 结论 | 依据 |
|---|---|---|---|
| 1 | Botmaker 是否支持 Coexistence；不支持时的替代 | **支持**（已复核）。兜底备选各列一家：YCloud、阿里云 Chat App Message Service，两家官网均有 Coexistence 说明页；对比见 `01-design/adr/0001-platform-choice.md`。 | S-B4； https://www.ycloud.com/whatsapp-business-app-coexistence ；阿里云国际站帮助中心 "WhatsApp Business App coexistence best practices" |
| 2 | AI Agent 能否把抽取字段稳定写入变量；是否支持 JSON 输出 | 能按指令写变量（已复核）；稳定性与 JSON 输出**未能复核**，由试用账号 20 条样例决定路线 A/B。【待核实】 | S-B9 |
| 3 | Webhook 事件类型与 payload；CTWA referral 是否透传 | 事件类型与 v1.1 示例已取得（部分复核）；referral 透传**未能复核**。【待核实】 | S-B5、S-B6、S-B12 |
| 4 | Code Actions 能否调外部 HTTP、超时与频率 | 能；超时 90 秒（已复核）；频率上限未能复核。【待核实】 | S-B10 |
| 5 | Botmaker 侧 10/1 后客服消息的结算方式 | **未能复核**。【待核实】 | S-B13 |
| 6 | 界面语言、时区、发票/合同主体 | 时区在接入号码时设置（已复核）；界面语言与发票主体未能复核。【待核实】 | S-B4、S-B14 |
| 7 | 中国大陆访问稳定性 | **未能复核**（推断需跨境网络）。【待核实】 | S-B15 |
| 8 | Tromox 公开信息 | 已查阅，见下节。 | 第 4 节 |

## 4. Tromox 公开信息（仅用于让示例更真实；不含参数、价格、质保）

| 项 | 内容 | 出处 |
|---|---|---|
| 品牌口号 | "Born for Cool Riding"；欧洲站 "Classic Soul. Electric Future." | https://eu.tromox.com/ |
| 车型名称（家族） | MC10（含 TrailX、StreetX）、UKKO（含 Ukko S+、UkkoPro）、M05、MINO（含 Mino B）、M03、Pesgo（含 Plus、C）。现售清单以客户提供为准【待客户确认】。 | https://www.tromox.com/en/faqs/ ； https://eu.tromox.com/ |
| 市场与网络 | 官网 FAQ 提到中国、意大利、欧洲、日本、韩国、澳大利亚、北美；另有美国站、南非站、菲律宾经销商站；欧洲站有 "Dealer Partnership Program" 与 "EU Warehouse Support"；总部杭州，欧洲服务中心在比利时鲁汶。各国经销商名单【待客户确认】。 | 同上；搜索结果中的 tromox.us、tromoxsa.com、evsupreme.net |
| 经销申请 | 官网设经销商/分销商申请表单；FAQ 写明希望申请方"已有至少 1 年的既有架构"、有二级网络更佳。有效线索标准以销售填写的为准【待客户确认】。 | https://www.tromox.com/en/faqs/ |
| 联系方式 | info@tromox.com（综合）、service@tromox.com（售后）、media@tromox.com（媒体）。 | 同上 |
| 社媒账号 | Facebook @tromoxofficial、Instagram @tromox_official、YouTube @TromoxOfficial。 | https://eu.tromox.com/ |

## 5. 未使用、未调用的说明

- 没有注册 Botmaker、Meta、YCloud、阿里云等任何账号；没有调用任何需要鉴权的接口。
- `https://api.botmaker.com/v2.0/openapi.json` 是公开的接口描述文件，读取它不属于调用 API。
- 仓库内所有代码均以 mock / fixture 跑通，见 `README.md`。
