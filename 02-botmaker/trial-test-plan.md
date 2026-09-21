# Botmaker 试用账号验证计划（20 条样例 + 平台验证项）

> 用途：开工第 1 周在试用账号里把所有【待核实】的平台行为测一遍，并用 20 条样例决定 AI 走路线 A 还是路线 B；结果是 `01-design/adr/0003-ai-route-a-b.md` 的决策依据。读者：集成工程师；结论抄送张宝文。
> 时间：2026-10-12 至 2026-10-16，决策门 2026-10-16（`07-project/timeline.md`）。
> 假设：试用账号由客户用企业邮箱开通（之后直接转正，资产不换手）；测试用一张**备用号码**，不拿客户正在用的业务号做试验；样例均为虚构内容；本计划写于开工前，执行时才会登录平台，仓库内的代码不调用任何真实接口。

## 1. 要回答的问题

| # | 问题 | 对应验证项 | 影响 |
|---|---|---|---|
| 1 | Coexistence 在 Botmaker 上实际怎么表现 | T-1 | 号码策略（`01-design/adr/0002-number-strategy.md`） |
| 2 | 内置 AI Agent 能否把字段稳定写入变量 | T-2（20 条样例） | 路线 A / B 决策门 |
| 3 | 平台是否支持固定 JSON 输出 | T-3 | 路线 A 的后续优化空间 |
| 4 | Webhook 真实回调长什么样、变量何时送达、失败是否重试 | T-4 | 集成服务的 fixture 与幂等设计 |
| 5 | Code Action 外呼是否可用、耗时与来源 IP | T-5 | 路线 B 可行性 |
| 6 | Click-to-WhatsApp 广告的 referral 是否透传 | T-6 | 来源追踪能否记录广告维度 |
| 7 | 2026-10-01 之后客服消息与 AI token 在账单里怎么体现 | T-7 | 成本模型的两个【待核实】输入 |
| 8 | 转人工全链路是否如设计 | T-8 | 人工接管第一版就上 |
| 9 | 变量名与标签名的字符限制、界面语言、大陆网络可达性 | T-9 | 配置细节与运维 |

## 2. 环境准备

| 项 | 要求 |
|---|---|
| Botmaker 账号 | 客户企业邮箱开通的免费账号（附最多 300 个初始对话，SOURCES S-B3）；集成工程师为管理员 |
| 测试号码 | 备用号码 1 个，走新号接入；另备 1 部装有 WhatsApp Business App（版本不低于 2.24.17）的手机与 1 个测试号，仅用于 T-1 |
| 测试手机 | 至少 2 部，号码国家码不同为佳，用于充当客户 |
| 配置 | 按 `setup-guide.md` 第 3、4 步搭最小流程：开场按钮、AI Agent（粘贴 `ai-agent-system-prompt.md` v1，路线 A 写法）、转人工节点；知识库放 3 至 5 条占位 FAQ |
| 模型 | 选定拟用于生产的模型并记录名称与版本（SOURCES S-B8） |
| 回调接收 | 集成服务的测试部署（`05-integration/deployment.md`），打开原始事件落盘；不使用第三方抓包网站，避免测试数据外流 |
| 记录 | 本文件第 5、6 节的表格；截图存项目网盘 |

## 3. 平台验证项

| 编号 | 验证内容 | 步骤要点 | 通过标准 | 结果回填到 |
|---|---|---|---|---|
| T-1 | Coexistence | 用测试 Business App 号按 `setup-guide.md` 2b 接入；从 App 回一条、从 Botmaker 回一条；观察人从 App 回复后机器人是否静默；记录所用号码的国家码与接入是否被拒 | 接入成功；两端消息互见；弄清机器人与人同时在线时的行为 | SOURCES S-B4、S-M7；ADR 0002 |
| T-2 | 字段写入变量（路线 A） | 跑第 4 节 20 条样例，逐条从会话详情或回调的 `variables` 读结果 | 见第 6 节决策门 | ADR 0003 |
| T-3 | 固定 JSON 输出 | 临时让 Agent 把整个字段块写进一个试验变量，20 条里抽 10 条看能否被 JSON 解析 | 仅记录，不设门槛 | SOURCES S-B9 |
| T-4 | Webhook 回调 | 分别触发：用户文本、按钮点击、Bot 消息、坐席消息、结束会话（带结束分类）、分配坐席；再让接收端先返回一次 500、再延迟 10 秒返回，观察是否重试与间隔 | 每类回调各存 1 份真实样本；弄清变量随哪类消息送达、有无重试 | `05-integration/webhook-service/fixtures/`；SOURCES S-B5、S-B6 |
| T-5 | Code Action 外呼 | 建一个只调集成服务 `GET /health` 的 Code Action；连续触发 20 次记录耗时；核对来源 IP 是否在公布清单内 | 外呼成功，单次耗时远低于 90 秒上限；来源 IP 可识别 | SOURCES S-B10、S-B11 |
| T-6 | CTWA referral 透传 | 客户有广告账户且同意时，投 1 条最小预算的 Click-to-WhatsApp 测试广告【待客户确认】；否则书面询问 Botmaker 支持。检查回调与变量里是否出现 source_id、source_url、headline 等 | 得到"透传 / 不透传 / 仅后台看板可见"三选一的明确结论 | SOURCES S-B12；`01-design/source-tracking.md` |
| T-7 | 计费可见性 | 2026-10-01 之后，在 Settings > Account > "Products and consumption" 看客服消息与 AI token 如何列示；记录 20 条样例前后的 token 增量；向 Botmaker 销售书面确认客服消息加价与"对话"的定义 | 拿到每条 AI 回复的实测 token 数；拿到书面答复 | `03-whatsapp/cost-model-inputs.csv`；SOURCES S-B7、S-B13 |
| T-8 | 转人工链路 | 触发一次 B 端交接：机器人静默、进入队列、工单建立、坐席用公司号回复、结束会话选分类、回调收到事件 | 全链路走通；销售群通知在 60 秒内到达（接好通知后） | `setup-guide.md` 第 10 节 |
| T-9 | 平台细节 | 变量名、标签名带下划线能否保存；后台界面语言；用客户办公室网络访问后台与 API 的稳定性 | 逐项有结论 | SOURCES S-B14、S-B15；`01-design/tag-taxonomy.md` |
| T-10 | 变量是否跨会话保留 | 走完一次 B 端交接并结束会话；同一测试号隔一段时间再发 `Hi`，看回调里的 `escalation_flag`、`escalation_reason` 是否还带着上次的值 | 弄清变量按联系人还是按会话保留；确认 S1 的变量复位生效，老客户再次来访不会重复通知销售 | `01-design/conversation-flow.md` S1；`setup-guide.md` 第 3 步 |
| T-11 | 回调里没有号码的联系人 | 查看 `contactId` 是否总是号码；若测试中出现业务范围用户标识（以用户名联系的客户），保存 1 份样本【待核实】 | 确认集成服务按平台客户 ID 入库并照常通知，号码与号码国家留空 | `05-integration/botmaker-api-notes.md`；`01-design/lead-schema.md` |

## 4. 20 条样例

说明：

- 公司名与人名均为虚构；"进入方式"为"按钮"的，先按对应按钮再发文本；"自由文本"的不按按钮直接发。
- 期望值按共享抽取规则（`shared/prompt_blocks/extraction-rules.md`）给出。"空"表示该变量必须保持为空：只说了城市时 `country_stated` 必须为空，这是重点检查项。
- 多轮样例以最后一条消息之后的变量状态为准；中间应出现的追问写在备注里。

| ID | 语种 | 进入方式 | 客户输入 | segment | b2b_type / b2c_intent | country_stated | product_interest | escalation_flag / reason | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| S-01 | EN | 按钮 Dealer/Distributor | We are Harbor Cycles Ltd, a motorcycle dealership in Manchester, UK. Interested in becoming a dealer for the MC10, about 8 units. I'm Tom Reed, sales director. | B2B | dealer | GB | MC10 | true / b2b_qualified | 公司、联系人、职位、城市、数量应一并写入 |
| S-02 | EN | 自由文本，两轮 | 第 1 条：Hello, I'd like to distribute Tromox across the Nordic countries, we have a network of 40 sub-dealers. 第 2 条：Company is Fjordline Mobility AS, Norway. I'm Ingrid, CEO. | B2B | distributor | NO | 空 | true / b2b_qualified | 第 1 条后应只追问一次且合并成一条；"Nordic countries" 不是国家，第 1 条后 `country_stated` 应为空 |
| S-03 | EN | 按钮 Rider or Customer，再按 Buy / Find a dealer | How much is the Ukko and where can I buy it in Austin? | B2C | buy | 空 | UKKO | false / 空 | 只说城市；知识库无零售价时应引导找当地经销商，不编价格 |
| S-04 | EN | 自由文本 | I want to talk to a real person please. | unknown | 空 | 空 | 空 | true / human_requested | |
| S-05 | EN | 自由文本 | My Mino's battery started smoking while charging last night! | B2C | support 或 warranty 均可 | 空 | MINO | true / complaint_warranty_legal_safety | 不得排查故障；应带安全提示句 |
| S-06 | EN | 按钮 Dealer/Distributor | We run a food delivery fleet in Dubai with 120 riders and are evaluating electric motorcycles. Could you send a quotation for 50 units of M05? | B2B | fleet | 空 | M05 | true / price_negotiation | 索要报价优先于字段收集；Dubai 记入城市 |
| S-07 | EN | 自由文本 | Hi, we import motorcycles into Chile and handle homologation ourselves. Interested in one container of MC10 and Pesgo. Company: Andes Motor Import SpA. Contact: Felipe Rojas. | B2B | importer | CL | MC10;PESGO | true / b2b_qualified | |
| S-08 | EN | 自由文本 | Can you write me a Python script to scrape websites? | unknown | 空 | 空 | 空 | false / 空 | 应只回固定拒答句；`ai_confidence` 应不低于 0.6（确信是无关消息），否则会被规则判成低置信度升级、白白打扰销售 |
| S-09 | DE | 按钮 Dealer/Distributor | Wir sind Zweirad Lindner GmbH in Leipzig, Deutschland, ein Händler für E-Roller. Interesse an MC10 und Mino, ca. 12 Stück pro Jahr. Ansprechpartner: Jonas Lindner, Geschäftsführer. | B2B | dealer | DE | MC10;MINO | true / b2b_qualified | 回复应为德语 |
| S-10 | DE | 按钮 Rider or Customer，再按 Test ride | Wo kann ich die Ukko in München Probe fahren? | B2C | test_ride | 空 | UKKO | false / 空 | 只说城市 |
| S-11 | DE | 自由文本 | Was kostet das M05 für Händler? Gibt es Mengenrabatt ab 20 Stück? | B2B | dealer 或 other 均可 | 空 | M05 | true / price_negotiation | 不得出现任何价格数字 |
| S-12 | ES | 按钮 Dealer/Distributor | Hola, somos Motos del Pacífico S.A. de C.V., distribuidores en México con 15 puntos de venta. Queremos la distribución de Tromox en México. Soy Mariana Torres, directora comercial. | B2B | distributor | MX | 空 | true / b2b_qualified | |
| S-13 | ES | 按钮 Rider or Customer | Necesito una batería de repuesto para mi Mino, ¿dónde la compro? | B2C | parts | 空 | MINO | false / 空 | |
| S-14 | ES | 自由文本 | Llevo dos semanas esperando una respuesta de garantía, quiero hablar con un responsable ya. | B2C | warranty | 空 | 空 | true / complaint_warranty_legal_safety | 投诉优先于"要求真人" |
| S-15 | FR | 按钮 Dealer/Distributor | Bonjour, nous sommes Rivage Location, société de location de scooters à Nice, en France. Nous souhaitons équiper notre flotte avec 30 Ukko. Je suis Claire Morel, gérante. | B2B | fleet | FR | UKKO | true / b2b_qualified | |
| S-16 | FR | 按钮 Rider or Customer，再按 Buy / Find a dealer | Bonjour, quel est le prix de la MC10 et est-elle disponible en Belgique ? | B2C | buy | BE | MC10 | false / 空 | 客户明说了国家市场 |
| S-17 | FR | 自由文本 | Si vous ne me remboursez pas sous 8 jours, je saisis mon avocat. | B2C | warranty 或 other 均可 | 空 | 空 | true / complaint_warranty_legal_safety | 法律威胁 |
| S-18 | PT | 自由文本，两轮 | 第 1 条：Olá, tenho uma loja de bicicletas elétricas no Porto e gostava de vender Tromox. 第 2 条：A loja chama-se Douro E-Bikes Lda, em Portugal. Sou o Rui Almeida. | B2B | dealer | PT | 空 | true / b2b_qualified | 第 1 条后 `country_stated` 应为空且不应升级；应只追问一次 |
| S-19 | PT | 按钮 Rider or Customer，再按 Support | A app não liga à minha M03, o que faço? | B2C | support | 空 | M03 | false / 空 | 知识库无答案时应明说并提出转人工；客户没有要求转人工就不升级 |
| S-20 | IT | 自由文本 | Ciao, vorrei informazioni su prezzi e disponibilità per 3 Mino. | B2B | 任意或空 | 空 | MINO | true / low_confidence | 数量大于 2 但无企业信息：按"漏掉经销商代价更高"判 B2B，且 `ai_confidence` 应低于 0.6 |

语种分布：EN 8、DE 3、ES 3、FR 3、PT 2、IT 1。最终语种清单【待客户确认】后，把不在范围内的语种样例换成范围内的。

## 5. 单条记录表

每条样例跑完填一行。

| 样例 ID | 执行日期 | 模型与 prompt 版本 | 7 个计分字段中写对的个数 | 写错或漏写的字段 | 文本字段（company、contact_name、volume 等）是否合理 | 回复语言正确 | 机器人发出的消息条数 | 备注 |
|---|---|---|---|---|---|---|---|---|
| S-01 | | | | | | | | |
| S-02 | | | | | | | | |
| …… | | | | | | | | |
| S-20 | | | | | | | | |

**7 个计分字段**（每条样例都按这 7 项计分，"应为空"也算一项，写了就算错）：

1. `language`
2. `segment`
3. `b2b_type` 或 `b2c_intent`（B 端看前者，C 端看后者，unknown 时两者都应为空；表中标"均可""任意"的，落在给定取值内即算对）
4. `country_stated`
5. `product_interest`
6. `escalation_flag`
7. `escalation_reason`

文本字段不计入门槛，但 B 端样例里 `company`、`contact_name` 漏写要在备注里单独记：它们决定销售拿到的线索好不好用。

## 6. 决策门

| 项 | 取值 | 来源 |
|---|---|---|
| 样例数 | 20 条 | `06-acceptance/thresholds.json` 的 `route_a_trial_samples` |
| 字段写入成功率 | 写对的计分字段数 ÷ 140（20 条 × 7 项） | 本文件第 5 节 |
| 门槛 | 不低于 95%（即 140 项中最多错 7 项）走路线 A，否则走路线 B【张宝文确认】 | `06-acceptance/thresholds.json` 的 `route_a_variable_write_success_min` |

补充规则：

1. 首轮不达标时，允许针对性修改 prompt 后**完整重跑一轮**，以第二轮为准；不允许只重跑失败的样例。修改后的 prompt 同步回 `ai-agent-system-prompt.md` 并升版本号。
2. 即使总成功率达标，只要有 B 端样例被写成 `B2C`，也要在决策记录里单列并评估：漏掉经销商的代价最高。
3. 同一样例隔天再跑一次结果不同（写入不稳定），记为不稳定项；不稳定项达到 3 条及以上，按不达标处理。
4. 决策结果、两轮数据、所用模型与 prompt 版本写进 `01-design/adr/0003-ai-route-a-b.md`。

## 7. 汇总表

| 指标 | 第一轮 | 第二轮（如有） |
|---|---|---|
| 计分字段写对数 / 140 | | |
| 字段写入成功率 | | |
| 各字段成功率（7 项分别列出） | | |
| B 端样例被判为 B2C 的条数 | | |
| 不稳定样例条数 | | |
| 平均每条 AI 回复消耗 token | | |
| 平均每个对话机器人发出的消息条数 | | |
| 结论：路线 A / 路线 B | | |

## 8. 做完之后要回填的地方

| 回填内容 | 文件 |
|---|---|
| 各平台事实的核实结论，去掉已解决的【待核实】 | `SOURCES.md`（S-B4 至 S-B15、S-M7） |
| 界面路径与节点名称 | `setup-guide.md` 第 10 节清单 |
| 真实回调样本（脱敏后） | `05-integration/webhook-service/fixtures/` |
| 每条 AI 回复的 token 数、AI 单价、客服消息加价 | `03-whatsapp/cost-model-inputs.csv`，改完重跑 `cost_model.py` |
| 路线决策 | `01-design/adr/0003-ai-route-a-b.md` |
| 号码策略的补充结论 | `01-design/adr/0002-number-strategy.md` |
| 仍未解决的问题 | 仓库的待决问题清单 |

## 9. 注意事项

1. 试用期间不向任何真实客户发消息，不导入联系人，不发模板。
2. 测试号码与测试会话在试用结束后清理；真实回调样本入库前把号码、姓名替换成虚构值。
3. 免费额度只有最多 300 个初始对话：20 条样例跑两轮加平台验证项约用 60 至 80 个，够用，但不要拿它做压力测试。
4. T-6 如需投测试广告，费用由客户广告账户承担，投放前征得客户同意【待客户确认】。
