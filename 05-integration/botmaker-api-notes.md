# Botmaker API 与 Webhook 笔记

> 用途：记录本项目用到的 Botmaker API v2.0 端点、鉴权、限流、webhook 配置与回调结构、结束分类到线索状态的映射、常见错误处理。读者：集成工程师。
> 依据：公开的接口描述文件与帮助中心文章（SOURCES S-B2、S-B5、S-B6、S-B10、S-B11、S-B12、S-B18）。未登录、未调用任何真实接口；凡未在一手来源读到的内容均标【待核实】。

## 1. 先说结论

1. **MVP 的集成服务只"收"不"调"**：它接收 Botmaker 的 webhook 回调，不主动调用 Botmaker API。建工单、停 AI、打标签、发模板都在 Botmaker 的流程里或由销售在后台完成。这样少一把长期有效的 API 密钥，也少一类故障。
2. 下表中标"可选"的端点，是确有需要时的扩展点（例如把规则生成的标签回写到会话）。启用前先过一遍第 7 节的限流与错误处理，并单独写带 mock 的客户端模块，不要混进 webhook 处理路径。
3. 不要用 `GET /messages`、`GET /billing/whatsapp/billed-conversations` 做轮询：接口描述写明这两个端点"会增加 BI 数据源费用"。对话数据以 webhook 推送为准。唯一的例外是回调缺口（第 7 节）：熔断期间的消息原文写明丢失、有无补发未写，单条失败是否重发也未写（SOURCES S-B5）【待核实】，按丢失处理，由人工用 API 对账一次，不做成定时轮询，集成服务本身仍不调用 API。

## 2. 鉴权与基础信息

| 项 | 内容 | 依据 |
|---|---|---|
| Base URL | `https://api.botmaker.com/v2.0` | SOURCES S-B2 |
| 鉴权 | 请求头 `access-token: <token>` | SOURCES S-B2 |
| Token 生成位置 | `https://go.botmaker.com/#/integrations/api` | SOURCES S-B2 |
| Token 有效期 | 接口描述中 `accessToken` 注明 "Expiration time: 5 years"；可用 `POST /auth/credentials`（clientId、secretId、refreshToken）换新，限 3 次/分钟 | 接口描述文件 |
| 另一种请求头 `bearer-token` | 仅供登录的坐席使用，"not usable by programs"，程序不要用 | 接口描述文件 |
| 归属 | Token 属于客户的 Botmaker 账号；我方只在客户授权期间保存，放部署环境的密钥配置，不进仓库 | 项目原则 |

Token 权限范围能否收窄（只读、限端点）：未见说明。【待核实】

## 3. 用到的端点

| 端点 | 用途 | MVP 是否调用 | 文档限流 |
|---|---|---|---|
| `GET /chats/{chatReference}` | 读会话状态：`variables`、`tags`、`queueId`、`agentId`、`whatsAppWindowCloseDatetime`、`lastUserMessageDatetime`、`isBotMuted`。只查最近 2 个月内有活动的会话 | 否（排障时手工用） | 3 次/秒 |
| `PATCH /chats/{chatReference}` | 回写会话变量与标签：`variables` 为对象，`tags` 为 `{"标签名": true/false}` | 可选（标签回写） | 3 次/秒 |
| `GET /chats/variables` | 拉取变量赋值记录，核对 AI Agent 是否把字段写进变量 | 否（试用期验证用） | 20 次/秒 |
| `POST /tickets` | 建工单：必填 `subject`、`contentMarkDown`、`customFields`；可选 `aiAgentId`。自定义字段定义用 `GET /tickets/field-definitions` 查 | 否（流程内建工单） | 60 次/分钟 |
| `GET /attention-queues` | 查服务队列 id、名称、并发数、可转接队列 | 否（配置核对用） | 5 次/分钟 |
| `POST /chats-actions/send-messages` | 向会话发消息（文本、按钮、`whatsappInteractive`），返回 202 表示已入队；只能在 24 小时客服窗口内发自由文本 | 否 | 350 次/秒 |
| `POST /chats-actions/trigger-intent` | 触发某个意图或**发送 WhatsApp 模板**（`intentIdOrName` 填模板名），可同时设置 `variables`、`tags` | 可选（二期的程序化再触达） | 未注明【待核实】 |
| `GET /whatsapp/templates`、`POST /whatsapp/templates` | 查询与创建模板；MVP 在后台界面提交模板即可 | 否 | 1 次/秒 |
| `GET /webhooks`、`GET /webhooks/{id}` | 只读：查看已配置的 webhook。接口**没有创建 webhook 的端点**，创建在后台界面完成 | 否 | 1 次/秒、5 次/秒 |
| `POST /webhooks/{id}/redirection-rules` | 重定向规则：把匹配 `chatsMatchProps` 的会话（例如测试账号）的回调转发到另一个 URL，用于联调与 UAT，不影响正式流量 | 可选（联调） | 5 次/秒 |
| `GET /messages` | 拉消息历史；**会增加 BI 数据源费用** | 否 | 5 次/秒 |
| `GET /billing/whatsapp/billed-conversations` | 按月列出计费会话，含 `origin`（user-initiated / business-initiated / referral-initiated）；**会增加 BI 数据源费用** | 否（月度对账时手工用） | 1 次/秒 |
| `GET /billing/consumptions` | 消耗汇总 | 否 | 1 次/月 |

`chatReference` 有两种写法（接口描述原文）：Botmaker 的 `chatId`；或 `channelId` + `:` + `contactId`（`channelId` 从 `GET /channels` 取，形如 `<项目>-whatsapp-<公司号码>`；`contactId` 对 WhatsApp 即客户号码）。webhook 回调里的 `customerId` 与 API 的 `chatId` 是同一个值：两边的 `sessionId` 都是"该 id + `_` + 会话创建时间"。【待核实】用真实样本确认。

## 4. Webhook 配置

| 项 | 内容 | 依据 |
|---|---|---|
| 配置位置 | Settings > Integrations > Botmaker API 中的 Webhooks 区域 | SOURCES S-B5 |
| 开通与计费 | webhook 是额外计费的功能，默认不开，要先在账户设置里开通；单价未公开【待核实】 | SOURCES S-B5 |
| 数量 | 同一渠道最多挂 1 个 webhook；联调不另建第二个，用重定向规则分流（见下方"联调"一行） | SOURCES S-B5 |
| 回调地址 | `https://<部署域名>/webhooks/botmaker`，必须是公网可达的 HTTPS | `deployment.md` |
| 鉴权 | 在 webhook 配置里填安全 Token；Botmaker 每次回调把它放在请求头 `auth-bm-token`。服务端对应环境变量 `BOTMAKER_WEBHOOK_TOKEN` | SOURCES S-B5 |
| 勾选项 | 渠道选 WhatsApp；消息类型勾选用户消息、Bot 消息、坐席消息、事件消息；打开"包含变量"。消息状态可不勾（服务只落盘不处理，勾了只是多流量） | SOURCES S-B5 |
| 出口 IP | Botmaker 的对外请求来自一份公开的固定 IP 清单，可填进 `ALLOWED_IPS` 作为第二道防线；清单会变，以帮助中心为准 | SOURCES S-B11 |
| 联调 | 用重定向规则把测试账号的回调指到预发地址，正式流量不受影响 | 第 3 节 |
| 后台监控 | webhook 页面有错误日志，以及成功 / 慢 / 错误 / 被拒计数、近 30 分钟最快 / 平均 / 最慢响应时间；用来确认是否触发过熔断、缺了哪一段 | SOURCES S-B5 |

回调失败时 Botmaker 怎么做，已知与未知分开写（SOURCES S-B5）：

- **已知：熔断。** 10 分钟内失败超过 100 次，接下来 10 分钟停发新消息，原文写明这段时间的消息丢失。丢的是回调，对话本身在 Botmaker 里照常进行。
- **未知：** 单条失败是否重试、重试间隔、超时阈值、是否要求 2xx 以外的特定响应、有无重放，原文均未写。【待核实】

服务侧的应对：原文先落盘再处理，通知在响应发出后异步发送、失败也不让 webhook 返回 5xx，尽快应答；处理幂等，同一回调重发直接返回 `duplicate`，因此无论对方重试与否都安全。熔断期间 Botmaker 根本不发，服务无从落盘，只能靠对账补（第 7 节）。

## 5. 回调结构（v1.1，【待核实】）

依据帮助中心示例（SOURCES S-B6），经摘要工具转述，字段以真实样本为准。服务端模型见 `webhook-service/app/models.py`，样例见 `webhook-service/fixtures/`。

| 类型 | 判别 | 服务用到的字段 | 处理 |
|---|---|---|---|
| 消息 | `type: "message"` | `contactId`（WhatsApp 即客户号码）、`whatsappNumber`、`customerId`、`sessionId`、`firstName`、`lastName`、`chatPlatform`、`variables{}`、`messages[]._id_ / date / from / fromName / message / operatorId` | 归一化并入库；`from` 为 `user` 的消息用于短码解析与时间戳；为 `agent` 的消息表示销售已回复 |
| 事件 | `type: "event"` | `events[].name`、`events[].info[].name / value` | `conversation-close` 读取 `typification` 回写状态；分配类事件置 `handed_off` |
| 状态 | 顶层 `status` | `messageId`、`status`、`error[]` | 只落盘，不改线索；`error` 非空时记警告 |

几点已在实现里兜住的不确定性：

1. **变量名写法**：流程里的会话变量与线索字段同名（下划线）。帮助中心写明变量 ID 不能含空格、连字符、星号等特殊字符，是否允许下划线没写（SOURCES S-B18）【待核实】。若平台不接受下划线，改用驼峰（`b2bType`、`productInterest`），服务两种都认、代码不用改；但流程、AI Agent 指令、配置指南里的变量名都要跟着改，标签是 TAG 类型的变量，`country_de` 这类标签名也在内，会牵动全仓的字段名写法。自定义变量还要避开预定义变量名，以及 Google Ads 集成自动写入的 `sourceId`、`gclid`。服务另接受一个可选的整体 JSON 变量 `lead_json`，单个变量优先于它。
2. **变量随哪类回调下发**：示例里 `variables` 出现在消息回调中。服务对每一条消息回调都重新评估是否需要通知，不依赖"变量一定跟着用户消息来"。【待核实】
3. **按钮点击的形态**：接口描述里消息内容类型有 `button-click` 与 `selectedButton`，回调示例里没有。流程应在按钮动作里直接给变量赋值（如 `segment=B2B`），服务只认变量，不解析按钮文本。【待核实】
4. **变量跨会话保留**：Botmaker 的会话变量按联系人保存。流程须在新会话开场（S1_GREETING）把 `escalation_flag`、`escalation_reason` 重置，否则老客户再次来访时，第一条消息就会带着上次的升级标记触发一次通知。【待核实】
5. **CTWA referral**：帮助中心回调字段表列有 `messages[].whatsappReferral`，子键 `sourceId`、`sourceURL`、`headline`、`body`；同文 JSON 示例里没有这个对象。字段表里没有来源类型与点击 id，`ctwa_clid` 在帮助中心与 API 描述文件中都未出现（SOURCES S-B6、S-B12）。服务现有代码只在顶层或消息内寻找名为 `referral` 的对象（`sourceType / sourceId / sourceUrl / headline / body / ctwaClid`，大小写与下划线不敏感），找到就记入线索并把来源渠道置为 `ctwa_ad`；**对象名不同，照字段表的写法到达时服务读不到**（子键能对上，对象名对不上）。本轮不改代码：拿到真实样本、核对对象名与层级后，再决定是否把 `whatsappReferral` 加进查找。【待核实】
6. **只有 WhatsApp 的 `contactId` 是号码**：其他渠道（Instagram、Messenger）的回调 MVP 直接跳过（结果为 `skipped_no_contact`）；二期接私信渠道时沿用"平台客户 ID"去重键即可。WhatsApp 渠道里 `contactId` 不是号码的客户（只给出业务范围用户标识【待核实】）不跳过：按 `bm:<customerId>` 去重入库并照常通知，`phone` 留空。

## 6. 结束分类（typification）到线索状态

销售在 Botmaker 结束会话时选择结束分类，`conversation-close` 事件把它带回来，服务据此回写 `status`。分类名称需要在 Botmaker 后台的结束分类功能中预先建好【待核实】，名称与含义由客户销售确认【待客户确认】。

| 结束分类（建议名） | 含义 | 线索状态 |
|---|---|---|
| `qualified_followup` | 有效线索，已首次沟通，继续跟进 | `contacted` |
| `won` | 成交或签约 | `closed_won` |
| `lost` | 明确无意向 | `closed_lost` |
| `nurture` | 暂不成熟，后续培育 | `nurture` |
| `not_a_lead` | 垃圾、无关或误入 | `invalid` |

匹配时忽略大小写，空格与连字符视同下划线（`Not a lead` 等同 `not_a_lead`）。不在表内的分类不改状态，只记一条警告日志（字段 `typification`），据此补映射：改 `webhook-service/app/normalize.py` 的 `TYPIFICATION_TO_STATUS`。

除结束分类外的两条系统规则：B 端字段收集完成时 `new → qualified`；回调里出现坐席消息时转 `contacted` 并记录 `assigned_to`。系统规则只向前推进，不会把销售回写的终态改回去。

## 7. 常见错误与处理

| 情形 | 表现 | 处理 |
|---|---|---|
| Token 无效或过期 | 401 或 403【待核实】具体状态码 | 到 Token 生成页重新生成，或用刷新接口；更新部署环境的密钥配置 |
| 权限不足 | 403 "Missing permissions ..." | 让客户所有者给我方账号相应角色 |
| 超过限流 | 429，说明里带该端点的上限 | 指数退避加抖动，单端点串行化；批量回写按 3 次/秒节流；不要并发扫全量 |
| 会话找不到 | 404；`GET /chats/{chatReference}` 只查近 2 个月活跃会话 | 改用会话搜索端点，或确认 `chatReference` 写法 |
| 请求体问题 | 400 "Chat reference or message body problem." | 核对 `chat` 引用二选一写法；WhatsApp 按钮标题不超过 20 字符、最多 3 个 |
| 窗口已关闭仍发自由文本 | 发送失败，状态回调 `error[]` 非空 | 只能用已审核模板（`trigger-intent` 或后台手动）再触达 |
| 发送是异步的 | `send-messages`、`trigger-intent` 返回 202，不代表送达 | 以状态回调为准；需要对账时在请求里带 `webhookPayload` 自定义标识 |
| 我方回调服务不可用 | 10 分钟内失败超过 100 次触发熔断，接下来 10 分钟停发，这段时间的消息丢失（SOURCES S-B5）；单条失败是否重试未知【待核实】 | 健康检查加告警，尽快恢复；恢复后用 `python -m app.replay` 重放已落盘未处理的事件。它只能重放落了盘的，熔断期间以及单条失败后没重发的回调补不回：先看 Botmaker 后台 webhook 错误日志确定缺口时段，再手工对账补齐，例如用 API 的 sessions 资源（`GET /sessions`，SOURCES S-B2）；该端点的参数、限流、是否像 `GET /messages` 一样增加 BI 数据源费用【待核实】 |

## 8. 待核实清单

| # | 事项 | 怎么验证 | 负责人 |
|---|---|---|---|
| 1 | 真实回调的字段与层级 | 试用账号接预发地址，`KEEP_RAW_PAYLOADS=true` 采样，替换 fixtures | 集成工程师 |
| 2 | 回调单条失败的重试、间隔与超时策略（熔断规则已证实，SOURCES S-B5） | 预发地址故意返回 500 观察，只用重定向规则引过去的测试会话；重定向的失败是否计入同一渠道的熔断计数未知，失败次数要远低于 10 分钟 100 次；同时书面问 Botmaker 支持 | 集成工程师 |
| 3 | 变量名是否允许下划线（已知不能含空格、连字符、星号，SOURCES S-B18） | 试用账号建变量 `b2b_type` | 集成工程师 |
| 4 | 回调是否包含分配坐席类事件 | 试用账号做一次转人工并接手 | 集成工程师 |
| 5 | 结束分类的配置位置与事件里的取值 | 试用账号建 5 个分类并结束会话 | 集成工程师 |
| 6 | CTWA referral：字段表已列 `messages[].whatsappReferral`（SOURCES S-B12），待真实样本核对对象名、层级、是否含点击 id；服务目前只认 `referral` | 需要真实广告流量；无广告前保持【待核实】 | 集成工程师、客户运营 |
| 7 | 会话链接地址格式（接口描述中出现 `#/chats`、`#/chat/{chatId}`、`#/{chatId}` 三种写法） | 后台打开任一会话看地址栏，更新 `BOTMAKER_CHAT_URL_TEMPLATE` | 集成工程师 |
| 8 | API Token 能否限权、能否设更短有效期 | 后台 Token 页面 | 集成工程师 |
| 9 | `trigger-intent` 发模板的限流 | 接口描述未注明，问 Botmaker 支持 | 集成工程师 |
| 10 | webhook 功能的单价与开通方式（额外计费、默认关闭，SOURCES S-B5） | 书面问 Botmaker；试用账号看账户设置 | 集成工程师 |
| 11 | 熔断后对账用哪个端点（如 `GET /sessions`）、是否增加 BI 数据源费用 | 接口描述文件逐端点核对；书面问 Botmaker 支持 | 集成工程师 |
