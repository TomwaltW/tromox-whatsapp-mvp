# 需要 Botmaker 书面答复的问题

> 用途：把散在各文件里、只能由 Botmaker 销售或支持回答的问题合并成一份，附可直接发出的英文邮件稿；拿到答复后按"影响什么"一列回填。读者：集成工程师（发问、回填）；张宝文（决定以谁的名义发）。
> 假设：开工前发出（`07-project/timeline.md` 的开工日前）；邮件以客户名义还是我方名义发、是否写明客户名称【张宝文确认】；不在邮件里透露我方报价与工作量。平台事实引用 `SOURCES.md` 条目编号。

## 1. 问题清单

| # | 问题 | 为什么问（现状） | 答复影响什么 |
|---|---|---|---|
| Q1 | 10/1 起客服消息（服务消息）经 Botmaker 结算时，是否在 Meta 单价上加收服务费（通知类是 +20%）；是否计入套餐对话数 | 定价页仍是"窗口内免费"的旧口径，帮助中心只说国别价格找客户经理（S-B13） | 成本模型 `bsp_markup_service`；报价单第三方费用 |
| Q2 | 超量单价以哪个为准：定价页 Standard / Scale / Pro 每个额外对话 0.07 / 0.06 / 0.05 USD，还是 FAQ 的 0.025 USD；"对话"是否即服务条款里的 DAILY USER | 两页矛盾，成本模型暂按定价页（S-B3） | 套餐费与升档临界点（`03-whatsapp/cost-model.md` 第 4 节） |
| Q3 | Meta 每号码每月 1,000 条免费服务消息是否原样传递给客户 | Meta 已官宣（S-M3），Botmaker 怎么结算未见说明 | 成本模型 `free_service_msgs_per_month` |
| Q4 | Meta 要求 2026-09-30 前在 WABA 上绑定支付方式：经 Botmaker 接入的账户由 Botmaker 的信用额度结算，还是客户要自己绑 | 未绑定的，10/1 起超出免费额度的服务消息停投（S-M9） | Meta 接入清单；上线检查表 |
| Q5 | webhook 附加功能的单价、开通方式；单条回调失败的重试次数、间隔、超时、是否要求 2xx；熔断期间丢失的消息有无补发 | 帮助中心只写了额外计费、默认关闭和熔断规则（S-B5） | 报价单第三方费用；集成服务的幂等、告警与对账设计 |
| Q6 | Click-to-WhatsApp 广告进线时，回调里是否带 `whatsappReferral`（`sourceId`、`sourceURL`、`headline`、`body`）；写进哪个会话变量；有无 `ctwa_clid` | 字段表列了，JSON 示例里没有（S-B6、S-B12） | 来源追踪能否记录广告维度（`01-design/source-tracking.md`） |
| Q7 | 新开账号是 Botmaker 3.0 还是经典界面；AI Agent 能否指定模型；所用模型的确切名称、版本与每百万 token 单价 | 3.0 版文章写默认 "Open AI 5.4" 且暂不能换，经典界面可以换（S-B7、S-B8） | 路线 A"离线评测与生产同一模型"的前提；ADR 0006；成本模型 AI 单价 |
| Q8 | AI Agent 的对话数据是否用于训练或改进任何模型（Botmaker 自有或 OpenAI、Anthropic 等下游）；能否签 DPA、提供子处理方清单；Co-pilot 能否按账户关闭，关闭后是否不再用于训练 | 官网写 Co-pilot 用对话训练 ChatGPT；WhatsApp 条款禁止用业务数据训练模型（S-B17、S-M5） | ADR 0006 的一票否决项；`03-whatsapp/compliance.md` |
| Q9 | "WhatsApp→Central 转接"按线路关闭后是否一直保持关闭；新增线路是否默认开启；关闭有无其他副作用 | 10/1 起每条线路默认开启，开启时机器人不在 WhatsApp 上回复（S-B16） | 配置指南与上线检查表的复查频率 |
| Q10 | 能否与非拉美主体（中国大陆或欧盟，例如比利时）签约并开具发票；币种、税务处理；合同主体是哪家公司 | 服务条款主体为 BOTMAKER INC 或阿根廷、巴西关联公司，开票口径未见（S-B14） | 客户财务流程与签约主体 |
| Q11 | 从中国大陆访问后台与坐席界面有无已知问题 | 无法从公开资料判断（S-B15） | 销售能否在 Botmaker 里接手 |
| Q12 | 变量 ID 是否允许下划线、是否区分大小写、长度上限 | 帮助中心只写了不许空格、连字符、星号（S-B18） | 全仓字段名（`shared/tromox_lead/`） |
| Q13 | Code Action 的调用频率与并发上限；`trigger-intent` 发模板的限流 | 公开资料未写（S-B10、`05-integration/botmaker-api-notes.md` 第 8 节） | 路线 B 可行性；再触达 |
| Q14 | API Token 能否限权、能否设较短有效期 | 公开资料未写（`05-integration/botmaker-api-notes.md` 第 8 节） | 密钥管理 |
| Q15 | 客户若用中国大陆 +86 号码走 Coexistence，Botmaker 侧是否支持 | Meta 已取消国家限制，但 +86 从未被点名（S-M7） | 号码策略（仅选方式 b 时） |

答复回填：Q1–Q3 改 `03-whatsapp/cost-model-inputs.csv` 后重跑 `cost_model.py`，再同步报价单；Q5、Q6 回填 `05-integration/botmaker-api-notes.md` 与 `01-design/source-tracking.md`；Q7、Q8 回填 ADR 0006；其余回填 `SOURCES.md` 对应条目，并去掉已解决的【待核实】。

## 2. 邮件稿（英文，可直接发）

Subject: Pre-onboarding questions: WhatsApp AI reception project (billing after Oct 1, webhooks, AI data terms)

Hello,

We are preparing to onboard a client onto Botmaker for a WhatsApp AI reception and lead-routing setup (one WhatsApp line, AI Agent plus human hand-off to sales, webhooks to the client's own lead database). The client's customers are mainly in Europe and North America. Before we open the account, we would appreciate written answers to the questions below.

Billing

1. From October 1, 2026, Meta charges for service messages. When Botmaker invoices these, do you add a service fee on top of Meta's rate (as with the +20% on notifications)? Do service messages count toward the plan's conversations?
2. Your prices page lists a fee for extra conversations of USD 0.07 / 0.06 / 0.05 (Standard / Scale / Pro), while the FAQ mentions USD 0.025 per additional user. Which one applies today? Is a "conversation" the DAILY USER defined in your Terms of Service?
3. Meta's free tier of 1,000 service messages per business phone number per month: is it passed through to the client unchanged?
4. Meta requires a payment method on file by September 30, 2026. For WhatsApp Business Accounts onboarded through Botmaker, is Meta billed through Botmaker, or does the client need to add its own payment method?
5. What is the price of the webhook add-on, and how is it activated?

Webhooks and data

6. When a single webhook delivery fails, how many times is it retried, at what interval, and what timeout do you apply? Is any 2xx response treated as success? Are messages dropped during the 10-minute pause after repeated failures ever re-sent?
7. For Click-to-WhatsApp ad conversations, does the webhook include `whatsappReferral` (`sourceId`, `sourceURL`, `headline`, `body`)? Is the referral also stored in a session variable, and if so, which one? Is `ctwa_clid` available?

AI and data protection

8. Will a new account be on Botmaker 3.0 or on the classic interface? Can we choose the generative model per AI Agent, and what is the exact model name, version and price per 1,000,000 tokens?
9. Are conversations handled by the AI Agent used to train or improve any model, either Botmaker's own or a provider's (for example OpenAI)? Can you sign a data processing agreement and share your list of sub-processors?
10. Your website says Co-pilot uses agent-user interactions as training data. WhatsApp's Business Solution Terms do not allow business data to be used for training AI models. Can Co-pilot be disabled for the account, and does that stop any use of our data for training?

Configuration and account

11. Once the WhatsApp-to-Central handoff is unchecked on a line, does it stay off? Are newly added lines turned on by default?
12. Can Botmaker contract with and invoice a company outside Latin America (mainland China or the EU)? Which Botmaker entity would sign, in which currency, and with what tax treatment?
13. Are there known access issues to the Botmaker console and the agent inbox from mainland China?
14. Are underscores allowed in variable IDs? Are variable IDs case-sensitive, and is there a length limit?
15. Are there rate or concurrency limits for Code Actions, and for sending templates through `trigger-intent`?
16. Can API tokens be limited in scope or given a shorter lifetime?
17. If the client connects an existing WhatsApp Business app number with a +86 (China) country code through Coexistence, is that supported?

Thank you. A reply by email is fine; links to documentation are welcome where they exist.

Best regards,
【发件人姓名与公司，张宝文确认】
