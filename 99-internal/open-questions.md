# 待决问题汇总（内部）

> 用途：全仓库所有【待核实】【待客户确认】【张宝文确认】的汇总，按负责人分组；每条都有负责人与出处。读者：沈思锴、张宝文。**内部文件，不进客户文档。**
> 第 1 节为人工整理的重点清单；第 2 节起由 `scripts/collect_open_questions.py` 自动生成，请勿手改，改完文档后重跑脚本。

## 1. 重点清单（人工整理，按负责人分组）

### 1.1 我要做的（集成工程师 沈思锴）

| # | 事项 | 怎么核实 | 影响什么 | 期限 |
|---|---|---|---|---|
| 1 | Botmaker 内置 AI Agent 把抽取字段写入变量是否稳定、能否固定输出 JSON | 试用账号跑 20 条样例，`02-botmaker/trial-test-plan.md` | 路线 A / B 决策（`01-design/adr/0003-ai-route-a-b.md`）；走 B 加 1 人天 | 2026-10-16 |
| 2 | 真实 webhook 回调样本、重试策略、CTWA referral 是否透传 | 试用账号把回调指到抓包地址 | `05-integration` 的 fixture 与归一化；来源追踪 | W1 |
| 3 | 客户号码的国家码能否走 Coexistence | 在接入流程里实测（仅选方式 b 时） | 号码策略（`01-design/adr/0002-number-strategy.md`） | W1 |
| 4 | 10/1 之后 Botmaker 如何结算客服消息（是否加 20%、是否计入套餐对话数） | 向 Botmaker 销售要书面答复 | 成本模型 `bsp_markup_service` | 开工前 |
| 5 | Botmaker AI token 单价与可选模型清单 | 后台 Settings > Account > Products and consumption，或问销售 | 成本模型 `botmaker_ai_usd_per_1m_tokens`；模型选型 | 开工前 |
| 6 | "每号码每月前 1,000 条免费"是否属实 | Meta 官方定价页；Botmaker 确认 | 成本模型 `free_service_msgs_per_month`；对客户的费用说明 | 开工前 |
| 7 | 法、意、西及其他目标市场的官方费率 | 下载 Meta 费率卡填入 `cost-model-rates.csv` | 第三方费用区间可能变化一倍以上 | 客户给出国家分布后 |
| 8 | 未认证状态能否先承接入站咨询；发送量分级的现行数值 | Meta 官方文档 | 认证延误时的退路（`07-project/timeline.md` 第 3 节） | W0 |
| 9 | 从中国大陆访问 Botmaker 后台与 API 是否稳定 | 请客户在办公网络实测登录与坐席界面 | 销售能否正常接手；是否改用 Coexistence 手机端回复 | W0 |
| 10 | Botmaker 标签与变量名是否允许下划线 | 试用账号 | `01-design/tag-taxonomy.md` 命名 | W1 |
| 11 | 再触达模板是否会被 Meta 归为 marketing 类 | W2 第一天提交审核看结果 | 模板单价与话术 | W2 |
| 12 | Botmaker 的发票与合同主体、后台界面语言 | 问销售 | 客户财务流程；运营培训用哪种语言界面 | 开工前 |

### 1.2 张宝文要定的

| # | 事项 | 出处 | 备注 |
|---|---|---|---|
| 1 | 精简版、完整版两档的对客价格 | `00-client/报价单.md` | 我方价见 `pricing-internal.md`；15,000–30,000 CNY 区间内 |
| 2 | 验收阈值的数值，以及是否写进合同 | `06-acceptance/acceptance-criteria.md` | 建议合同只写指标名与"以验收标准文件为准" |
| 3 | 月度维护的对客价、响应时限 | `00-client/维护服务说明.md` | 我方 2,500 CNY / 月 |
| 4 | 付款节奏（建议 30 / 40 / 30）、含税与开票 | `00-client/报价单.md`、`pricing-internal.md` | |
| 5 | 开工日（假设 2026-10-12）与是否对客户承诺上线日期 | `07-project/timeline.md` | 建议只承诺"认证通过后 4 周" |
| 6 | 需求变更的计费口径 | `00-client/报价单.md` | 对客户只写"按工作量另行报价" |
| 7 | 二期优先、案例署名、Meta 审核延误不算违约 | `pricing-internal.md` 第 5 节 | 我与张宝文之间 |
| 8 | 客户选精简版时，语种与样本量的承诺范围 | `00-client/报价单.md` | |

### 1.3 客户要给的（经张宝文 / Kim）

| # | 事项 | 什么时候要 | 影响什么 |
|---|---|---|---|
| 1 | 日均咨询量、主要国家分布、是否投 Click-to-WhatsApp 广告 | 中秋碰面 | 成本模型、语种选择、套餐档位 |
| 2 | 号码方案选 a 还是 b；现有号码与 Meta 商务账户现状；用哪个公司主体做商家认证 | 中秋碰面；认证 2026-09-30 前提交 | 关键路径；隐私合规责任主体 |
| 3 | 销售写下的"有效线索标准" | 2026-10-09 前 | 分类规则与验收 |
| 4 | 100–200 条历史咨询导出 | 2026-10-09 前 | 离线评测能否按期 |
| 5 | 产品目录与现售车型；可对外说的价格与质保口径；各国经销商名单；FAQ 素材 | 开工前 | 知识库；AI 能说什么不能说什么 |
| 6 | 语种清单（完整版最多 4 个非英语语种） | 开工前 | 话术翻译、测试范围 |
| 7 | 销售名单、工作时间、周末是否值班、用飞书还是企业微信 | 中秋碰面 | 通知渠道、响应时限、夜间话术 |
| 8 | 隐私政策链接；法务对欧盟用户数据处理的复核意见 | 上线前 | 开场白隐私告知；数据存放位置 |
| 9 | 给销售的 AI 摘要用中文还是英文；品牌语气要求 | 开工前 | prompt |
| 10 | 是否启用"营销消息同意"步骤 | 开工前 | 第二阶段主动再触达的前提 |

## 2. 全量索引：数量

| 标记 | 负责人 | 条数（去重后） |
|---|---|---|
| 【待核实】 | 集成工程师（沈思锴） | 244 |
| 【张宝文确认】 | 张宝文 | 82 |
| 【待客户确认】 | 客户（经张宝文 / Kim 对接） | 221 |

## 3. 我要做的：平台、政策、价格类事实核实

负责人：集成工程师（沈思锴）

| # | 事项 | 出处 | 负责人 |
|---|---|---|---|
| 1 | 标记说明：【待核实】＝平台细节仍在核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝由张宝文最终确定。 | `00-client/培训计划.md:4` | 集成工程师（沈思锴） |
| 2 | 标记说明：【待核实】＝平台要求仍在向官方核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝由张宝文最终确定。 | `00-client/客户需提供清单.md:4` | 集成工程师（沈思锴） |
| 3 | 备齐下表材料，在 Meta 商务管理平台的商家认证功能中提交【待核实】。 | `00-client/客户需提供清单.md:29` | 集成工程师（沈思锴） |
| 4 | 具体材料以 Meta 后台的提示为准【待核实】。 | `00-client/客户需提供清单.md:40` | 集成工程师（沈思锴） |
| 5 | 号码要求 / 以公司名义办理；能接收短信或语音验证码；没有在 WhatsApp 上注册过，注册过需先注销；手机号或固定电话均可【待核实】 / 已在 WhatsApp Business App 上使用；App 版本 2.24.17 及以上；号码所属国家是否在支持范围内【待核实】 | `00-client/客户需提供清单.md:110` | 集成工程师（沈思锴） |
| 6 | 标记说明：【待核实】＝平台政策或价格仍在向官方核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝商务数字与承诺由张宝文最终确定。 | `00-client/报价单.md:5` | 集成工程师（沈思锴） |
| 7 | 下表为估算【待核实】，单位除注明外为 USD/月。摩兽直接向平台开户付款，我方不经手。 | `00-client/报价单.md:57` | 集成工程师（沈思锴） |
| 8 | WhatsApp 消息费 / Meta，经 Botmaker 结算 / 20 / 170 / 1,090 / 2026-10-01 起窗口内回复按条计费，单价随客户所在国家变化；Botmaker 加收的服务费比例【待核实】 | `00-client/报价单.md:62` | 集成工程师（沈思锴） |
| 9 | AI 用量费 / Botmaker / 不足 10 / 50 / 680 / 按 AI 处理的文字量计费；单价未公开【待核实】 | `00-client/报价单.md:63` | 集成工程师（沈思锴） |
| 10 | 每个号码每月前 1,000 条窗口内回复免费 / 已计入 / 【待核实】 | `00-client/报价单.md:80` | 集成工程师（沈思锴） |
| 11 | 法国、意大利、西班牙等市场的单条费率 / 暂用已核实市场的平均值代替 / 【待核实】 | `00-client/报价单.md:81` | 集成工程师（沈思锴） |
| 12 | 第三方费用由平台直接向摩兽出具账单，以美元计价、信用卡支付；平台能否提供符合摩兽财务要求的发票【待核实】。 | `00-client/报价单.md:113` | 集成工程师（沈思锴） |
| 13 | Botmaker 对窗口内回复的结算方式、AI 用量单价、每月 1,000 条免费额度 / 【待核实】 | `00-client/报价单.md:140` | 集成工程师（沈思锴） |
| 14 | 需要注意 / 号码要能接收短信或语音验证码，且没有在 WhatsApp 上注册过（注册过需先注销）；社媒入口的链接要换成新号 / App 版本需 2.24.17 及以上；接入当天持机人要在场扫码；之后至少每 14 天打开一次 App，否则连接会断开；模板消息只能从平台发送；广播列表停用，一对一聊天中的阅后即焚、一次性查看、实时位置会被关闭… | `00-client/方案书.md:229` | 集成工程师（沈思锴） |
| 15 | 能。官方提供并存方式（Coexistence），Botmaker 官方支持，条件见上表方式 b。是否选用，取决于这个号码对现有业务有多重要，以及号码所属国家是否在支持范围内【待核实】。 | `00-client/方案书.md:240` | 集成工程师（沈思锴） |
| 16 | 自 2026-10-01 起，Meta 对 24 小时客服窗口内企业发出的每一条自由回复按条收费，人工回复和 AI 回复都算，单价按客户所在国家确定。MVP 上线必然在此之后，所以费用估算已按新规则计算（见第 11 节）。两点利好：由 Click-to-WhatsApp 广告或 Facebook 主页按钮进入的对话，72 小时内的消息免费… | `00-client/方案书.md:267` | 集成工程师（沈思锴） |
| 17 | 以下为估算【待核实】，按 2026-10-01 之后的计费规则计算；拿到摩兽真实的咨询量、国家分布和广告投放情况后会重新测算。 | `00-client/方案书.md:389` | 集成工程师（沈思锴） |
| 18 | Meta 审核延误 / 商家认证和显示名审核由 Meta 决定，可能被退回 / 国庆假期前提交；按清单备齐材料；审核期间先完成其他工作，未认证状态下能否先承接入站咨询【待核实】 | `00-client/方案书.md:429` | 集成工程师（沈思锴） |
| 19 | 网络访问 / Meta、WhatsApp、Botmaker 后台从中国大陆访问需要跨境网络 / 沿用摩兽海外社媒团队现有的合规跨境网络环境；访问稳定性【待核实】 | `00-client/方案书.md:440` | 集成工程师（沈思锴） |
| 20 | 标记说明：【待核实】＝平台细节仍在核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝商务数字与承诺由张宝文最终确定。 | `00-client/维护服务说明.md:4` | 集成工程师（沈思锴） |
| 21 | 假设：Botmaker 后台的具体菜单名称以培训时看到的实际界面为准【待核实】；各指标的目标值为建议值【待客户确认】；审核人为建议分工【待客户确认】。 | `00-client/运维手册.md:5` | 集成工程师（沈思锴） |
| 22 | 导入 / 在 Botmaker 后台的知识库（Knowledge Base）功能中新增或修改【待核实】 / 运营 | `00-client/运维手册.md:35` | 集成工程师（沈思锴） |
| 23 | 咨询量（按天、按周） / Botmaker 数据看板【待核实】、线索库 / 趋势；哪个帖子带来高峰 / 突增时提醒销售；突降时检查链接是否失效 | `00-client/运维手册.md:128` | 集成工程师（沈思锴） |
| 24 | 销售首次响应时间 / Botmaker 数据看板【待核实】 / 工作时间内 B 端线索 2 小时内【待客户确认】 / 反馈给销售负责人 | `00-client/运维手册.md:133` | 集成工程师（沈思锴） |
| 25 | 号码质量评级 / Meta 后台的 WhatsApp 管理功能【待核实】 / 保持良好 / 下降时立即停发模板并找技术 | `00-client/运维手册.md:138` | 集成工程师（沈思锴） |
| 26 | 假设：响应时限、周末值班安排、线索分工为建议值【待客户确认】；Botmaker 后台的按钮名称以培训时看到的实际界面为准【待核实】；结束分类的名称为暂定【待核实】【待客户确认】。 | `00-client/销售接手SOP.md:5` | 集成工程师（沈思锴） |
| 27 | 把会话分配给自己【待核实】。接手之后，AI 不再回复这位客户。 | `00-client/销售接手SOP.md:49` | 集成工程师（沈思锴） |
| 28 | 在 Botmaker 的会话里选择模板发送【待核实】。模板的审核类别由 Meta 决定，可能影响单条费用【待核实】。 | `00-client/销售接手SOP.md:98` | 集成工程师（沈思锴） |
| 29 | 结束会话时，在 Botmaker 里选择一个结束分类，系统会据此更新线索库里的状态。名称为暂定【待核实】【待客户确认】。 | `00-client/销售接手SOP.md:102` | 集成工程师（沈思锴） |
| 30 | 同事休假或离职，会话没人管 / 由销售负责人把会话转给其他销售【待核实】 | `00-client/销售接手SOP.md:122` | 集成工程师（沈思锴） |
| 31 | 中文后台 / 官网与帮助中心为英、西、葡三语，后台语言【待核实】（SOURCES S-B14） / 任务书前提为"有中文后台"，本次未复核【待核实】 / 阿里云控制台，任务书前提为"有中文后台"，本次未复核【待核实】 | `01-design/adr/0001-platform-choice.md:31` | 集成工程师（沈思锴） |
| 32 | 内置 AI Agent 与知识库 / 有；按 token 另计费，单价未公开（SOURCES S-B7） / 【待核实】 / 【待核实】 | `01-design/adr/0001-platform-choice.md:32` | 集成工程师（沈思锴） |
| 33 | 计价货币 / USD（SOURCES S-B3） / 【待核实】 / 【待核实】 | `01-design/adr/0001-platform-choice.md:33` | 集成工程师（沈思锴） |
| 34 | 备注 / 主要市场在拉美，有时差；开票与合同主体【待核实】 / 若内置 AI 能力不足，需要路线 B 式的外部调用承担更多工作 / 国内主体签约与开票可能更顺【待核实】；同上 | `01-design/adr/0001-platform-choice.md:34` | 集成工程师（沈思锴） |
| 35 | 1 之后 Botmaker 如何结算客服消息 / 【待核实】SOURCES S-B13 | `01-design/adr/0001-platform-choice.md:58` | 集成工程师（沈思锴） |
| 36 | 后台界面语言、发票与合同主体 / 【待核实】SOURCES S-B14 | `01-design/adr/0001-platform-choice.md:59` | 集成工程师（沈思锴） |
| 37 | 中国大陆访问稳定性 / 【待核实】SOURCES S-B15 | `01-design/adr/0001-platform-choice.md:60` | 集成工程师（沈思锴） |
| 38 | 超量后是否允许长期不升档 / 【待核实】03-whatsapp/cost-model.md 第 4 节 | `01-design/adr/0001-platform-choice.md:61` | 集成工程师（沈思锴） |
| 39 | 部分国家码的号码可能不支持 Coexistence：第三方文章列过清单，官方页面当前未见；以客户实际号码在接入流程中的结果为准【待核实】（SOURCES S-M7）。 | `01-design/adr/0002-number-strategy.md:31` | 集成工程师（沈思锴） |
| 40 | 同一号码上 Bot 与真人并存：销售在手机 App 里回复后，平台侧能否自动让 Bot 对该会话保持静音【待核实】，列入试用验证（02-botmaker/trial-test-plan.md）。 | `01-design/adr/0002-number-strategy.md:32` | 集成工程师（沈思锴） |
| 41 | 客户号码的国家码是否在 Coexistence 支持范围内 / 【待核实】SOURCES S-M7 | `01-design/adr/0002-number-strategy.md:58` | 集成工程师（沈思锴） |
| 42 | 未完成商家认证时可否先承接入站会话、主动发送上限是多少 / 【待核实】SOURCES S-M8 | `01-design/adr/0002-number-strategy.md:59` | 集成工程师（沈思锴） |
| 43 | Coexistence 下真人在 App 回复后 Bot 的静音行为 / 【待核实】 | `01-design/adr/0002-number-strategy.md:60` | 集成工程师（沈思锴） |
| 44 | AI Agent 写变量的稳定性、是否支持 JSON 输出 / 【待核实】SOURCES S-B9，由决策门回答 | `01-design/adr/0003-ai-route-a-b.md:43` | 集成工程师（沈思锴） |
| 45 | Code Action 调用频率上限 / 【待核实】SOURCES S-B10 | `01-design/adr/0003-ai-route-a-b.md:44` | 集成工程师（沈思锴） |
| 46 | 卡片里回到 Botmaker 会话的链接格式 / 【待核实】 | `01-design/adr/0005-notification-channel.md:44` | 集成工程师（沈思锴） |
| 47 | 成本 / 单价未公开【待核实】；成本模型按每百万 token 1.0 至 5.0 USD 的占位区间估算 / 公开价位低；路线 B 的模型费在任何档位都很小（03-whatsapp/cost-model-results.md） / 低 | `01-design/adr/0006-model-selection.md:29` | 集成工程师（沈思锴） |
| 48 | 数据条款 / Botmaker 作为服务商承担；其下游模型方是否用于训练【待核实】 / 需选择有"不用于训练"承诺的商用接口档位，并留存书面依据【待核实】 / 同上；另需评估欧盟用户数据进入境内模型服务的跨境合规【待客户确认】需法务复核 | `01-design/adr/0006-model-selection.md:30` | 集成工程师（沈思锴） |
| 49 | Botmaker 可选模型清单与 token 单价 / 【待核实】SOURCES S-B7、S-B8 | `01-design/adr/0006-model-selection.md:56` | 集成工程师（沈思锴） |
| 50 | 各候选的"不用于训练"条款依据 / 【待核实】 | `01-design/adr/0006-model-selection.md:57` | 集成工程师（沈思锴） |
| 51 | Code Action 可调外部 HTTP、单次执行上限 90 秒（SOURCES S-B10）；调用频率上限【待核实】。 | `01-design/architecture.md:111` | 集成工程师（沈思锴） |
| 52 | Botmaker webhook 的重试与超时策略 / 【待核实】SOURCES S-B5 | `01-design/architecture.md:174` | 集成工程师（沈思锴） |
| 53 | webhook 真实回调样本与字段 / 【待核实】SOURCES S-B6 | `01-design/architecture.md:175` | 集成工程师（沈思锴） |
| 54 | Click-to-WhatsApp referral 明细是否进入回调 / 【待核实】SOURCES S-B12 | `01-design/architecture.md:177` | 集成工程师（沈思锴） |
| 55 | 销售所在网络能否稳定打开 Botmaker 坐席界面 / 【待核实】SOURCES S-B15 | `01-design/architecture.md:178` | 集成工程师（沈思锴） |
| 56 | 写入变量 / source_code（平台内写入方式【待核实】；集成服务会用同一规则再解析一次，以服务端为准） | `01-design/conversation-flow.md:45` | 集成工程师（沈思锴） |
| 57 | 会话级变量复位 / 进入本状态时把 escalation_flag 置为 false、escalation_reason 置空。Botmaker 的会话变量很可能按联系人长期保留【待核实】；不复位的话，老客户再次来访的第一条消息就会带着上一次的升级标记，再次触发销售通知。线索类字段（公司、类型、国家等）不复位，老客户不用重答 | `01-design/conversation-flow.md:55` | 集成工程师（沈思锴） |
| 58 | 动作 / 结束分类经事件回调回写线索 status（映射见 routing-rules.md 第 5 节）；客户再次来访回到 S1_GREETING 或直接续接原队列【待核实】 | `01-design/conversation-flow.md:203` | 集成工程师（沈思锴） |
| 59 | 一个联系人一条线索**：以 E.164 号码为去重键，lead_id 由它哈希生成；同一客户多次来访更新同一条记录，回调重放不会产生重复线索。平台未给出号码时（客户以用户名联系、回调里只有业务范围用户标识【待核实】），改用平台客户 ID 作键（bm:<customerId>），phone 与 country_by_phone 留空，国家改… | `01-design/lead-schema.md:8` | 集成工程师（沈思锴） |
| 60 | Botmaker 会话变量与字段同名**（shared/tromox_lead/fields.py 中的 BOTMAKER_VARIABLES）。若平台不接受下划线变量名【待核实】，集成服务的归一化同时接受驼峰写法（b2bType 等）。 | `01-design/lead-schema.md:12` | 集成工程师（沈思锴） |
| 61 | phone / string (E.164) \ / null / 系统 / 客户 WhatsApp 号码，统一为 E.164（如 +4915112345678）；客户以用户名联系、平台只给出业务范围用户 ID 时为空【待核实】 /  / 是 | `01-design/lead-schema.md:20` | 集成工程师（沈思锴） |
| 62 | referral / object \ / null / 系统 / Click-to-WhatsApp 广告 referral（source_id、source_url、headline 等）；是否透传【待核实】 | `01-design/lead-schema.md:36` | 集成工程师（沈思锴） |
| 63 | 销售结束会话时在 Botmaker 选择结束分类（typification），集成服务据此回写 status；映射表见 05-integration/botmaker-api-notes.md。【待核实】 | `01-design/lead-schema.md:111` | 集成工程师（沈思锴） |
| 64 | "description": "Click-to-WhatsApp ad referral. Whether Botmaker passes it through is 【待核实】.", | `01-design/lead.schema.json:54` | 集成工程师（沈思锴） |
| 65 | 停用 AI / 转人工后对该会话静音 Bot，避免 AI 与销售同时回复；会话结束后恢复。平台内的具体动作名称【待核实】；API 侧聊天对象带 isBotMuted 字段（SOURCES S-B2） | `01-design/routing-rules.md:119` | 集成工程师（沈思锴） |
| 66 | 结束分类与线索状态的映射（分类名称【待核实】【待客户确认】）： | `01-design/routing-rules.md:126` | 集成工程师（沈思锴） |
| 67 | 窗口规则：客户最后一条消息之后 24 小时内可以自由回复；窗口关闭后只能发经 Meta 预审的模板消息。窗口截止时间 = last_message_ts + 24 小时；Botmaker 的聊天对象直接给出 whatsAppWindowCloseDatetime（SOURCES S-B2），通知卡片上以北京时间显示截止时间。客户每回复一次… | `01-design/routing-rules.md:158` | 集成工程师（沈思锴） |
| 68 | 模板属 utility 类，措辞不带促销内容；Meta 可能改判为 marketing 类【待核实】。模板正文见 02-botmaker/templates/。 | `01-design/routing-rules.md:176` | 集成工程师（沈思锴） |
| 69 | Botmaker 是否把 referral 明细放进 webhook 回调 / 【待核实】帮助中心的回调示例里没有这一段（SOURCES S-B6）；试用账号第一周验证（02-botmaker/trial-test-plan.md） | `01-design/source-tracking.md:98` | 集成工程师（沈思锴） |
| 70 | 假设：Botmaker 标签名可使用小写字母、数字与下划线【待核实】；若不支持下划线，统一去掉下划线改驼峰，映射关系不变。 | `01-design/tag-taxonomy.md:4` | 集成工程师（沈思锴） |
| 71 | 假设：支持语种、工作时间、回复时限、隐私政策链接均为默认值【待客户确认】；AI Agent 可用的动作（转人工、跳转流程）与变量写入方式以试用账号实测为准【待核实】（SOURCES S-B9）。 | `02-botmaker/ai-agent-system-prompt.md:5` | 集成工程师（沈思锴） |
| 72 | 交接话术由谁发有两种部署方式，按试用结果二选一【待核实】：默认由 AI 发（可即时翻译，不用在流程里维护各语种版本）；若 AI Agent 能直接触发"转人工"流程节点且该节点自带各语种话术，则把上面一句改为 "When you hand over, trigger the handover and send nothing: the f… | `02-botmaker/ai-agent-system-prompt.md:145` | 集成工程师（沈思锴） |
| 73 | "是否在工作时间"由流程判断并通过变量或节点分支告诉 AI【待核实】；AI 自己不推算时间。 | `02-botmaker/ai-agent-system-prompt.md:146` | 集成工程师（沈思锴） |
| 74 | 是否需要平台支持结构化 JSON 输出 / 不需要。平台是否支持 JSON 输出【待核实】；若支持，可作为后续优化，把 16 个字段合成一次写入 / 不依赖平台，由外部调用保证固定 JSON | `02-botmaker/ai-agent-system-prompt.md:265` | 集成工程师（沈思锴） |
| 75 | 连续无关消息的限流（例如同一会话内拒答超过若干次后不再回复）如需要，在流程层处理【待核实】，不写进 prompt。 | `02-botmaker/ai-agent-system-prompt.md:270` | 集成工程师（沈思锴） |
| 76 | 假设：账号、号码、Meta 商务账户全部开在客户名下，集成工程师只拿管理权限；后台界面以英文为准；界面路径只写已在帮助中心读到的（见 SOURCES.md），其余一律写成"在 Botmaker 后台的 X 功能中"并标【待核实】，首次进入试用账号时补全。 | `02-botmaker/setup-guide.md:4` | 集成工程师（沈思锴） |
| 77 | 前置：客户已按 03-whatsapp/meta-onboarding-checklist.md 准备好 Meta 商务账户与号码；操作人所在网络可稳定访问 Botmaker 后台（SOURCES S-B15）【待核实】。 | `02-botmaker/setup-guide.md:5` | 集成工程师（沈思锴） |
| 78 | 套餐先不付费，试用期验证完（trial-test-plan.md）再由客户绑卡开 Standard（149 USD/月，SOURCES S-B3）。开通 WhatsApp 商业平台账户另有一次性 99 USD。发票与合同主体【待核实】（SOURCES S-B14）。 | `02-botmaker/setup-guide.md:37` | 集成工程师（沈思锴） |
| 79 | 账号内的时区、语言等全局设置：在 Botmaker 后台的账号设置功能中完成【待核实】；号码的时区在第 2 步接入时填写（SOURCES S-B4）。 | `02-botmaker/setup-guide.md:38` | 集成工程师（沈思锴） |
| 80 | 验证方法**：客户管理员与集成工程师都能登录同一个项目；在 Botmaker 后台的成员管理功能中【待核实】能看到客户邮箱为所有者。截图存入交付记录（验收项 C5）。 | `02-botmaker/setup-guide.md:40` | 集成工程师（沈思锴） |
| 81 | 额外约束 / 号码需能收短信或语音验证码，且当前未注册在任何 WhatsApp 上 / App 版本不低于 2.24.17；至少每 14 天打开一次 App，否则断连；吞吐固定 20 条/秒；阅后即焚、一次性查看、实时位置、广播列表停用；号码国家码是否受限【待核实】（SOURCES S-M7） | `02-botmaker/setup-guide.md:51` | 集成工程师（沈思锴） |
| 82 | 设置两步验证 PIN 并交客户保管：在 Botmaker 或 Meta 后台的号码设置功能中【待核实】。 | `02-botmaker/setup-guide.md:59` | 集成工程师（沈思锴） |
| 83 | 与销售约定分工：哪些会话由机器人先接、哪些由人在手机上直接回。人从手机 App 回复后机器人是否自动静默【待核实】，在试用账号验证（trial-test-plan.md 的 T-1）。 | `02-botmaker/setup-guide.md:68` | 集成工程师（沈思锴） |
| 84 | 在 Botmaker 后台的变量管理功能中【待核实】建下列 18 个会话变量，**变量名与线索字段名逐字相同**（源头：shared/tromox_lead/fields.py 的 BOTMAKER_VARIABLES）。平台若不接受下划线【待核实】，改用驼峰（如 b2bType），集成服务的归一化两种写法都接受。 | `02-botmaker/setup-guide.md:83` | 集成工程师（沈思锴） |
| 85 | S1_GREETING / 一条带 3 个回复按钮的消息 / 按钮标题不超过 20 个字符，最多 3 个：Dealer/Distributor、Rider or Customer、Other；话术含 AI 身份告知与隐私政策链接 {privacy_url}【待客户确认】；**进入本状态先把变量 escalation_flag 置为 fal… | `02-botmaker/setup-guide.md:113` | 集成工程师（沈思锴） |
| 86 | S7_AFTER_HOURS / 工作时间判断：在 Botmaker 后台的营业时间功能中【待核实】配置 {working_hours}【待客户确认】 / 非工作时间转人工时改发夜间话术，AI 继续可答 FAQ | `02-botmaker/setup-guide.md:119` | 集成工程师（沈思锴） |
| 87 | 静默机器人（该会话内 AI 不再自动回复）：在 Botmaker 的转人工动作中【待核实】；API 侧可见 isBotMuted 字段（SOURCES S-B2）。 | `02-botmaker/setup-guide.md:126` | 集成工程师（沈思锴） |
| 88 | 建工单：在流程内直接建工单的节点【待核实】；若流程内没有，退路是由 Code Action 调用 POST /tickets（SOURCES S-B2，60 次/分钟），在试用账号里定。 | `02-botmaker/setup-guide.md:128` | 集成工程师（沈思锴） |
| 89 | 资源（Resources）里挂上第 5 步的知识库；动作（Actions）里只开放"转人工"与必要的流程跳转，其余不开。可用动作清单【待核实】。 | `02-botmaker/setup-guide.md:143` | 集成工程师（沈思锴） |
| 90 | 模型：Bot Designer 左侧工具栏 "Generative model" 设 Bot 默认模型；AI Agent 配置最后一步 "Generative Model" 里可选 "Use a different model" 单独指定（SOURCES S-B8）。未指定时默认 "GPT-4 Mini"。**离线评测与生产必须是同一模型… | `02-botmaker/setup-guide.md:144` | 集成工程师（沈思锴） |
| 91 | 导入方式：在 Botmaker 后台的知识库（Knowledge Base）功能中上传【待核实】；也可用 API POST /knowledge-bases 新建、PUT /knowledge-bases 更新（SOURCES S-B2，type 可取 www、doc、content、articles、other，language 含 E… | `02-botmaker/setup-guide.md:158` | 集成工程师（沈思锴） |
| 92 | 队列在 Botmaker 后台的服务队列（Service queues / attention queues）功能中建【待核实】；API 侧只能查与改，不能建（SOURCES S-B2，GET /attention-queues 限 5 次/分钟）。 | `02-botmaker/setup-guide.md:176` | 集成工程师（沈思锴） |
| 93 | 转人工时建工单，标题建议 [B2B][DE] 公司名 - 产品，正文放 ai_summary 与关键字段。工单自定义字段【待核实】；MVP 不依赖自定义字段。 | `02-botmaker/setup-guide.md:180` | 集成工程师（沈思锴） |
| 94 | 写入方式按优先级：流程节点里的打标签动作（seg_ 跟按钮走）【待核实】；不能在流程里算的（country_、src_、prio_）由集成服务算好存进线索库的 tags 字段，是否同时回写 Botmaker 会话标签（PATCH /chats/{chatReference}，3 次/秒，SOURCES S-B2）在试用后定【待核实】。标签… | `02-botmaker/setup-guide.md:191` | 集成工程师（沈思锴） |
| 95 | 销售结束会话时必须选一个结束分类，集成服务据此回写线索状态（事件回调里带 typification，SOURCES S-B6）。分类名【待核实】【待客户确认】： | `02-botmaker/setup-guide.md:195` | 集成工程师（沈思锴） |
| 96 | Bot 消息（Bot Messages） / 试用期勾，稳定后可关 / AI 写完变量后，变量变更可能随下一条 Bot 消息送达【待核实】；确认变量能随用户消息可靠送达后关掉，减少回调量 | `02-botmaker/setup-guide.md:223` | 集成工程师（沈思锴） |
| 97 | 回调的重试与超时策略未见官方说明【待核实】（SOURCES S-B5）：集成服务按"先落盘原始事件、立即返回 200、再处理"设计，并按消息 _id_ 做幂等。 | `02-botmaker/setup-guide.md:228` | 集成工程师（沈思锴） |
| 98 | 用测试手机发一条消息，集成服务日志里出现一条 type=message 的原始事件，字段与 05-integration/webhook-service/fixtures/ 的样例对得上；对不上的字段回填 fixture 并去掉相应的【待核实】。 | `02-botmaker/setup-guide.md:233` | 集成工程师（沈思锴） |
| 99 | 运行环境：Node.js v22；外部 HTTP 用内置 rp；单次执行超时 90 秒；每次最多写 200 个变量、每个变量值不超过 100 KB（SOURCES S-B10）。调用频率上限【待核实】。 | `02-botmaker/setup-guide.md:241` | 集成工程师（沈思锴） |
| 100 | 在 Botmaker 后台的代码功能中新建并发布一个 Code Action【待核实】，然后在 Bot Designer 里通过 "More > Action > Code Actions" 把它挂到 S2、S4 之后以及转人工之前（SOURCES S-B10）。 | `02-botmaker/setup-guide.md:242` | 集成工程师（沈思锴） |
| 101 | 外部分类接口的归属（直连模型的 OpenAI-compatible 接口，还是在集成服务里加一个分类端点）由 01-design/adr/0003-ai-route-a-b.md 定；无论哪种，密钥都不写进代码正文，用 Botmaker 的常量或密钥配置功能保存【待核实】。 | `02-botmaker/setup-guide.md:243` | 集成工程师（沈思锴） |
| 102 | 骨架（只用了帮助中心文章里出现过的对象与方法；字段名以试用账号实测为准【待核实】）： | `02-botmaker/setup-guide.md:244` | 集成工程师（沈思锴） |
| 103 | 角色与权限在 Botmaker 后台的成员与角色功能中配置【待核实】；平台支持自定义角色（SOURCES S-B2 的 roles 资源）。 | `02-botmaker/setup-guide.md:304` | 集成工程师（沈思锴） |
| 104 | 所有登录账号开启两步验证：在 Botmaker 后台的安全设置功能中【待核实】。 | `02-botmaker/setup-guide.md:306` | 集成工程师（沈思锴） |
| 105 | 假设：三条模板都按 utility（事务通知）类别提交；Meta 可能把它们改判为 marketing（营销）类，费率与发送条件随之变化【待核实】；ES / DE / FR / PT 译文为占位，语种清单与译文均【待客户确认】，须由母语者审核后再提交。 | `02-botmaker/templates/README.md:4` | 集成工程师（沈思锴） |
| 106 | 类别选 utility / 内容必须围绕客户自己发起的那次咨询，不含促销、优惠、新品推荐、节日问候；出现这些内容会被改判为 marketing【待核实】 | `02-botmaker/templates/README.md:28` | 集成工程师（沈思锴） |
| 107 | 变量不要太多 / 正文里固定文字要明显多于变量，否则容易被拒【待核实】 | `02-botmaker/templates/README.md:32` | 集成工程师（沈思锴） |
| 108 | 按钮 / 只用快捷回复按钮，标题不超过 25 个字符【待核实】；第二个按钮给客户一个体面的"不需要了"，减少被拉黑与举报 | `02-botmaker/templates/README.md:34` | 集成工程师（沈思锴） |
| 109 | 提交入口：在 Botmaker 后台的 WhatsApp 模板管理功能中【待核实】；也可用 API POST /whatsapp/templates（限 1 次/秒，SOURCES S-B2）。审核通常较快，但 W2 第一天就提交，不要等到 UAT（07-project/timeline.md）。 | `02-botmaker/templates/README.md:39` | 集成工程师（沈思锴） |
| 110 | 每月看一次模板的送达、已读与回复情况：在 Botmaker 后台的模板或通知报表功能中【待核实】。 | `02-botmaker/templates/README.md:56` | 集成工程师（沈思锴） |
| 111 | 假设：类别 utility；是否被 Meta 改判为 marketing【待核实】；译文与语种【待客户确认】。 | `02-botmaker/templates/tromox_info_request_v1.md:4` | 集成工程师（沈思锴） |
| 112 | 假设：类别 utility；是否被 Meta 改判为 marketing【待核实】；译文与语种【待客户确认】；仅完整版包含本模板。 | `02-botmaker/templates/tromox_support_update_v1.md:4` | 集成工程师（沈思锴） |
| 113 | 用途：开工第 1 周在试用账号里把所有【待核实】的平台行为测一遍，并用 20 条样例决定 AI 走路线 A 还是路线 B；结果是 01-design/adr/0003-ai-route-a-b.md 的决策依据。读者：集成工程师；结论抄送张宝文。 | `02-botmaker/trial-test-plan.md:3` | 集成工程师（沈思锴） |
| 114 | 之后客服消息与 AI token 在账单里怎么体现 / T-7 / 成本模型的两个【待核实】输入 | `02-botmaker/trial-test-plan.md:17` | 集成工程师（沈思锴） |
| 115 | T-11 / 回调里没有号码的联系人 / 查看 contactId 是否总是号码；若测试中出现业务范围用户标识（以用户名联系的客户），保存 1 份样本【待核实】 / 确认集成服务按平台客户 ID 入库并照常通知，号码与号码国家留空 / 05-integration/botmaker-api-notes.md；01-design/lead-… | `02-botmaker/trial-test-plan.md:47` | 集成工程师（沈思锴） |
| 116 | 各平台事实的核实结论，去掉已解决的【待核实】 / SOURCES.md（S-B4 至 S-B15、S-M7） | `02-botmaker/trial-test-plan.md:137` | 集成工程师（沈思锴） |
| 117 | 模型提供方不得用我们的数据训练或改进模型 / 选有明确"接口数据不用于训练"条款的企业级或接口级服务；消费级产品一律不用 / 选型时逐家核对条款【待核实】 | `03-whatsapp/compliance.md:38` | 集成工程师（沈思锴） |
| 118 | Botmaker 内置模型同样适用 / 向 Botmaker 索取数据处理协议与下游处理方清单，确认其内置模型的数据不用于训练 / 【待核实】 | `03-whatsapp/compliance.md:40` | 集成工程师（沈思锴） |
| 119 | 本方案的主动消息只有一种**：针对客户自己发起的咨询做后续跟进（02-botmaker/templates/），按 utility 类别提交；是否被改判为 marketing【待核实】。 | `03-whatsapp/compliance.md:50` | 集成工程师（沈思锴） |
| 120 | 同意记录要可举证**：何时、在哪个会话、客户点了哪个按钮。线索库里至少保留同意时间与来源会话的标识【待核实】实现方式。 | `03-whatsapp/compliance.md:54` | 集成工程师（沈思锴） |
| 121 | WhatsApp / Meta / 平台方 / 其角色以 Meta 的条款为准【待核实】 | `03-whatsapp/compliance.md:66` | 集成工程师（沈思锴） |
| 122 | AI 身份告知 / 开场第一句说明是 AI 虚拟助手；被问到时如实回答。欧盟《人工智能法》对聊天机器人的透明度义务及其适用时间【待核实】 / 已写入话术与 prompt | `03-whatsapp/compliance.md:73` | 集成工程师（沈思锴） |
| 123 | 运营在 1 个工作日内登记到请求台账；法定答复期限通常为一个月【待核实】，内部目标 10 个工作日内完成【待客户确认】。 | `03-whatsapp/compliance.md:82` | 集成工程师（沈思锴） |
| 124 | 删除范围：线索库按 phone 删除该线索记录与原始事件；Botmaker 内的联系人与会话记录，在 Botmaker 后台的联系人管理功能中删除或匿名化【待核实】；已导出的表格与备份同步处理。 | `03-whatsapp/compliance.md:83` | 集成工程师（沈思锴） |
| 125 | Botmaker / 消息全文、联系人、变量、工单 / Botmaker 的云环境（其对外 IP 属 Google Cloud 网段，推断，SOURCES S-B15）；具体区域【待核实】 / 索取数据处理协议与数据驻留说明 | `03-whatsapp/compliance.md:92` | 集成工程师（沈思锴） |
| 126 | 会话记录 / Botmaker / 按平台设置，可配置范围【待核实】 / 与线索保留期对齐 | `03-whatsapp/compliance.md:107` | 集成工程师（沈思锴） |
| 127 | free_service_msgs_per_month,1000,1000,1000,条/号码/月,【待核实】,SOURCES S-M3：仅 BSP 来源，官方页面未读到；敏感性分析含 0 条情景 | `03-whatsapp/cost-model-inputs.csv:12` | 集成工程师（沈思锴） |
| 128 | bsp_markup_service,0.20,0.20,0.20,比例,【待核实】,SOURCES S-B13：Botmaker 对客服消息的加价未公布，暂按通知类同为 20% 假设 | `03-whatsapp/cost-model-inputs.csv:13` | 集成工程师（沈思锴） |
| 129 | botmaker_ai_usd_per_1m_tokens,1.0,2.5,5.0,USD/百万 token,【待核实】,SOURCES S-B7：单价未公开，此为占位区间 | `03-whatsapp/cost-model-inputs.csv:16` | 集成工程师（沈思锴） |
| 130 | ext_model_usd_per_1m_input,0.15,1.00,3.00,USD/百万 token,【待核实】,占位区间（小模型到旗舰模型的公开价位量级），以选定模型官网价为准 | `03-whatsapp/cost-model-inputs.csv:20` | 集成工程师（沈思锴） |
| 131 | ext_model_usd_per_1m_output,0.60,5.00,15.00,USD/百万 token,【待核实】,同上 | `03-whatsapp/cost-model-inputs.csv:21` | 集成工程师（沈思锴） |
| 132 | FR,法国,0.10,,【待核实】,WEU,无官方数字：取已复核西欧市场均值作代理 | `03-whatsapp/cost-model-rates.csv:3` | 集成工程师（沈思锴） |
| 133 | IT,意大利,0.15,,【待核实】,WEU,同上 | `03-whatsapp/cost-model-rates.csv:4` | 集成工程师（沈思锴） |
| 134 | ES,西班牙,0.10,,【待核实】,WEU,同上 | `03-whatsapp/cost-model-rates.csv:5` | 集成工程师（沈思锴） |
| 135 | OTHER,其他市场,0.30,,【待核实】,ALL,无官方数字：取全部已复核市场均值作代理 | `03-whatsapp/cost-model-rates.csv:7` | 集成工程师（沈思锴） |
| 136 | 法国 / 10% / 0.0417（代理值） / 【待核实】 | `03-whatsapp/cost-model-results.md:12` | 集成工程师（沈思锴） |
| 137 | 意大利 / 15% / 0.0417（代理值） / 【待核实】 | `03-whatsapp/cost-model-results.md:13` | 集成工程师（沈思锴） |
| 138 | 西班牙 / 10% / 0.0417（代理值） / 【待核实】 | `03-whatsapp/cost-model-results.md:14` | 集成工程师（沈思锴） |
| 139 | 其他市场 / 30% / 0.0196（代理值） / 【待核实】 | `03-whatsapp/cost-model-results.md:16` | 集成工程师（沈思锴） |
| 140 | 加权平均费率：0.0346 USD/条（Meta 基础价，未含 BSP 加价）。代理值 = 已复核市场的算术平均（西欧组：德、荷、英；全部组：所有已复核市场），仅用于量级估算。【待核实】 | `03-whatsapp/cost-model-results.md:18` | 集成工程师（沈思锴） |
| 141 | cost-model-inputs.csv / 低/中/高三档的全部输入，含状态列（假设 / 【待核实】 / 【待客户确认】 / 已复核） / 是 | `03-whatsapp/cost-model.md:14` | 集成工程师（沈思锴） |
| 142 | 月度免费额度抵扣：M_free = min(M − M_fep, free_service_msgs_per_month)（【待核实】，SOURCES S-M3）。 | `03-whatsapp/cost-model.md:37` | 集成工程师（沈思锴） |
| 143 | "对话"的定义**：Botmaker 套餐里的 conversation 未见官方定义，超量条款写的是 "per additional user"；模型按"一个月内一个客户算一个对话"处理。【待核实】 | `03-whatsapp/cost-model.md:49` | 集成工程师（沈思锴） |
| 144 | 套餐升档**：按公开单价，"Standard + 超量"在任何对话量下都不比升档贵；升 Scale / Pro 的理由是坐席数（10 / 20 / 50），不是对话量。超量是否允许长期不升档。【待核实】 | `03-whatsapp/cost-model.md:50` | 集成工程师（沈思锴） |
| 145 | 代理费率**：法、意、西和"其他市场"没有取得官方数字，用已复核市场的算术平均代替（西欧组取德、荷、英；全部组取所有已复核市场）。这只保证量级正确。拿到 Meta 费率卡后，把数字填进 cost-model-rates.csv 的 rate_usd 列即可替换代理值。【待核实】 | `03-whatsapp/cost-model.md:51` | 集成工程师（沈思锴） |
| 146 | "代理值 = 已复核市场的算术平均（西欧组：德、荷、英；全部组：所有已复核市场），仅用于量级估算。【待核实】", | `03-whatsapp/cost_model.py:236` | 集成工程师（沈思锴） |
| 147 | 假设：客户已有运营 Facebook / Instagram 的商务账户【待客户确认】；Meta 的认证材料要求、分级数值等属平台通用规则，本次未逐条重新核对原文（SOURCES S-M8），凡带数字或具体要求处均标【待核实】，以提交时 Meta 后台的提示为准。 | `03-whatsapp/meta-onboarding-checklist.md:4` | 集成工程师（沈思锴） |
| 148 | 官网域名验证 / 在商务账户里完成域名验证，有助于认证与后续广告归因【待核实】 / 客户 IT | `03-whatsapp/meta-onboarding-checklist.md:26` | 集成工程师（沈思锴） |
| 149 | WhatsApp 消息费的支付 / 经 BSP 接入时，消息费由 Botmaker 代收并加服务费（SOURCES S-B3）；是否还需在 Meta 侧绑卡【待核实】 / 客户财务 | `03-whatsapp/meta-onboarding-checklist.md:29` | 集成工程师（沈思锴） |
| 150 | 材料清单（境内公司为例）【待核实】 | `03-whatsapp/meta-onboarding-checklist.md:43` | 集成工程师（沈思锴） |
| 151 | 由客户管理员在 Meta 商务账户的安全中心发起认证【待核实】，按提示上传材料并选择验证方式（公司域名邮箱、电话或域名验证）。 | `03-whatsapp/meta-onboarding-checklist.md:56` | 集成工程师（沈思锴） |
| 152 | 限制 / 号码当前不能注册在任何 WhatsApp 上 / App 版本不低于 2.24.17；至少每 14 天打开一次 App 否则断连（SOURCES S-B4）；吞吐固定 20 条/秒；阅后即焚、一次性查看、实时位置、广播列表停用；平台侧不支持群聊；部分国家码可能不支持【待核实】（SOURCES S-M7） | `03-whatsapp/meta-onboarding-checklist.md:68` | 集成工程师（沈思锴） |
| 153 | 未在任何 WhatsApp 上注册 / 曾注册过的先在 App 内注销账号再接入；注销后的等待期【待核实】 | `03-whatsapp/meta-onboarding-checklist.md:77` | 集成工程师（沈思锴） |
| 154 | 国家码的选择【待客户确认】 / 权衡三点：目标市场客户对号码的观感；公司能否长期持有并稳定收验证码；境内号码接入的可行性【待核实】 | `03-whatsapp/meta-onboarding-checklist.md:78` | 集成工程师（沈思锴） |
| 155 | 不用临时号码 / 不使用接码平台或来路不明的虚拟号；如用云通信厂商的正规号码，须确认能长期持有并能收验证码【待核实】 | `03-whatsapp/meta-onboarding-checklist.md:79` | 集成工程师（沈思锴） |
| 156 | 该号码的国家码在支持范围内：以接入流程的实际结果为准【待核实】，建议先用一个测试号在试用账号里走一遍（02-botmaker/trial-test-plan.md 的 T-1） | `03-whatsapp/meta-onboarding-checklist.md:86` | 集成工程师（沈思锴） |
| 157 | 规则要点【待核实】： | `03-whatsapp/meta-onboarding-checklist.md:95` | 集成工程师（沈思锴） |
| 158 | 显示名审核与商家认证是两件事：认证过了，显示名仍可能被拒；显示名的修改次数与频率有限制【待核实】。 | `03-whatsapp/meta-onboarding-checklist.md:100` | 集成工程师（沈思锴） |
| 159 | 名称旁的认证徽标需另行申请，条件与流程【待核实】；MVP 不依赖它。 | `03-whatsapp/meta-onboarding-checklist.md:101` | 集成工程师（沈思锴） |
| 160 | 经 Botmaker 嵌入式注册时 PIN 由谁设置、在哪里查看或重置【待核实】，接入当天问清并记录。 | `03-whatsapp/meta-onboarding-checklist.md:106` | 集成工程师（沈思锴） |
| 161 | 遗忘 PIN 的重置流程与等待期【待核实】。 | `03-whatsapp/meta-onboarding-checklist.md:108` | 集成工程师（沈思锴） |
| 162 | 分级的常见口径【待核实】：24 小时内可主动触达的去重客户数按 250、1,000、10,000、100,000、不限逐级提升；完成商家认证、保持质量、用量上来之后自动升级。2025 年下半年起额度改为在商务账户层面共享的说法【待核实】。 | `03-whatsapp/meta-onboarding-checklist.md:113` | 集成工程师（沈思锴） |
| 163 | 质量评级分高、中、低三档，依据近期客户反馈（拉黑、举报）计算；持续为低会被标记、降级甚至限制发送。号码状态有已连接、被标记、受限等【待核实】。 | `03-whatsapp/meta-onboarding-checklist.md:114` | 集成工程师（沈思锴） |
| 164 | 监控：每周在 Botmaker 或 Meta 的 WhatsApp 管理后台看一次质量评级与当前分级【待核实】；也可用 GET /whatsapp/accounts/{number}/status 查询（SOURCES S-B2）。写入 00-client/运维手册.md 的周检项。 | `03-whatsapp/meta-onboarding-checklist.md:117` | 集成工程师（沈思锴） |
| 165 | 认证尚未通过时的退路【待核实】 | `03-whatsapp/meta-onboarding-checklist.md:119` | 集成工程师（沈思锴） |
| 166 | 参考单价（USD / 百万 token，输入 / 输出；为 2026-06-24 的缓存价，开跑前以官网价格页为准【待核实】）：claude-opus-5 5 / 25；claude-sonnet-5 2 / 10；claude-haiku-4-5 1 / 5。其他服务商的单价请查各自官网，不要凭印象填。 | `04-eval/README.md:104` | 集成工程师（沈思锴） |
| 167 | 路线 A（Botmaker 内置 AI Agent）的模型在平台内，无法离线直调；离线评测用来迭代规则与示例，平台内的实际表现以 02-botmaker/trial-test-plan.md 的 20 条样例为准。【待核实】内置模型能否通过同款接口在平台外复现。 | `04-eval/README.md:124` | 集成工程师（沈思锴） |
| 168 | 依据：公开的接口描述文件与帮助中心文章（SOURCES S-B2、S-B5、S-B6、S-B10、S-B11）。未登录、未调用任何真实接口；凡未在一手来源读到的内容均标【待核实】。 | `05-integration/botmaker-api-notes.md:4` | 集成工程师（沈思锴） |
| 169 | Token 权限范围能否收窄（只读、限端点）：未见说明。【待核实】 | `05-integration/botmaker-api-notes.md:23` | 集成工程师（沈思锴） |
| 170 | POST /chats-actions/trigger-intent / 触发某个意图或**发送 WhatsApp 模板**（intentIdOrName 填模板名），可同时设置 variables、tags / 可选（二期的程序化再触达） / 未注明【待核实】 | `05-integration/botmaker-api-notes.md:35` | 集成工程师（沈思锴） |
| 171 | chatReference 有两种写法（接口描述原文）：Botmaker 的 chatId；或 channelId + : + contactId（channelId 从 GET /channels 取，形如 <项目>-whatsapp-<公司号码>；contactId 对 WhatsApp 即客户号码）。webhook 回调里的 cus… | `05-integration/botmaker-api-notes.md:43` | 集成工程师（沈思锴） |
| 172 | Botmaker 对回调失败是否重试、超时多久、是否要求 2xx 以外的特定响应：文章未写。【待核实】服务侧的应对：原文先落盘、处理幂等、同一回调重发直接返回 duplicate，因此无论对方重试与否都安全。 | `05-integration/botmaker-api-notes.md:56` | 集成工程师（沈思锴） |
| 173 | 回调结构（v1.1，【待核实】） | `05-integration/botmaker-api-notes.md:58` | 集成工程师（沈思锴） |
| 174 | 变量名写法**：流程里的会话变量与线索字段同名（下划线）。若平台不接受下划线【待核实】，改用驼峰（b2bType、productInterest），服务两种都认；另接受一个可选的整体 JSON 变量 lead_json，单个变量优先于它。 | `05-integration/botmaker-api-notes.md:70` | 集成工程师（沈思锴） |
| 175 | 变量随哪类回调下发**：示例里 variables 出现在消息回调中。服务对每一条消息回调都重新评估是否需要通知，不依赖"变量一定跟着用户消息来"。【待核实】 | `05-integration/botmaker-api-notes.md:71` | 集成工程师（沈思锴） |
| 176 | 按钮点击的形态**：接口描述里消息内容类型有 button-click 与 selectedButton，回调示例里没有。流程应在按钮动作里直接给变量赋值（如 segment=B2B），服务只认变量，不解析按钮文本。【待核实】 | `05-integration/botmaker-api-notes.md:72` | 集成工程师（沈思锴） |
| 177 | 变量跨会话保留**：Botmaker 的会话变量按联系人保存。流程须在新会话开场（S1_GREETING）把 escalation_flag、escalation_reason 重置，否则老客户再次来访时，第一条消息就会带着上次的升级标记触发一次通知。【待核实】 | `05-integration/botmaker-api-notes.md:73` | 集成工程师（沈思锴） |
| 178 | CTWA referral**：回调示例里没有 referral 字段。服务会在顶层或消息内寻找 referral 对象（sourceType / sourceId / sourceUrl / headline / body / ctwaClid，大小写与下划线不敏感），找到就记入线索并把来源渠道置为 ctwa_ad。【待核实】 | `05-integration/botmaker-api-notes.md:74` | 集成工程师（沈思锴） |
| 179 | 只有 WhatsApp 的 contactId 是号码**：其他渠道（Instagram、Messenger）的回调 MVP 直接跳过（结果为 skipped_no_contact）；二期接私信渠道时沿用"平台客户 ID"去重键即可。WhatsApp 渠道里 contactId 不是号码的客户（只给出业务范围用户标识【待核实】）不跳过：按… | `05-integration/botmaker-api-notes.md:75` | 集成工程师（沈思锴） |
| 180 | 销售在 Botmaker 结束会话时选择结束分类，conversation-close 事件把它带回来，服务据此回写 status。分类名称需要在 Botmaker 后台的结束分类功能中预先建好【待核实】，名称与含义由客户销售确认【待客户确认】。 | `05-integration/botmaker-api-notes.md:79` | 集成工程师（沈思锴） |
| 181 | Token 无效或过期 / 401 或 403【待核实】具体状态码 / 到 Token 生成页重新生成，或用刷新接口；更新部署环境的密钥配置 | `05-integration/botmaker-api-notes.md:97` | 集成工程师（沈思锴） |
| 182 | 我方回调服务不可用 / Botmaker 侧重试策略未知【待核实】 / 健康检查加告警；恢复后用 python -m app.replay 重放已落盘未处理的事件 | `05-integration/botmaker-api-notes.md:104` | 集成工程师（沈思锴） |
| 183 | CTWA referral 是否透传 / 需要真实广告流量；无广告前保持【待核实】 / 集成工程师、客户运营 | `05-integration/botmaker-api-notes.md:115` | 集成工程师（沈思锴） |
| 184 | VPS / 约 6 至 12 USD / 与 03-whatsapp/cost-model-inputs.csv 的 hosting_usd_per_month（低、中档 6 USD，高档 12 USD）一致；具体厂商报价【待核实】 | `05-integration/deployment.md:21` | 集成工程师（沈思锴） |
| 185 | 切换有数秒不可用。Botmaker 对回调失败是否重试尚不清楚【待核实】，所以更新放在咨询低谷（北京时间上午，欧美的深夜）进行；更新后看一眼 /health 与最近日志。表结构用 CREATE TABLE IF NOT EXISTS 建立，线索以 JSON 存放，升级字段不需要迁移脚本。 | `05-integration/deployment.md:142` | 集成工程师（沈思锴） |
| 186 | 所选厂商的实际月费是否落在 6 至 12 USD / 【待核实】 / 集成工程师 | `05-integration/deployment.md:177` | 集成工程师（沈思锴） |
| 187 | Botmaker 回调失败的重试策略（决定更新窗口的宽严） / 【待核实】 / 集成工程师 | `05-integration/deployment.md:178` | 集成工程师（沈思锴） |
| 188 | 假设：回调结构按 Botmaker 帮助中心示例建模（SOURCES S-B6），真实样本到手前标【待核实】；服务部署在境外，见 ../deployment.md；Botmaker API 端点与限流见 ../botmaker-api-notes.md。 | `05-integration/webhook-service/README.md:4` | 集成工程师（沈思锴） |
| 189 | 状态回写 / 坐席消息出现时线索转 contacted；conversation-close 事件里的结束分类（typification）映射为线索状态，映射表见 ../botmaker-api-notes.md 第 6 节。【待核实】 | `05-integration/webhook-service/README.md:29` | 集成工程师（沈思锴） |
| 190 | app/models.py / Botmaker v1.1 回调模型，宽松解析【待核实】 | `05-integration/webhook-service/README.md:38` | 集成工程师（沈思锴） |
| 191 | fixtures/ / 6 个回调样例，顶层 _note 注明结构【待核实】 | `05-integration/webhook-service/README.md:44` | 集成工程师（沈思锴） |
| 192 | BOTMAKER_CHAT_URL_TEMPLATE / （链接见出处） / 卡片上的"接手"链接【待核实】 | `05-integration/webhook-service/README.md:116` | 集成工程师（沈思锴） |
| 193 | 真实回调的字段名与层级是否与 fixture 一致，尤其 contactId、customerId、messages[]._id_、variables。【待核实】 | `05-integration/webhook-service/README.md:137` | 集成工程师（沈思锴） |
| 194 | 按钮点击在回调里的形态，以及变量是随用户消息、Bot 消息还是单独事件下发。【待核实】 | `05-integration/webhook-service/README.md:138` | 集成工程师（沈思锴） |
| 195 | Botmaker 是否接受带下划线的变量名；不接受时用驼峰，服务两种都认。【待核实】 | `05-integration/webhook-service/README.md:139` | 集成工程师（沈思锴） |
| 196 | 回调是否包含分配坐席类事件（assigned-to-agent、queue-set）；没有时线索在首条坐席消息出现时才转 contacted。【待核实】 | `05-integration/webhook-service/README.md:140` | 集成工程师（沈思锴） |
| 197 | Botmaker 对回调失败的重试与超时策略。【待核实】 | `05-integration/webhook-service/README.md:141` | 集成工程师（沈思锴） |
| 198 | CTWA 广告 referral 是否透传进回调。【待核实】 | `05-integration/webhook-service/README.md:142` | 集成工程师（沈思锴） |
| 199 | 卡片链接的实际地址格式（公开接口描述里出现过三种写法）。【待核实】 | `05-integration/webhook-service/README.md:143` | 集成工程师（沈思锴） |
| 200 | 会话变量跨会话保留：流程需在新会话开场时重置 escalation_flag 与 escalation_reason，否则老客户再次来访会在第一条消息就触发一次通知。【待核实】 | `05-integration/webhook-service/README.md:144` | 集成工程师（沈思锴） |
| 201 | contactId 是否永远是号码：Botmaker 的公开接口描述里已出现 BSUID（WhatsApp 的商家范围用户标识）相关字段与事件。若部分客户只给出标识而不给号码，"按号码判国家、按号码去重"对这部分客户不成立。服务的处理：WhatsApp 渠道的回调只要带 customerId，线索照常入库并照常通知销售，去重键改用 bm:… | `05-integration/webhook-service/README.md:145` | 集成工程师（沈思锴） |
| 202 | 【待核实】 The structure follows the example in Botmaker's help centre (SOURCES S-B6) and has | `05-integration/webhook-service/app/models.py:3` | 集成工程师（沈思锴） |
| 203 | referral: dict[str, Any] / None = None                          # 【待核实】 CTWA passthrough | `05-integration/webhook-service/app/models.py:30` | 集成工程师（沈思锴） |
| 204 | referral: dict[str, Any] / None = None                          # 【待核实】 | `05-integration/webhook-service/app/models.py:66` | 集成工程师（沈思锴） |
| 205 | defines the close categories in Botmaker 【待核实】【待客户确认】 (see botmaker-api-notes.md). | `05-integration/webhook-service/app/normalize.py:53` | 集成工程师（沈思锴） |
| 206 | ASSIGNMENT_EVENTS = {"assigned-to-agent", "queue-set"}  # 【待核实】 whether webhooks emit these | `05-integration/webhook-service/app/normalize.py:62` | 集成工程师（沈思锴） |
| 207 | 【待核实】; individual variables win over it. Nullish values are dropped so they can | `05-integration/webhook-service/app/normalize.py:114` | 集成工程师（沈思锴） |
| 208 | Botmaker's API already models as BSUID 【待核实】) being mistaken for a phone number. | `05-integration/webhook-service/app/normalize.py:149` | 集成工程师（沈思锴） |
| 209 | """CTWA ad referral, if Botmaker passes it through 【待核实】 (top level or per message).""" | `05-integration/webhook-service/app/normalize.py:177` | 集成工程师（沈思锴） |
| 210 | 【待核实】 - the lead is still recorded, keyed by Botmaker's customer id, with phone | `05-integration/webhook-service/app/normalize.py:233` | 集成工程师（沈思锴） |
| 211 | "_note": "【待核实】结构依据 Botmaker 帮助中心的 webhook 示例（SOURCES S-B6）整理，尚未用真实回调样本核对；拿到真实样本后替换本文件并同步 app/models.py。号码、姓名、公司均为虚构。 场景：销售在 Botmaker 结束会话并选择结束分类（typification），用于回写线索状态。分… | `05-integration/webhook-service/fixtures/event_conversation_close.json:2` | 集成工程师（沈思锴） |
| 212 | 商家认证状态已知：已通过，或已提交且清楚未通过期间的限制【待核实】 / 后台状态 | `06-acceptance/go-live-checklist.md:14` | 集成工程师（沈思锴） |
| 213 | R04 / **认证延误**：Meta 商家认证与显示名审核是关键路径上唯一不受控的环节 / 中至高 / 高 / 节前提交，不等开工；按清单一次备齐材料；被退回当天处理；退路是以未认证状态先承接入站咨询，其限制【待核实】（S-M8） / 摩兽业务（提交）；集成工程师（材料辅导） / 07-project/timeline.md、03-wh… | `07-project/risk-register.md:13` | 集成工程师（沈思锴） |
| 214 | R16 / **Coexistence 特有问题**：超过 14 天未打开 App 会断开（S-B4）；Bot 与真人在同一号码上可能同时回复；客户号码的国家码可能不在支持范围（S-M7） / 中 / 中 / 仅在确有必要时选 Coexistence；"每 14 天打开 App"写入运营例行事项并指定责任人；试用期验证真人回复后 Bot … | `07-project/risk-register.md:25` | 集成工程师（沈思锴） |
| 215 | 认证未过时的退路：用未认证状态先承接入站咨询（客户先发消息、我们在窗口内回复），同时继续走认证；未认证状态下的主动发送上限与能否正常使用显示名【待核实】，见 03-whatsapp/meta-onboarding-checklist.md。 | `07-project/timeline.md:71` | 集成工程师（沈思锴） |
| 216 | 你之前对客户说的"WhatsApp 可以和 Botmaker 共存"成立**：我核实过，Botmaker 帮助中心有官方的 Coexistence 接入文章。条件：App 版本要够新、至少每 14 天打开一次 App、模板只能从平台发、广播列表会停用；客户号码所属国家是否在支持范围内，要以实际接入结果为准。【待核实】 | `99-internal/zhang-baowen-brief.md:15` | 集成工程师（沈思锴） |
| 217 | "每个号码每月前 1,000 条免费"目前只在服务商文章里看到，Meta 官方页面我没读到，先别对客户承诺。【待核实】 | `99-internal/zhang-baowen-brief.md:22` | 集成工程师（沈思锴） |
| 218 | Botmaker 的 AI 是按 token 另外收费的，单价没公开。【待核实】 | `99-internal/zhang-baowen-brief.md:23` | 集成工程师（沈思锴） |
| 219 | 结论标记：**已复核**＝在一手来源读到原文；**部分复核**＝仅第三方来源一致；**未能复核**＝未找到可靠来源，沿用原数字并标【待核实】；**有更新**＝与开工前掌握的信息不同。 | `SOURCES.md:5` | 集成工程师（沈思锴） |
| 220 | "每号码每月前 1,000 条免费"**只在 BSP 文章里出现**（360dialog、SendPulse），在抓取到的 Meta 官方页面上没有读到（S-M1、S-M3）。 / 成本模型把免费额度做成参数，同时给出 0 条的保守情景。【待核实】 | `SOURCES.md:13` | 集成工程师（沈思锴） |
| 221 | Botmaker 的生成式 AI **按 token 另行计费**，单价未公开；默认模型在帮助中心写作 "GPT-4 Mini"，可按 Bot 或按 Agent 切换（S-B7、S-B8）。 / 路线 A 不是"零模型成本"；成本模型给区间并标【待核实】。 | `SOURCES.md:14` | 集成工程师（沈思锴） |
| 222 | Botmaker webhook 的鉴权头是 auth-bm-token，帮助中心给出了 v1.1 消息回调示例（S-B5、S-B6）；公开 API 描述文件给出了逐端点限流（S-B2）。 / 集成服务的 fixture 按该示例建模；真实样本到手前字段仍标【待核实】。 | `SOURCES.md:15` | 集成工程师（沈思锴） |
| 223 | S-B5 / Webhook 在 Settings > Integrations > Botmaker API 中配置：回调 URL、可选安全 Token（随每次回调放在请求头 auth-bm-token）、渠道选择、消息类型勾选（Bot / 用户 / 坐席消息、消息状态、仅 HSM 状态、事件消息）、"包含变量"开关。重试与超时策略文章… | `SOURCES.md:25` | 集成工程师（沈思锴） |
| 224 | S-B6 / Webhook 回调示例（v1.1 消息）：顶层 v、type（message / event）、chatPlatform、contactId、customerId、sessionId、whatsappNumber、firstName、lastName、chatChannelId、customerCreationTime、s… | `SOURCES.md:26` | 集成工程师（沈思锴） |
| 225 | S-B7 / 生成式 AI 计费：按 token 计，"fixed price per block of 1,000,000 tokens"，单价随模型不同，文章未给数字；每次回复约带最近 20 条消息、指令、知识库命中段落；消耗明细在 Settings > Account > "Products and consumption"。建 A… | `SOURCES.md:27` | 集成工程师（沈思锴） |
| 226 | S-B9 / AI Agent 可按指令把用户信息写入变量，官方示例写法为 "store it in ${fullName}"。是否支持结构化（JSON）输出：文章未提。【待核实】需在试用账号验证（见 02-botmaker/trial-test-plan.md）。 / 部分复核 / （链接见出处） | `SOURCES.md:29` | 集成工程师（沈思锴） |
| 227 | S-B10 / Code Actions：运行时 Node.js v22；外部 HTTP 用内置 rp（request-promise）；单次执行超时 90 秒；单次最多 200 个用户变量、每个变量值最大 100 KB；用 user.set / user.get 读写变量，result.text / result.gotoRule / … | `SOURCES.md:30` | 集成工程师（沈思锴） |
| 228 | S-B12 / CTWA：Botmaker 有 "Click to WhatsApp Dashboards" 功能，会识别来源为广告 referral 的会话；Google Ads 集成文章提到变量 sourceId "与 Meta Ads 的 Referral source ID 同理"。referral 明细（source_url、h… | `SOURCES.md:32` | 集成工程师（沈思锴） |
| 229 | S-B13 / 10/1 之后 Botmaker 如何向客户结算客服消息（是否加 20%、是否计入套餐对话数）：FAQ 仍写"24 小时窗口内消息免费"，属旧口径。【待核实】需向 Botmaker 销售书面确认。 / 未能复核 / （链接见出处） | `SOURCES.md:33` | 集成工程师（沈思锴） |
| 230 | S-B14 / 官网与帮助中心为英/西/葡三语；后台界面语言、发票与合同主体：未找到公开说明。【待核实】 / 未能复核 / 同上 | `SOURCES.md:34` | 集成工程师（沈思锴） |
| 231 | S-B15 / 从中国大陆访问 Botmaker 后台与 API 的稳定性：无法从本机验证。其对外 IP 属 Google Cloud 网段（推断），大陆直连大概率不稳定，需客户现有的合规跨境网络。【待核实】 / 未能复核（推断） / S-B11 | `SOURCES.md:35` | 集成工程师（沈思锴） |
| 232 | S-M3 / "每个号码每月前 1,000 条服务消息免费、按月重置不累计"：360dialog 称出自 Meta 定价文档 2026-08-05 更新；SendPulse 写 "Meta confirmed"；但 S-M1、S-M2 两个官方页面以及 Zendesk、Courier 的公告中均未读到。【待核实】 / 部分复核 / （链接… | `SOURCES.md:43` | 集成工程师（沈思锴） |
| 233 | S-M4 / 费率示例（Meta 基础价，USD/条，不含 BSP 加价）：德国 0.0550、荷兰 0.0500、巴西 0.0068、美国/加拿大 0.0034、印度 0.0014、哥伦比亚 0.0008。德国与巴西两个数字与开工前掌握的一致。法、意、西、英等其余市场**未取得官方数字**，成本模型中相应行标【待核实】。 / 部分复核（… | `SOURCES.md:44` | 集成工程师（沈思锴） |
| 234 | S-M7 / Coexistence 的国家限制：多篇第三方文章称部分国家码的号码不支持（曾列出欧盟/欧洲经济区、英国、印度、日本、韩国、澳大利亚、菲律宾、俄罗斯、土耳其、南非、尼日利亚），但 S-M6 官方页面当前未见该清单。以客户实际号码的国家码在接入流程中的结果为准。【待核实】 / 未能复核 / 第三方文章（respond.io、Y… | `SOURCES.md:47` | 集成工程师（沈思锴） |
| 235 | S-M8 / 账号类通用规则（号码注册在客户自己的商务账户下、接入时收验证码、商家认证、显示名审核、发送量分级与质量评级）：属平台长期规则，本次未逐条重新核对原文；分级的具体数值与"未认证可否先承接入站会话"标【待核实】，见 03-whatsapp/meta-onboarding-checklist.md。 / 未逐条复核 / Meta … | `SOURCES.md:48` | 集成工程师（沈思锴） |
| 236 | AI Agent 能否把抽取字段稳定写入变量；是否支持 JSON 输出 / 能按指令写变量（已复核）；稳定性与 JSON 输出**未能复核**，由试用账号 20 条样例决定路线 A/B。【待核实】 / S-B9 | `SOURCES.md:55` | 集成工程师（沈思锴） |
| 237 | Webhook 事件类型与 payload；CTWA referral 是否透传 / 事件类型与 v1.1 示例已取得（部分复核）；referral 透传**未能复核**。【待核实】 / S-B5、S-B6、S-B12 | `SOURCES.md:56` | 集成工程师（沈思锴） |
| 238 | Code Actions 能否调外部 HTTP、超时与频率 / 能；超时 90 秒（已复核）；频率上限未能复核。【待核实】 / S-B10 | `SOURCES.md:57` | 集成工程师（沈思锴） |
| 239 | Botmaker 侧 10/1 后客服消息的结算方式 / **未能复核**。【待核实】 / S-B13 | `SOURCES.md:58` | 集成工程师（沈思锴） |
| 240 | 界面语言、时区、发票/合同主体 / 时区在接入号码时设置（已复核）；界面语言与发票主体未能复核。【待核实】 / S-B4、S-B14 | `SOURCES.md:59` | 集成工程师（沈思锴） |
| 241 | 中国大陆访问稳定性 / **未能复核**（推断需跨境网络）。【待核实】 / S-B15 | `SOURCES.md:60` | 集成工程师（沈思锴） |
| 242 | FieldSpec("phone", "string (E.164) / null", SRC_SYSTEM, "客户 WhatsApp 号码，统一为 E.164（如 +4915112345678）；客户以用户名联系、平台只给出业务范围用户 ID 时为空【待核实】", label_column=True), | `shared/tromox_lead/fields.py:26` | 集成工程师（沈思锴） |
| 243 | FieldSpec("referral", "object / null", SRC_SYSTEM, "Click-to-WhatsApp 广告 referral（source_id、source_url、headline 等）；是否透传【待核实】"), | `shared/tromox_lead/fields.py:42` | 集成工程师（沈思锴） |
| 244 | """Click-to-WhatsApp ad referral. Whether Botmaker passes it through is 【待核实】.""" | `shared/tromox_lead/schema.py:44` | 集成工程师（沈思锴） |

## 4. 张宝文要定的：商务数字与承诺

负责人：张宝文

| # | 事项 | 出处 | 负责人 |
|---|---|---|---|
| 1 | 标记说明：【待核实】＝平台细节仍在核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝由张宝文最终确定。 | `00-client/培训计划.md:4` | 张宝文 |
| 2 | 假设：日期按《方案书》第 10 节的时间计划，随开工日调整【张宝文确认】；形式为线上会议加屏幕共享，全程录屏【待客户确认】；参训名单【待客户确认】。 | `00-client/培训计划.md:5` | 张宝文 |
| 3 | 新同事入职，可先看录屏与配套文档，由老同事带着做一遍；需要再次安排培训的，按工作量另行报价【张宝文确认】。 | `00-client/培训计划.md:59` | 张宝文 |
| 4 | 标记说明：【待核实】＝平台要求仍在向官方核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝由张宝文最终确定。 | `00-client/客户需提供清单.md:4` | 张宝文 |
| 5 | 假设：正式开工日按 2026-10-12 计【张宝文确认】；"建议负责人"一栏为建议，请摩兽填入实际姓名【待客户确认】。 | `00-client/客户需提供清单.md:5` | 张宝文 |
| 6 | 版本：初稿 v0.1，2026-09-21。全部服务金额由张宝文最终确定；定稿时请替换【张宝文确认】标记并删除本行。 | `00-client/报价单.md:4` | 张宝文 |
| 7 | 标记说明：【待核实】＝平台政策或价格仍在向官方核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝商务数字与承诺由张宝文最终确定。 | `00-client/报价单.md:5` | 张宝文 |
| 8 | 精简版 / 【张宝文确认】 | `00-client/报价单.md:36` | 张宝文 |
| 9 | 完整版 / 【张宝文确认】 | `00-client/报价单.md:37` | 张宝文 |
| 10 | 具体包含多少定制开发、调优多久，待需求过一遍后确定【张宝文确认】。 | `00-client/报价单.md:44` | 张宝文 |
| 11 | 月度包含 / 平台与系统对接的技术调整（每月含一定额度，额度【张宝文确认】）；平台政策、计费规则变化的评估与适配建议；故障排查与恢复；AI 规则的结构性调整；每月一份运行小结 | `00-client/报价单.md:91` | 张宝文 |
| 12 | 金额 / 按月计，【张宝文确认】 | `00-client/报价单.md:95` | 张宝文 |
| 13 | 不购买维护服务时，也可按次支持，按工作量另行报价【张宝文确认】。 | `00-client/报价单.md:97` | 张宝文 |
| 14 | 以上为建议【张宝文确认】。付款期限与逾期处理【张宝文确认】。 | `00-client/报价单.md:107` | 张宝文 |
| 15 | 报价是否含税、发票类型与税率【张宝文确认】。 | `00-client/报价单.md:111` | 张宝文 |
| 16 | 开票主体与开票时点【张宝文确认】。 | `00-client/报价单.md:112` | 张宝文 |
| 17 | 调优期内的话术微调、知识库内容更新、规则小幅修正属于上线初期调整，不另计【张宝文确认】。 | `00-client/报价单.md:119` | 张宝文 |
| 18 | 报价有效期【张宝文确认】。 | `00-client/报价单.md:133` | 张宝文 |
| 19 | 两档项目总包金额、维护服务月费与额度、付款节奏、含税与开票 / 【张宝文确认】 | `00-client/报价单.md:137` | 张宝文 |
| 20 | 版本：初稿 v0.1，2026-09-21。本稿供张宝文修改定稿后转交 Kim；定稿时请删除本行与全部【张宝文确认】标记。 | `00-client/方案书.md:4` | 张宝文 |
| 21 | 假设：正式开工日按 2026-10-12（国庆假期后第一个完整周的周一）计【张宝文确认】；日均咨询量、国家分布、是否投放广告等均未拿到真实数字，文中凡涉及处均为估算。 | `00-client/方案书.md:6` | 张宝文 |
| 22 | 工程师这类外部资源的报价是多少？ / 以"配置档位 + 包含内容"的方式给出，分精简版与完整版两档；金额【张宝文确认】。 / 《报价单》 | `00-client/方案书.md:48` | 张宝文 |
| 23 | 两档配置的差别（语种范围、标签范围、调优周期等）和其他范围外事项见《报价单》。具体包含多少定制开发、调优多久，待需求过一遍后确定【张宝文确认】。 | `00-client/方案书.md:286` | 张宝文 |
| 24 | 验收用数字说话。下列阈值均为建议值【张宝文确认】，详细口径由我方另附验收标准文件。 | `00-client/方案书.md:302` | 张宝文 |
| 25 | 评测集规模 / 用真实历史咨询，由销售标注正确答案 / 不少于 150 条【张宝文确认】 | `00-client/方案书.md:308` | 张宝文 |
| 26 | B 端找得全（主指标） / 100 条真正的 B 端咨询里，AI 至少认出 90 条 / 不低于 90%【张宝文确认】 | `00-client/方案书.md:309` | 张宝文 |
| 27 | B 端找得准 / AI 判为 B 端的咨询里，至少 80% 确实是 B 端 / 不低于 80%【张宝文确认】 | `00-client/方案书.md:310` | 张宝文 |
| 28 | 国家判断准确率 / 有手机号国家码的咨询中，国家判对的比例 / 不低于 95%【张宝文确认】 | `00-client/方案书.md:311` | 张宝文 |
| 29 | 产品需求识别率 / 客户提到的车型被正确识别的比例 / 不低于 85%【张宝文确认】 | `00-client/方案书.md:312` | 张宝文 |
| 30 | 转人工比例 / 需要人工接手的咨询占比，太高说明 AI 没帮上忙 / 不高于 30%【张宝文确认】 | `00-client/方案书.md:313` | 张宝文 |
| 31 | 端到端验收场景 / 20 个场景全部通过，覆盖不少于 3 个语种（精简版为 2 个语种）【张宝文确认】 | `00-client/方案书.md:319` | 张宝文 |
| 32 | B 端线索确认到销售收到通知 / 不超过 60 秒【张宝文确认】 | `00-client/方案书.md:320` | 张宝文 |
| 33 | 第 1 周 / 2026-10-12 至 2026-10-18 / 正式开工【张宝文确认】；开通 Botmaker、接入号码；用历史咨询做离线评测 / 集成工程师 | `00-client/方案书.md:346` | 张宝文 |
| 34 | 项目总包 / 按项目一次性计价，周期约一个月，外加上线初期调整 / 我方 / 【张宝文确认】 | `00-client/方案书.md:363` | 张宝文 |
| 35 | 长期维护（可选） / 调优期结束后按月 / 我方 / 另行报价【张宝文确认】 | `00-client/方案书.md:365` | 张宝文 |
| 36 | 首月维护 / 包含上线初期调整 / 精简版 2 周、完整版 4 周，完整版基本覆盖上线后首月；调优期之后的长期维护另行报价【张宝文确认】 | `00-client/方案书.md:372` | 张宝文 |
| 37 | 按**项目总包**一次性计价，不按时间周期收费。建议分三次付款：开工 30%、上线验收 40%、调优结束 30%【张宝文确认】。需求变更按工作量另行报价。 | `00-client/方案书.md:381` | 张宝文 |
| 38 | 以"配置档位 + 包含内容"的方式给出，分精简版与完整版两档，差别在语种范围、标签范围和调优周期；金额【张宝文确认】，见《报价单》。 | `00-client/方案书.md:385` | 张宝文 |
| 39 | MVP 验证有效后，可以视情况升级，以下均不在第一阶段范围内，费用另行评估【张宝文确认】： | `00-client/方案书.md:445` | 张宝文 |
| 40 | 标记说明：【待核实】＝平台细节仍在核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝商务数字与承诺由张宝文最终确定。 | `00-client/维护服务说明.md:4` | 张宝文 |
| 41 | 项目总包已包含上线初期调整（精简版 2 周，完整版 4 周）。维护服务从调优结束验收之后开始，即精简版 2026-11-22 之后、完整版 2026-12-04 之后，按月计【张宝文确认】。 | `00-client/维护服务说明.md:15` | 张宝文 |
| 42 | 技术调整 / 每月含一定额度【张宝文确认】，用于：调整通知渠道或卡片内容；调整线索字段与标签规则；AI 规则的结构性调整；新增模板并送审；产品目录变更后的配套调整 | `00-client/维护服务说明.md:21` | 张宝文 |
| 43 | 以下为建议【张宝文确认】： | `00-client/维护服务说明.md:40` | 张宝文 |
| 44 | 服务时间：周一至周五 09:00 至 18:00（北京时间），法定节假日除外【张宝文确认】。服务时间之外发生严重故障时的处理方式【张宝文确认】。 | `00-client/维护服务说明.md:48` | 张宝文 |
| 45 | 渠道：项目沟通群或邮件【张宝文确认】。 | `00-client/维护服务说明.md:52` | 张宝文 |
| 46 | 月费 / 【张宝文确认】 | `00-client/维护服务说明.md:67` | 张宝文 |
| 47 | 月度技术调整额度 / 【张宝文确认】 | `00-client/维护服务说明.md:68` | 张宝文 |
| 48 | 起订期与续订方式 / 【张宝文确认】 | `00-client/维护服务说明.md:69` | 张宝文 |
| 49 | 终止通知期 / 【张宝文确认】 | `00-client/维护服务说明.md:70` | 张宝文 |
| 50 | 系统照常运行，运营的日常维护照常进行。遇到需要技术的情况，可以按次支持，按工作量另行报价；按次支持不承诺响应时限【张宝文确认】。 | `00-client/维护服务说明.md:74` | 张宝文 |
| 51 | 决策门**：在 Botmaker 试用账号里跑 20 条样例（02-botmaker/trial-test-plan.md），字段写入成功率不低于 95% 走 A，否则走 B。阈值的机器可读版本在 06-acceptance/thresholds.json（route_a_trial_samples、route_a_variable_wr… | `01-design/adr/0003-ai-route-a-b.md:16` | 张宝文 |
| 52 | 决策门阈值 95% 与样例数 20 / 【张宝文确认】 | `01-design/adr/0003-ai-route-a-b.md:45` | 张宝文 |
| 53 | 门槛 / 不低于 95%（即 140 项中最多错 7 项）走路线 A，否则走路线 B【张宝文确认】 / 06-acceptance/thresholds.json 的 route_a_variable_write_success_min | `02-botmaker/trial-test-plan.md:111` | 张宝文 |
| 54 | 集成服务 / 域名与托管位置： / 客户（托管费属第三方费用，客户直付）；如需代开代管【张宝文确认】 / 集成工程师 / 见 05-integration/deployment.md | `03-whatsapp/meta-onboarding-checklist.md:169` | 张宝文 |
| 55 | 数量 / 真实咨询不少于 150 条，其中 B 端不少于 30 条【张宝文确认】；B 端不足时宁可多翻历史记录补齐，也不要用编造的样本凑数 | `04-eval/labeling-guide.md:10` | 张宝文 |
| 56 | 假设：阈值为集成工程师建议值，**全部需【张宝文确认】**后再写进对客户的承诺；语种范围随报价档位变化。 | `06-acceptance/acceptance-criteria.md:4` | 张宝文 |
| 57 | 评测集：客户历史咨询经标注后的真实数据，**不少于 150 条**【张宝文确认】，其中 B 端不少于 30 条；标注方法见 04-eval/labeling-guide.md。合成数据只用于跑通工具，不计入验收。评测与生产使用同一模型、同一版 prompt。 | `06-acceptance/acceptance-criteria.md:15` | 张宝文 |
| 58 | A1 / B 端召回率（主指标） / ≥ 90%【张宝文确认】 / 标注为 B2B 的样本中，被判为 B2B 的比例。漏掉经销商的代价远高于误判个人，所以召回率优先 | `06-acceptance/acceptance-criteria.md:19` | 张宝文 |
| 59 | A2 / B 端精确率 / ≥ 80%【张宝文确认】 / 被判为 B2B 的样本中，标注确为 B2B 的比例 | `06-acceptance/acceptance-criteria.md:20` | 张宝文 |
| 60 | A3 / 国家准确率 / ≥ 95%【张宝文确认】 / 仅统计有号码前缀的样本；判定国家 = 客户自述国家，没有则取号码国家码 | `06-acceptance/acceptance-criteria.md:21` | 张宝文 |
| 61 | A4 / 产品识别率 / ≥ 85%【张宝文确认】 / 标注了产品的样本中，识别出的产品代码集合与标注完全一致的比例 | `06-acceptance/acceptance-criteria.md:22` | 张宝文 |
| 62 | A5 / 升级率（转人工比例） / ≤ 30%【张宝文确认】 / 被标记需要人工接管的样本比例；B 端字段收集完成后的正常交接也计入 | `06-acceptance/acceptance-criteria.md:23` | 张宝文 |
| 63 | A6 / JSON 解析成功率 / ≥ 98%【张宝文确认】 / 模型输出能被解析并通过字段校验的比例 | `06-acceptance/acceptance-criteria.md:24` | 张宝文 |
| 64 | B1 / uat-test-cases.md 中的 **20 个**端到端场景全部通过 / 20 / 20【张宝文确认】 | `06-acceptance/acceptance-criteria.md:32` | 张宝文 |
| 65 | B2 / 场景覆盖语种 / ≥ 3 个语种（精简版为 2 个）【张宝文确认】 | `06-acceptance/acceptance-criteria.md:33` | 张宝文 |
| 66 | B3 / B 端线索确认到销售收到通知的时延 / ≤ 60 秒【张宝文确认】 | `06-acceptance/acceptance-criteria.md:34` | 张宝文 |
| 67 | 在 Botmaker 试用账号内跑 **20 条**样例（02-botmaker/trial-test-plan.md）：字段写入变量的成功率 **≥ 95%** 走路线 A（内置 AI Agent 抽取），否则走路线 B（外部固定 JSON 调用）。【张宝文确认】 | `06-acceptance/acceptance-criteria.md:41` | 张宝文 |
| 68 | 对月度维护服务有没有需求，还是先自己维护、有事再找？ / 维护服务是否一并报；金额【张宝文确认】 | `07-project/meeting-prep.md:95` | 张宝文 |
| 69 | 假设：第二阶段是否启动、做哪几项，取决于 MVP 调优期结束时的数据；任何金额均【张宝文确认】，本文件不写数字。 | `07-project/phase-2-outline.md:4` | 张宝文 |
| 70 | R07 / **客户数据准备不足**：历史咨询不足 150 条，或没人标注，离线评测失去意义 / 中至高 / 高 / 节前三件事里单列；合成数据只用来跑通工具，不用于验收；样本不足时与张宝文协商调整样本量阈值【张宝文确认】并延长上线后抽查；开工日前未到位则 W1 至 W3 顺延 / 摩兽业务、摩兽销售；张宝文跟进 / 04-eval/la… | `07-project/risk-register.md:16` | 张宝文 |
| 71 | R12 / **需求蔓延**：CRM、经销商评分、私信接入等二期事项挤进 MVP / 高 / 中 / 报价单两档范围写死；范围外事项进二期清单；变更按约定另计，金额【张宝文确认】 / 张宝文 / 00-client/报价单.md、07-project/phase-2-outline.md | `07-project/risk-register.md:21` | 张宝文 |
| 72 | 假设：开工日 2026-10-12（国庆假期后第一个完整周的周一）为假设【张宝文确认】；国庆假期按 2026-10-01 至 2026-10-07 计，以国务院公布为准；调优期按完整版 4 周画，精简版为 2 周（到 2026-11-22）。 | `07-project/timeline.md:4` | 张宝文 |
| 73 | 正式开工（W1） / 假设【张宝文确认】 | `07-project/timeline.md:16` | 张宝文 |
| 74 | 张宝文对客户的总价在 15,000–30,000 CNY 区间内，他的 FDE 时间与利润空间由他自己定。下表只是算术参考。【张宝文确认】 | `99-internal/pricing-internal.md:17` | 张宝文 |
| 75 | 对客户的月度维护价 / 【张宝文确认】，客户版口径见 00-client/维护服务说明.md | `99-internal/pricing-internal.md:35` | 张宝文 |
| 76 | 付款时限 / 每个节点达成后 7 个自然日内付到；客户拖款不影响张宝文按节点付我 / 【张宝文确认】 | `99-internal/pricing-internal.md:45` | 张宝文 |
| 77 | 含税与开票 / 上述数字为不含税到手价；开票主体与税点由谁承担要先说清 / 【张宝文确认】 | `99-internal/pricing-internal.md:46` | 张宝文 |
| 78 | 变更计费 / 范围外需求先书面确认再做，按 1,200 CNY / 人天 / 【张宝文确认】 | `99-internal/pricing-internal.md:47` | 张宝文 |
| 79 | Meta 审核延误 / 日历时间顺延，不算我方违约；调优期从实际上线日起算 / 【张宝文确认】 | `99-internal/pricing-internal.md:48` | 张宝文 |
| 80 | 二期优先 / 第二阶段（他预估约 50,000 CNY，未定）同等条件下优先由我承接 / 【张宝文确认】 | `99-internal/pricing-internal.md:49` | 张宝文 |
| 81 | 案例署名 / 脱敏后可作为我的案例展示；客户名是否可提另行确认 / 【张宝文确认】 | `99-internal/pricing-internal.md:50` | 张宝文 |
| 82 | 全部【张宝文确认】项汇总在 open-questions.md。最靠前的：两档对客价格；验收阈值是否写进合同；维护月费；付款节奏与开票；是否承诺上线日期（建议只承诺"认证通过后 4 周"）。 | `99-internal/zhang-baowen-brief.md:58` | 张宝文 |

## 5. 客户要给的：需摩兽提供或拍板

负责人：客户（经张宝文 / Kim 对接）

| # | 事项 | 出处 | 负责人 |
|---|---|---|---|
| 1 | 标记说明：【待核实】＝平台细节仍在核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝由张宝文最终确定。 | `00-client/培训计划.md:4` | 客户（经张宝文 / Kim 对接） |
| 2 | 假设：日期按《方案书》第 10 节的时间计划，随开工日调整【张宝文确认】；形式为线上会议加屏幕共享，全程录屏【待客户确认】；参训名单【待客户确认】。 | `00-client/培训计划.md:5` | 客户（经张宝文 / Kim 对接） |
| 3 | 标记说明：【待核实】＝平台要求仍在向官方核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝由张宝文最终确定。 | `00-client/客户需提供清单.md:4` | 客户（经张宝文 / Kim 对接） |
| 4 | 假设：正式开工日按 2026-10-12 计【张宝文确认】；"建议负责人"一栏为建议，请摩兽填入实际姓名【待客户确认】。 | `00-client/客户需提供清单.md:5` | 客户（经张宝文 / Kim 对接） |
| 5 | 确定用哪个公司主体做认证【待客户确认】。该主体的法定名称要与 Meta 商务账户里填写的名称、官网上的公司信息一致。 | `00-client/客户需提供清单.md:27` | 客户（经张宝文 / Kim 对接） |
| 6 | 指定一名 Meta 商务账户管理员。如果摩兽已经有投广告用的商务账户，沿用同一个即可【待客户确认】。 | `00-client/客户需提供清单.md:28` | 客户（经张宝文 / Kim 对接） |
| 7 | Botmaker 账号与付款方式 / 平台开在摩兽名下，摩兽为所有者 / 用公司邮箱注册；平台以美元计价、信用卡支付，需要一张可付美元的公司信用卡【待客户确认】 / 运营、财务 | `00-client/客户需提供清单.md:91` | 客户（经张宝文 / Kim 对接） |
| 8 | 两种方式任选其一，选择建议见《方案书》第 6 节；最终选择【待客户确认】。 | `00-client/客户需提供清单.md:106` | 客户（经张宝文 / Kim 对接） |
| 9 | 标记说明：【待核实】＝平台政策或价格仍在向官方核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝商务数字与承诺由张宝文最终确定。 | `00-client/报价单.md:5` | 客户（经张宝文 / Kim 对接） |
| 10 | 具体语种【待客户确认】。不在验收范围内的语种，AI 仍然可以应答，只是不做专门的测试与调优。 | `00-client/报价单.md:42` | 客户（经张宝文 / Kim 对接） |
| 11 | 日均咨询量 / 低 10 个、中 30 个、高 120 个 / 【待客户确认】 | `00-client/报价单.md:76` | 客户（经张宝文 / Kim 对接） |
| 12 | B 端咨询占比 / 10% 至 20% / 【待客户确认】 | `00-client/报价单.md:77` | 客户（经张宝文 / Kim 对接） |
| 13 | 客户国家分布 / 德国 25%、意大利 15%、法国 10%、西班牙 10%、美国 10%、其他 30% / 【待客户确认】 | `00-client/报价单.md:78` | 客户（经张宝文 / Kim 对接） |
| 14 | 从 Click-to-WhatsApp 广告或 Facebook 主页按钮进入的对话占比（这部分 72 小时内免费） / 低 0%、中 20%、高 30% / 【待客户确认】 | `00-client/报价单.md:79` | 客户（经张宝文 / Kim 对接） |
| 15 | 选择精简版还是完整版；具体语种 / 【待客户确认】 | `00-client/报价单.md:138` | 客户（经张宝文 / Kim 对接） |
| 16 | 日均咨询量、国家分布、广告投放占比 / 【待客户确认】 | `00-client/报价单.md:139` | 客户（经张宝文 / Kim 对接） |
| 17 | 现状（根据 Kim 2026-09-18 的描述整理，细节【待客户确认】） | `00-client/方案书.md:52` | 客户（经张宝文 / Kim 对接） |
| 18 | 下面三段对话中的英文，是计划上线的实际话术。花括号内为占位内容，上线前替换；工作时间与答复时限为默认值【待客户确认】。涉及车型参数、价格、质保的内容一律来自摩兽提供的知识库，示例中不编造。 | `00-client/方案书.md:105` | 客户（经张宝文 / Kim 对接） |
| 19 | 通知销售 / 线索卡片发到销售群（飞书或企业微信，【待客户确认】），目标 1 分钟内送达 / 销售第一时间知道 | `00-client/方案书.md:195` | 客户（经张宝文 / Kim 对接） |
| 20 | 建议：MVP 用方式 a 起步；如果现有号码已经是主要对外入口，则选方式 b。也可以先 a 后 b：先用新号把链路跑通，再把老号并入。最终选择【待客户确认】，建议在中秋碰面时确定。 | `00-client/方案书.md:232` | 客户（经张宝文 / Kim 对接） |
| 21 | 隐私 / 开场消息附隐私政策链接【待客户确认】；只收集业务必需的信息；客户要求删除时按流程删除；发到销售群的卡片默认隐藏完整号码。欧盟客户占比较高，建议摩兽法务复核隐私告知与数据存放安排【待客户确认】 | `00-client/方案书.md:263` | 客户（经张宝文 / Kim 对接） |
| 22 | 隐私合规 / 欧盟客户的个人数据有专门要求 / 隐私告知、只收必要信息、删除请求流程；建议法务复核【待客户确认】 | `00-client/方案书.md:439` | 客户（经张宝文 / Kim 对接） |
| 23 | 标记说明：【待核实】＝平台细节仍在核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝商务数字与承诺由张宝文最终确定。 | `00-client/维护服务说明.md:4` | 客户（经张宝文 / Kim 对接） |
| 24 | 假设：Botmaker 后台的具体菜单名称以培训时看到的实际界面为准【待核实】；各指标的目标值为建议值【待客户确认】；审核人为建议分工【待客户确认】。 | `00-client/运维手册.md:5` | 客户（经张宝文 / Kim 对接） |
| 25 | 内容类型 / 建议审核人【待客户确认】 | `00-client/运维手册.md:50` | 客户（经张宝文 / Kim 对接） |
| 26 | 转人工比例 / 线索库 / 建议不高于 30%【待客户确认】 / 偏高说明知识库不够，补 FAQ | `00-client/运维手册.md:132` | 客户（经张宝文 / Kim 对接） |
| 27 | 销售首次响应时间 / Botmaker 数据看板【待核实】 / 工作时间内 B 端线索 2 小时内【待客户确认】 / 反馈给销售负责人 | `00-client/运维手册.md:133` | 客户（经张宝文 / Kim 对接） |
| 28 | 假设：响应时限、周末值班安排、线索分工为建议值【待客户确认】；Botmaker 后台的按钮名称以培训时看到的实际界面为准【待核实】；结束分类的名称为暂定【待核实】【待客户确认】。 | `00-client/销售接手SOP.md:5` | 客户（经张宝文 / Kim 对接） |
| 29 | 谁来接：按销售负责人定的国家或类型分工【待客户确认】。接的人在群里回一句"我接"，避免两个人同时回复。 | `00-client/销售接手SOP.md:43` | 客户（经张宝文 / Kim 对接） |
| 30 | 以下均为建议【待客户确认】： | `00-client/销售接手SOP.md:65` | 客户（经张宝文 / Kim 对接） |
| 31 | 夜间进线时，AI 已经告诉客户"同事将在一个工作日内回复"，并说明了工作时间（默认周一至周五 09:00 至 18:00，北京时间【待客户确认】）。销售要做的就是兑现这句话。 | `00-client/销售接手SOP.md:75` | 客户（经张宝文 / Kim 对接） |
| 32 | 同一位客户同一件事，模板最多发 2 次，两次至少间隔 3 天；两次都没有回复，就把线索状态改为培育或无意向，不再追发【待客户确认】。 | `00-client/销售接手SOP.md:96` | 客户（经张宝文 / Kim 对接） |
| 33 | 结束会话时，在 Botmaker 里选择一个结束分类，系统会据此更新线索库里的状态。名称为暂定【待核实】【待客户确认】。 | `00-client/销售接手SOP.md:102` | 客户（经张宝文 / Kim 对接） |
| 34 | 状态：已采纳方向（2026-09-21）；具体选 a 还是 b 取决于客户现有号码状况【待客户确认】。 | `01-design/adr/0002-number-strategy.md:4` | 客户（经张宝文 / Kim 对接） |
| 35 | 客户现有号码的类型、国家码、持机人，是否已在 WhatsApp Business App 上使用 / 【待客户确认】 | `01-design/adr/0002-number-strategy.md:56` | 客户（经张宝文 / Kim 对接） |
| 36 | 新号用哪个国家的号码、由哪个主体办理 / 【待客户确认】 | `01-design/adr/0002-number-strategy.md:57` | 客户（经张宝文 / Kim 对接） |
| 37 | 客户团队日常用什么表格工具还不知道【待客户确认】。 | `01-design/adr/0004-lead-storage.md:11` | 客户（经张宝文 / Kim 对接） |
| 38 | 备份**：每日把数据库文件与 CSV 复制到客户指定的存储位置【待客户确认】；保留期见 03-whatsapp/compliance.md。 | `01-design/adr/0004-lead-storage.md:19` | 客户（经张宝文 / Kim 对接） |
| 39 | 直接写飞书多维表格 / 销售看着方便；权限现成 / 依赖客户是否用飞书；接口限流与字段变更会反过来约束服务；欧盟客户数据进入境内工具需法务评估【待客户确认】 | `01-design/adr/0004-lead-storage.md:25` | 客户（经张宝文 / Kim 对接） |
| 40 | 客户用哪种表格或协作工具；是否需要同步适配器 / 【待客户确认】 | `01-design/adr/0004-lead-storage.md:41` | 客户（经张宝文 / Kim 对接） |
| 41 | 备份放在哪里、保留多久 / 【待客户确认】 | `01-design/adr/0004-lead-storage.md:42` | 客户（经张宝文 / Kim 对接） |
| 42 | 欧盟客户数据同步到境内工具的合规评估 / 【待客户确认】需法务复核 | `01-design/adr/0004-lead-storage.md:43` | 客户（经张宝文 / Kim 对接） |
| 43 | 状态：已采纳适配器方案（2026-09-21）；具体接哪个工具【待客户确认】。 | `01-design/adr/0005-notification-channel.md:4` | 客户（经张宝文 / Kim 对接） |
| 44 | 销售团队用哪种协作工具、通知发到哪个群 / 【待客户确认】 | `01-design/adr/0005-notification-channel.md:42` | 客户（经张宝文 / Kim 对接） |
| 45 | 是否需要按语种或区域分群通知 / 【待客户确认】 | `01-design/adr/0005-notification-channel.md:43` | 客户（经张宝文 / Kim 对接） |
| 46 | 含欧盟用户信息的通知进入境内协作工具的合规评估 / 【待客户确认】需法务复核 | `01-design/adr/0005-notification-channel.md:45` | 客户（经张宝文 / Kim 对接） |
| 47 | 咨询以英语为主，另有西、德、法、葡等语种（具体语种【待客户确认】），小语种上的分类质量是主要不确定项。 | `01-design/adr/0006-model-selection.md:9` | 客户（经张宝文 / Kim 对接） |
| 48 | 客户主体在中国大陆，另有欧洲服务中心（SOURCES 第 4 节）；由哪个主体签约、付款，决定了哪些模型开得出来【待客户确认】。 | `01-design/adr/0006-model-selection.md:10` | 客户（经张宝文 / Kim 对接） |
| 49 | 主体可开通性 / 高：随 Botmaker 账号开通，无需另签 / 取决于签约主体：境内主体直接签约与付款可能受限，境外主体可行性更高【待客户确认】 / 高：人民币结算、可开票 | `01-design/adr/0006-model-selection.md:27` | 客户（经张宝文 / Kim 对接） |
| 50 | 数据条款 / Botmaker 作为服务商承担；其下游模型方是否用于训练【待核实】 / 需选择有"不用于训练"承诺的商用接口档位，并留存书面依据【待核实】 / 同上；另需评估欧盟用户数据进入境内模型服务的跨境合规【待客户确认】需法务复核 | `01-design/adr/0006-model-selection.md:30` | 客户（经张宝文 / Kim 对接） |
| 51 | 由哪个主体签约与付款 / 【待客户确认】 | `01-design/adr/0006-model-selection.md:55` | 客户（经张宝文 / Kim 对接） |
| 52 | 欧盟用户数据进入境内模型服务的合规评估 / 【待客户确认】需法务复核 | `01-design/adr/0006-model-selection.md:58` | 客户（经张宝文 / Kim 对接） |
| 53 | 销售群通知 / 60 秒内把 B 端线索摘要推给销售；号码默认打码 / 客户现有协作工具【待客户确认】 / 选型见 adr/0005-notification-channel.md | `01-design/architecture.md:128` | 客户（经张宝文 / Kim 对接） |
| 54 | 销售群用哪种协作工具 / 【待客户确认】 | `01-design/architecture.md:179` | 客户（经张宝文 / Kim 对接） |
| 55 | 假设：英文为母版；西、德、法、葡为占位，具体语种【待客户确认】；{privacy_url}、{working_hours}、{sla_b2b}、{sla_general} 为占位符，默认值见第 5 节，均【待客户确认】；话术里不出现任何参数、价格、质保条款。 | `01-design/conversation-flow.md:4` | 客户（经张宝文 / Kim 对接） |
| 56 | 媒体、供应商、求职等与销售无关但与摩兽有关的来访：依据知识库给出对应的公开联系方式（内容【待客户确认】），segment 保持 unknown，随后结束。 | `01-design/conversation-flow.md:134` | 客户（经张宝文 / Kim 对接） |
| 57 | 问题已解决且客户无后续：进 S8_CONSENT（该步骤是否启用【待客户确认】），否则直接结束。 | `01-design/conversation-flow.md:151` | 客户（经张宝文 / Kim 对接） |
| 58 | 触发 / C 端问题已解决；是否启用【待客户确认】 | `01-design/conversation-flow.md:184` | 客户（经张宝文 / Kim 对接） |
| 59 | S1 开场问候与三个按钮 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:219` | 客户（经张宝文 / Kim 对接） |
| 60 | S2 一次问齐 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:220` | 客户（经张宝文 / Kim 对接） |
| 61 | S2 交接话术 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:221` | 客户（经张宝文 / Kim 对接） |
| 62 | S3 C 端接待与三个按钮 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:222` | 客户（经张宝文 / Kim 对接） |
| 63 | S4 其他 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:223` | 客户（经张宝文 / Kim 对接） |
| 64 | S6 一般转人工 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:224` | 客户（经张宝文 / Kim 对接） |
| 65 | S7 非工作时间 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:225` | 客户（经张宝文 / Kim 对接） |
| 66 | S8 营销同意与两个按钮 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:226` | 客户（经张宝文 / Kim 对接） |
| 67 | 话题收口 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:227` | 客户（经张宝文 / Kim 对接） |
| 68 | 价格与质保守卫 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:228` | 客户（经张宝文 / Kim 对接） |
| 69 | 没听懂两次 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:229` | 客户（经张宝文 / Kim 对接） |
| 70 | {privacy_url} / 客户官网隐私政策链接 / 【待客户确认】 | `01-design/conversation-flow.md:237` | 客户（经张宝文 / Kim 对接） |
| 71 | {working_hours} / Monday to Friday, 09:00-18:00 China time (UTC+8) / 【待客户确认】 | `01-design/conversation-flow.md:238` | 客户（经张宝文 / Kim 对接） |
| 72 | {sla_b2b} / one business day / 【待客户确认】 | `01-design/conversation-flow.md:239` | 客户（经张宝文 / Kim 对接） |
| 73 | {sla_general} / one business day / 【待客户确认】 | `01-design/conversation-flow.md:240` | 客户（经张宝文 / Kim 对接） |
| 74 | ai_summary / string / AI 抽取 / 给销售看的一两句话摘要（默认简体中文【待客户确认】） / 是 | `01-design/lead-schema.md:39` | 客户（经张宝文 / Kim 对接） |
| 75 | 产品代码目录：MC10、UKKO、M05、MINO、M03、PESGO（来自官网公开车型名，SOURCES 第 4 节）。现售清单【待客户确认】。 | `01-design/lead-schema.md:90` | 客户（经张宝文 / Kim 对接） |
| 76 | 假设：工作时间、响应时限、结束分类名称均为默认值，【待客户确认】。 | `01-design/routing-rules.md:5` | 客户（经张宝文 / Kim 对接） |
| 77 | 回复语言：客户语言在支持清单内（SUPPORTED_LANGUAGES：en、es、de、fr、pt、it，最终清单【待客户确认】）则跟随；不在清单内用英文作答，并在需要时转人工 | `01-design/routing-rules.md:45` | 客户（经张宝文 / Kim 对接） |
| 78 | 队列 / MVP 设一个销售队列；按语种或区域分队列放到调优期再定【待客户确认】 | `01-design/routing-rules.md:121` | 客户（经张宝文 / Kim 对接） |
| 79 | 结束分类与线索状态的映射（分类名称【待核实】【待客户确认】）： | `01-design/routing-rules.md:126` | 客户（经张宝文 / Kim 对接） |
| 80 | 默认工作时间：周一至周五 09:00 至 18:00，北京时间（UTC+8）【待客户确认】。 | `01-design/routing-rules.md:138` | 客户（经张宝文 / Kim 对接） |
| 81 | 响应时限（全部【待客户确认】）： | `01-design/routing-rules.md:160` | 客户（经张宝文 / Kim 对接） |
| 82 | 同一客户同一咨询，模板最多发 2 次，间隔不少于 3 天；两次都没回就把线索状态记为 nurture 或 closed_lost，不再追发【待客户确认】。（与 02-botmaker/templates/README.md 同一口径。） | `01-design/routing-rules.md:187` | 客户（经张宝文 / Kim 对接） |
| 83 | 假设：{whatsapp_number} 为最终接入的公司号码【待客户确认】；预填文案母版为 Hi Tromox!。 | `01-design/source-tracking.md:5` | 客户（经张宝文 / Kim 对接） |
| 84 | 可选扩展【待客户确认】：面向单一市场的账号可以用当地语言的预填文案（如德语账号用 Hallo Tromox! [IG-2609D]），短码解析不受影响，语言判定还能更早生效。 | `01-design/source-tracking.md:79` | 客户（经张宝文 / Kim 对接） |
| 85 | IG-2609 / Instagram / 主页链接 / 全球 / 常驻 / 2026-09-21 / 【待客户确认】 / 示例行 | `01-design/source-tracking.md:87` | 客户（经张宝文 / Kim 对接） |
| 86 | AD-2609A / Click-to-WhatsApp / 广告组 A / 【待客户确认】 / 【待客户确认】 /  /  / 示例行 | `01-design/source-tracking.md:88` | 客户（经张宝文 / Kim 对接） |
| 87 | 产品 / prod_ / product_interest 中的产品代码小写；目录见 shared/tromox_lead/products.py【待客户确认】 / prod_mc10 /  / 上 | `01-design/tag-taxonomy.md:20` | 客户（经张宝文 / Kim 对接） |
| 88 | 优先级 / prio_ / 规则：B 端且类型为 distributor / importer / fleet 为 high，其余 B 端为 normal；C 端仅在投诉、质保争议、法律、安全类升级时为 high【待客户确认】 / prio_high /  / 上 | `01-design/tag-taxonomy.md:25` | 客户（经张宝文 / Kim 对接） |
| 89 | 假设：支持语种、工作时间、回复时限、隐私政策链接均为默认值【待客户确认】；AI Agent 可用的动作（转人工、跳转流程）与变量写入方式以试用账号实测为准【待核实】（SOURCES S-B9）。 | `02-botmaker/ai-agent-system-prompt.md:5` | 客户（经张宝文 / Kim 对接） |
| 90 | 粘贴前替换占位符：{privacy_url}、{working_hours}、{sla_b2b}、{sla_general}、{safety_line}，取值均【待客户确认】；默认值见 2.8 下方的说明。 | `02-botmaker/ai-agent-system-prompt.md:11` | 客户（经张宝文 / Kim 对接） |
| 91 | 本段待确认：支持语种清单【待客户确认】；精简版只对英语加 1 个主要语种做测试与调优，其余语种 AI 仍会应答但不在验收范围。 | `02-botmaker/ai-agent-system-prompt.md:55` | 客户（经张宝文 / Kim 对接） |
| 92 | {privacy_url} / 客户隐私政策链接 / 【待客户确认】 | `02-botmaker/ai-agent-system-prompt.md:142` | 客户（经张宝文 / Kim 对接） |
| 93 | {safety_line} / If anyone is in danger, please contact your local emergency services first. / 【待客户确认】，建议法务过目 | `02-botmaker/ai-agent-system-prompt.md:143` | 客户（经张宝文 / Kim 对接） |
| 94 | 非英语的机器人回复仅示意"语言跟随客户"，译文上线前须由母语者审核【待客户确认】。 | `02-botmaker/ai-agent-system-prompt.md:277` | 客户（经张宝文 / Kim 对接） |
| 95 | AI / {知识库答案：西班牙的试驾与购买渠道，以西班牙语作答}【待客户确认】 | `02-botmaker/ai-agent-system-prompt.md:355` | 客户（经张宝文 / Kim 对接） |
| 96 | 占位符写法：{…}，填完后删除花括号与【待客户确认】标记。 | `02-botmaker/knowledge-base-template.md:13` | 客户（经张宝文 / Kim 对接） |
| 97 | 字段说明：**ID**（分类前缀 + 序号）、**问题（EN）**、**答案**、**AI 直答**、**负责人**（起草）、**审核人**、**最后更新**。负责人与审核人的具体人选【待客户确认】。 | `02-botmaker/knowledge-base-template.md:18` | 客户（经张宝文 / Kim 对接） |
| 98 | KB-PRD-001 / Which models does Tromox currently offer? / {现售车型清单与一句话定位；车型家族名见 SOURCES 第 4 节，现售清单以客户为准}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:24` | 客户（经张宝文 / Kim 对接） |
| 99 | KB-PRD-002 / What are the main differences between the models? / {各车型面向的人群与用途，不写具体参数或写经确认的公开参数}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:25` | 客户（经张宝文 / Kim 对接） |
| 100 | KB-PRD-003 / How fast can it go and how far on a single charge? / {按车型给出对外口径；无统一口径则引导到官网车型页}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:26` | 客户（经张宝文 / Kim 对接） |
| 101 | KB-PRD-004 / How long does the battery take to charge, and what is its lifespan? / {对外口径}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:27` | 客户（经张宝文 / Kim 对接） |
| 102 | KB-PRD-005 / Do I need a licence to ride it? Can I carry a passenger? / {按国家分条；无把握的国家写"请咨询当地经销商"}【待客户确认】 / 需转人工 / 运营 / 法务或区域负责人 | `02-botmaker/knowledge-base-template.md:28` | 客户（经张宝文 / Kim 对接） |
| 103 | KB-PRD-006 / Is there an app? What can it do? / {对外口径}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:29` | 客户（经张宝文 / Kim 对接） |
| 104 | KB-PRD-007 / Where can I find manuals and specifications? / {官网链接}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:30` | 客户（经张宝文 / Kim 对接） |
| 105 | KB-PRD-008 / What is an e-motorcycle and how does it compare with a petrol one? / {通用科普口径}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:31` | 客户（经张宝文 / Kim 对接） |
| 106 | KB-BUY-001 / Is Tromox available in my country? / {已覆盖国家清单；未覆盖国家的统一说法}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:37` | 客户（经张宝文 / Kim 对接） |
| 107 | KB-BUY-002 / Where can I buy a Tromox? / {按国家分条：经销商查询页或当地总代联系方式}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:38` | 客户（经张宝文 / Kim 对接） |
| 108 | KB-BUY-003 / Can I buy online? / {对外口径}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:39` | 客户（经张宝文 / Kim 对接） |
| 109 | KB-BUY-004 / How much does it cost? / {是否有可对外说的零售指导价；没有则写"价格因国家而异，请联系当地经销商"}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:40` | 客户（经张宝文 / Kim 对接） |
| 110 | KB-BUY-005 / How do I become a Tromox dealer or distributor? / {申请流程的对外说法；AI 会先收集公司、国家、业务类型、意向车型与数量，再转销售} 【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:41` | 客户（经张宝文 / Kim 对接） |
| 111 | KB-BUY-006 / What are the requirements to become a reseller in my country? / {可对外说的基本要求；官网 FAQ 提到希望申请方已有至少 1 年的既有架构，是否沿用由销售确认}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:42` | 客户（经张宝文 / Kim 对接） |
| 112 | KB-BUY-008 / Do you offer fleet, rental or corporate purchase programmes? / {是否有此类合作及对外说法}【待客户确认】 / 需转人工 / 销售 / 销售负责人 | `02-botmaker/knowledge-base-template.md:44` | 客户（经张宝文 / Kim 对接） |
| 113 | KB-BUY-009 / How long does delivery take? / {对外口径；无统一口径则转人工}【待客户确认】 / 需转人工 / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:45` | 客户（经张宝文 / Kim 对接） |
| 114 | KB-AFS-001 / How do I contact Tromox customer support? / {售后联系渠道与受理时间；官网公开的售后邮箱见 SOURCES 第 4 节，是否沿用由客户确认}【待客户确认】 / yes / 运营 / 售后负责人 | `02-botmaker/knowledge-base-template.md:51` | 客户（经张宝文 / Kim 对接） |
| 115 | KB-AFS-002 / What does the warranty cover and for how long? / {可对外说的质保口径，按国家分条；未经审核前保持"需转人工"}【待客户确认】 / 需转人工 / 售后 / 售后负责人与法务 | `02-botmaker/knowledge-base-template.md:52` | 客户（经张宝文 / Kim 对接） |
| 116 | KB-AFS-003 / How do I make a warranty claim? / {报修流程：找谁、要准备什么材料}【待客户确认】 / yes / 售后 / 售后负责人 | `02-botmaker/knowledge-base-template.md:53` | 客户（经张宝文 / Kim 对接） |
| 117 | KB-AFS-005 / How do I maintain my vehicle? / {日常保养要点}【待客户确认】 / yes / 售后 / 售后负责人 | `02-botmaker/knowledge-base-template.md:55` | 客户（经张宝文 / Kim 对接） |
| 118 | KB-AFS-006 / How should I charge and store the battery? / {充电与存放的对外口径}【待客户确认】 / yes / 售后 / 售后负责人 | `02-botmaker/knowledge-base-template.md:56` | 客户（经张宝文 / Kim 对接） |
| 119 | KB-PRT-001 / Where can I buy spare parts? / {按国家分条：经销商或指定渠道}【待客户确认】 / yes / 运营 / 售后负责人 | `02-botmaker/knowledge-base-template.md:64` | 客户（经张宝文 / Kim 对接） |
| 120 | KB-PRT-002 / Can I buy a second or replacement battery? / {对外口径}【待客户确认】 / yes / 运营 / 售后负责人 | `02-botmaker/knowledge-base-template.md:65` | 客户（经张宝文 / Kim 对接） |
| 121 | KB-PRT-003 / Which accessories are available? / {配件清单或官网链接}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:66` | 客户（经张宝文 / Kim 对接） |
| 122 | KB-TRD-001 / Where can I test ride a Tromox? / {按国家分条：可试驾的经销商或预约方式}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:73` | 客户（经张宝文 / Kim 对接） |
| 123 | KB-TRD-002 / Is there a dealer or showroom near me? / {经销商查询页链接；各国经销商名单由客户提供}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:74` | 客户（经张宝文 / Kim 对接） |
| 124 | KB-TRD-003 / Will Tromox be at an upcoming show or event? / {近期展会与活动；无则删除本条}【待客户确认】 / yes / 运营 / 市场负责人 | `02-botmaker/knowledge-base-template.md:75` | 客户（经张宝文 / Kim 对接） |
| 125 | KB-COM-001 / Who is Tromox? Where is the company based? / {公司简介的对外口径}【待客户确认】 / yes / 运营 / 市场负责人 | `02-botmaker/knowledge-base-template.md:81` | 客户（经张宝文 / Kim 对接） |
| 126 | KB-COM-002 / Is Tromox a European brand? / {对外口径}【待客户确认】 / yes / 运营 / 市场负责人 | `02-botmaker/knowledge-base-template.md:82` | 客户（经张宝文 / Kim 对接） |
| 127 | KB-COM-003 / How can I contact Tromox for media, sponsorship or influencer cooperation? / {对外联系渠道；官网公开的媒体邮箱见 SOURCES 第 4 节，是否沿用由客户确认}【待客户确认】 / yes / 运营 / 市场负责人 | `02-botmaker/knowledge-base-template.md:83` | 客户（经张宝文 / Kim 对接） |
| 128 | KB-COM-004 / I am a supplier and want to offer my products or services. / {统一回复口径或指定邮箱}【待客户确认】 / yes / 运营 / 采购或行政 | `02-botmaker/knowledge-base-template.md:84` | 客户（经张宝文 / Kim 对接） |
| 129 | KB-COM-005 / Are you hiring? / {招聘信息入口}【待客户确认】 / yes / 运营 / 人事 | `02-botmaker/knowledge-base-template.md:85` | 客户（经张宝文 / Kim 对接） |
| 130 | KB-COM-006 / How do you use my personal data? How can I have it deleted? / {隐私政策链接与一句话说明}；删除或查询请求一律转人工处理，流程见 03-whatsapp/compliance.md【待客户确认】 / yes（仅限链接与一句话说明） / 运营 / 法务 | `02-botmaker/knowledge-base-template.md:86` | 客户（经张宝文 / Kim 对接） |
| 131 | 现售车型清单与对外卖点 / KB-PRD-001 至 KB-PRD-004 / 【待客户确认】 | `02-botmaker/knowledge-base-template.md:110` | 客户（经张宝文 / Kim 对接） |
| 132 | 各国经销商名单或经销商查询页 / KB-BUY-001、KB-BUY-002、KB-TRD-001、KB-TRD-002、KB-PRT-001 / 【待客户确认】 | `02-botmaker/knowledge-base-template.md:111` | 客户（经张宝文 / Kim 对接） |
| 133 | 可对外说的价格与质保口径 / KB-BUY-004、KB-AFS-002 / 【待客户确认】 | `02-botmaker/knowledge-base-template.md:112` | 客户（经张宝文 / Kim 对接） |
| 134 | 售后受理渠道与时间 / KB-AFS-001、KB-AFS-003 / 【待客户确认】 | `02-botmaker/knowledge-base-template.md:113` | 客户（经张宝文 / Kim 对接） |
| 135 | 隐私政策链接 / KB-COM-006 与开场话术 / 【待客户确认】 | `02-botmaker/knowledge-base-template.md:114` | 客户（经张宝文 / Kim 对接） |
| 136 | 品牌语气要求与禁用词 / 全部条目的措辞 / 【待客户确认】 | `02-botmaker/knowledge-base-template.md:115` | 客户（经张宝文 / Kim 对接） |
| 137 | 权限与交接 / 客户为所有者，各角色权限到位 / 0.5 小时 / 人员名单【待客户确认】 | `02-botmaker/setup-guide.md:29` | 客户（经张宝文 / Kim 对接） |
| 138 | 由客户用企业邮箱注册 Botmaker 账号（开账号免费，附最多 300 个初始对话额度，SOURCES S-B3）。注册邮箱用公共邮箱（如 whatsapp-admin@客户域名）而不是个人邮箱，避免人员变动后账号失联。【待客户确认】 | `02-botmaker/setup-guide.md:35` | 客户（经张宝文 / Kim 对接） |
| 139 | S1_GREETING / 一条带 3 个回复按钮的消息 / 按钮标题不超过 20 个字符，最多 3 个：Dealer/Distributor、Rider or Customer、Other；话术含 AI 身份告知与隐私政策链接 {privacy_url}【待客户确认】；**进入本状态先把变量 escalation_flag 置为 fal… | `02-botmaker/setup-guide.md:113` | 客户（经张宝文 / Kim 对接） |
| 140 | S7_AFTER_HOURS / 工作时间判断：在 Botmaker 后台的营业时间功能中【待核实】配置 {working_hours}【待客户确认】 / 非工作时间转人工时改发夜间话术，AI 继续可答 FAQ | `02-botmaker/setup-guide.md:119` | 客户（经张宝文 / Kim 对接） |
| 141 | S8_CONSENT / 可选步骤【待客户确认】：一条带 2 个按钮的消息 Yes, keep me posted / No, thanks / 写 consent_marketing；只在 C 端对话自然结束时问一次 | `02-botmaker/setup-guide.md:120` | 客户（经张宝文 / Kim 对接） |
| 142 | 发交接话术（工作时间内发 S2 或通用交接话术，非工作时间发夜间话术），其中 {sla_b2b}、{sla_general}、{working_hours} 均【待客户确认】。 | `02-botmaker/setup-guide.md:129` | 客户（经张宝文 / Kim 对接） |
| 143 | 知识库正文以英文为主库；AI 用客户的语言作答。涉及质保、退换、法律的条目，若要用当地语言的固定措辞，单独提供经审核的译文【待客户确认】。 | `02-botmaker/setup-guide.md:159` | 客户（经张宝文 / Kim 对接） |
| 144 | sales_b2b / segment=B2B 的全部转人工 / 海外销售【待客户确认】 / 响应时限见 00-client/销售接手SOP.md | `02-botmaker/setup-guide.md:172` | 客户（经张宝文 / Kim 对接） |
| 145 | support_b2c / C 端售后、质保、投诉、安全类 / 售后或运营【待客户确认】 | `02-botmaker/setup-guide.md:173` | 客户（经张宝文 / Kim 对接） |
| 146 | 销售结束会话时必须选一个结束分类，集成服务据此回写线索状态（事件回调里带 typification，SOURCES S-B6）。分类名【待核实】【待客户确认】： | `02-botmaker/setup-guide.md:195` | 客户（经张宝文 / Kim 对接） |
| 147 | 管理员（备份） / 客户运营负责人（Kim 或其指定的人）【待客户确认】 / 同上 / 避免单点 | `02-botmaker/setup-guide.md:300` | 客户（经张宝文 / Kim 对接） |
| 148 | 坐席 / 海外销售、售后【待客户确认】 / 在所属队列接会话、回消息、结束会话选分类 / Standard 套餐含 10 个坐席（SOURCES S-B3） | `02-botmaker/setup-guide.md:302` | 客户（经张宝文 / Kim 对接） |
| 149 | 假设：三条模板都按 utility（事务通知）类别提交；Meta 可能把它们改判为 marketing（营销）类，费率与发送条件随之变化【待核实】；ES / DE / FR / PT 译文为占位，语种清单与译文均【待客户确认】，须由母语者审核后再提交。 | `02-botmaker/templates/README.md:4` | 客户（经张宝文 / Kim 对接） |
| 150 | 响应时限规则见 00-client/销售接手SOP.md：工作时间内 2 小时首次回复；非工作时间进线的，下一个工作日 10:00（北京时间）前回复；周末无人值班时，周一用模板再触达。时限数值均【待客户确认】。 | `02-botmaker/templates/README.md:21` | 客户（经张宝文 / Kim 对接） |
| 151 | 每个语种单独提交 / 同名模板下按语种各建一份；语言代码（如西语、葡语的地区变体）按目标市场选【待客户确认】 | `02-botmaker/templates/README.md:30` | 客户（经张宝文 / Kim 对接） |
| 152 | 同一客户同一咨询，模板最多发 2 次，间隔不少于 3 天；两次都没回就把线索状态记为 nurture 或 closed_lost，不再追发【待客户确认】。 | `02-botmaker/templates/README.md:54` | 客户（经张宝文 / Kim 对接） |
| 153 | 假设：类别 utility；是否被 Meta 改判为 marketing【待核实】；译文与语种【待客户确认】。 | `02-botmaker/templates/tromox_info_request_v1.md:4` | 客户（经张宝文 / Kim 对接） |
| 154 | es / {ES 译文待定} / 【待客户确认】 | `02-botmaker/templates/tromox_info_request_v1.md:27` | 客户（经张宝文 / Kim 对接） |
| 155 | de / {DE 译文待定} / 【待客户确认】 | `02-botmaker/templates/tromox_info_request_v1.md:28` | 客户（经张宝文 / Kim 对接） |
| 156 | fr / {FR 译文待定} / 【待客户确认】 | `02-botmaker/templates/tromox_info_request_v1.md:29` | 客户（经张宝文 / Kim 对接） |
| 157 | pt / {PT 译文待定} / 【待客户确认】 | `02-botmaker/templates/tromox_info_request_v1.md:30` | 客户（经张宝文 / Kim 对接） |
| 158 | 同一咨询最多发 2 次，间隔不少于 3 天【待客户确认】。 | `02-botmaker/templates/tromox_info_request_v1.md:53` | 客户（经张宝文 / Kim 对接） |
| 159 | 假设：类别 utility；是否被 Meta 改判为 marketing【待核实】；译文与语种【待客户确认】；仅完整版包含本模板。 | `02-botmaker/templates/tromox_support_update_v1.md:4` | 客户（经张宝文 / Kim 对接） |
| 160 | 同一请求最多发 2 次，间隔不少于 3 天【待客户确认】。 | `02-botmaker/templates/tromox_support_update_v1.md:51` | 客户（经张宝文 / Kim 对接） |
| 161 | T-6 / CTWA referral 透传 / 客户有广告账户且同意时，投 1 条最小预算的 Click-to-WhatsApp 测试广告【待客户确认】；否则书面询问 Botmaker 支持。检查回调与变量里是否出现 source_id、source_url、headline 等 / 得到"透传 / 不透传 / 仅后台看板可见"三选一的… | `02-botmaker/trial-test-plan.md:42` | 客户（经张宝文 / Kim 对接） |
| 162 | 语种分布：EN 8、DE 3、ES 3、FR 3、PT 2、IT 1。最终语种清单【待客户确认】后，把不在范围内的语种样例换成范围内的。 | `02-botmaker/trial-test-plan.md:80` | 客户（经张宝文 / Kim 对接） |
| 163 | T-6 如需投测试广告，费用由客户广告账户承担，投放前征得客户同意【待客户确认】。 | `02-botmaker/trial-test-plan.md:150` | 客户（经张宝文 / Kim 对接） |
| 164 | 假设：本文件是工程侧的合规设计说明，**不是法律意见**；欧盟隐私要求只写到"基本做法"的深度；客户以哪个主体作为数据责任方尚未确定【待客户确认】。平台条款引用见 SOURCES S-M5，未逐条核对的平台规则见 SOURCES S-M8。 | `03-whatsapp/compliance.md:4` | 客户（经张宝文 / Kim 对接） |
| 165 | 与提供方之间有数据处理协议 / 客户作为业务方"聘用 AI 提供方作为第三方服务商"，需要相应的数据处理条款 / 【待客户确认】由哪一方签 | `03-whatsapp/compliance.md:39` | 客户（经张宝文 / Kim 对接） |
| 166 | 营销类消息必须有明确的事先同意**：MVP 不发营销消息。流程里的同意步骤（S8，可选【待客户确认】）只是把同意记录进线索字段 consent_marketing，为第二阶段的主动再触达做准备；没有记录同意的客户，第二阶段也不得群发。 | `03-whatsapp/compliance.md:51` | 客户（经张宝文 / Kim 对接） |
| 167 | 数据控制者 / 摩兽的某个主体【待客户确认】 / 决定处理目的与方式；若以欧洲主体面向欧盟客户，责任关系更直接 | `03-whatsapp/compliance.md:64` | 客户（经张宝文 / Kim 对接） |
| 168 | 隐私告知 / 开场话术内放隐私政策链接 {privacy_url}；隐私政策需补充：通过 WhatsApp 处理咨询、使用 AI 助手、处理目的、保存期限、权利行使方式、联系人 / 【待客户确认】隐私政策由客户法务更新 | `03-whatsapp/compliance.md:72` | 客户（经张宝文 / Kim 对接） |
| 169 | 处理依据 / 回应咨询：基于客户请求的前期沟通或正当利益；营销：单独同意（第 2 节） / 【待客户确认】法务定性 | `03-whatsapp/compliance.md:74` | 客户（经张宝文 / Kim 对接） |
| 170 | 访问与删除请求 / 见 3.3 / 已设计，时限【待客户确认】 | `03-whatsapp/compliance.md:76` | 客户（经张宝文 / Kim 对接） |
| 171 | 跨境传输 / 见 3.4 / 【待客户确认】法务评估 | `03-whatsapp/compliance.md:77` | 客户（经张宝文 / Kim 对接） |
| 172 | 运营在 1 个工作日内登记到请求台账；法定答复期限通常为一个月【待核实】，内部目标 10 个工作日内完成【待客户确认】。 | `03-whatsapp/compliance.md:82` | 客户（经张宝文 / Kim 对接） |
| 173 | 集成服务与线索库 / 线索字段、原始回调事件 / 境外小型 VPS；面向欧盟客户时优先选欧盟区域【待客户确认】 / 05-integration/deployment.md | `03-whatsapp/compliance.md:94` | 客户（经张宝文 / Kim 对接） |
| 174 | 销售群通知（飞书或企业微信） / 线索摘要；号码默认只显示后四位 / 中国境内 / **这是一次向中国的跨境传输**：靠打码与最小化降低风险，是否还需标准合同条款等传输机制由法务评估【待客户确认】 | `03-whatsapp/compliance.md:95` | 客户（经张宝文 / Kim 对接） |
| 175 | 境内主体处理境外个人信息时，国内个人信息保护方面的要求同样需要法务一并评估【待客户确认】。 | `03-whatsapp/compliance.md:98` | 客户（经张宝文 / Kim 对接） |
| 176 | 数据保留（建议值，均【待客户确认】） | `03-whatsapp/compliance.md:100` | 客户（经张宝文 / Kim 对接） |
| 177 | 提示法务复核的清单【待客户确认】 | `03-whatsapp/compliance.md:123` | 客户（经张宝文 / Kim 对接） |
| 178 | daily_inquiries,10,30,120,个/天,【待客户确认】,日均新咨询数；月对话数 = 日均 x 30 | `03-whatsapp/cost-model-inputs.csv:2` | 客户（经张宝文 / Kim 对接） |
| 179 | b2b_share,0.10,0.15,0.20,比例,【待客户确认】,B 端咨询占比 | `03-whatsapp/cost-model-inputs.csv:3` | 客户（经张宝文 / Kim 对接） |
| 180 | ctwa_share,0.00,0.20,0.30,比例,【待客户确认】,经 Click-to-WhatsApp 广告或 Facebook 主页按钮进入的对话占比（72 小时免费） | `03-whatsapp/cost-model-inputs.csv:9` | 客户（经张宝文 / Kim 对接） |
| 181 | cost-model-inputs.csv / 低/中/高三档的全部输入，含状态列（假设 / 【待核实】 / 【待客户确认】 / 已复核） / 是 | `03-whatsapp/cost-model.md:14` | 客户（经张宝文 / Kim 对接） |
| 182 | 假设：客户已有运营 Facebook / Instagram 的商务账户【待客户确认】；Meta 的认证材料要求、分级数值等属平台通用规则，本次未逐条重新核对原文（SOURCES S-M8），凡带数字或具体要求处均标【待核实】，以提交时 Meta 后台的提示为准。 | `03-whatsapp/meta-onboarding-checklist.md:4` | 客户（经张宝文 / Kim 对接） |
| 183 | 是否已有商务账户 / 沿用现有的（运营 Facebook 主页与 Instagram 的那个），不新建重复账户；重复账户是认证被拒的常见原因 / 客户 / 【待客户确认】 | `03-whatsapp/meta-onboarding-checklist.md:23` | 客户（经张宝文 / Kim 对接） |
| 184 | 管理员 / 至少 2 名客户员工为管理员，用本人实名 Facebook 账号，开启两步验证；不使用共用或新注册的空白账号 / 客户 / 【待客户确认】 | `03-whatsapp/meta-onboarding-checklist.md:24` | 客户（经张宝文 / Kim 对接） |
| 185 | 先定用哪个主体【待客户确认】 | `03-whatsapp/meta-onboarding-checklist.md:33` | 客户（经张宝文 / Kim 对接） |
| 186 | 国家码的选择【待客户确认】 / 权衡三点：目标市场客户对号码的观感；公司能否长期持有并稳定收验证码；境内号码接入的可行性【待核实】 | `03-whatsapp/meta-onboarding-checklist.md:78` | 客户（经张宝文 / Kim 对接） |
| 187 | 必须与企业或品牌有明确关系，并与官网、社媒上的对外名称一致；建议直接用 Tromox【待客户确认】。 | `03-whatsapp/meta-onboarding-checklist.md:97` | 客户（经张宝文 / Kim 对接） |
| 188 | 保留期限 / 验收结束后按客户制度删除或归档【待客户确认】 | `04-eval/labeling-guide.md:33` | 客户（经张宝文 / Kim 对接） |
| 189 | 历史记录里有欧盟等地区居民的个人信息，导出与使用前请按 03-whatsapp/compliance.md 的要求确认合规依据【待客户确认】。 | `04-eval/labeling-guide.md:35` | 客户（经张宝文 / Kim 对接） |
| 190 | product_interest / 客户点名的车型，用产品代码、分号分隔：MC10;UKKO；代码目录 MC10、UKKO、M05、MINO、M03、PESGO【待客户确认】；没点名留空 / 运营 | `04-eval/labeling-guide.md:50` | 客户（经张宝文 / Kim 对接） |
| 191 | 请销售负责人在中秋碰面前后填好；is_valid_lead 一列按此判断，第二阶段的经销商评分也以此为起点。表中"摩兽的标准"一列全部【待客户确认】。 | `04-eval/labeling-guide.md:130` | 客户（经张宝文 / Kim 对接） |
| 192 | 主体 / 哪些类型算有效：门店、分销商、进口商、车队/租赁、线上转售、企业团购？哪些不算？ / 【待客户确认】 | `04-eval/labeling-guide.md:134` | 客户（经张宝文 / Kim 对接） |
| 193 | 市场 / 重点国家与区域；已有独家代理、暂不开放的国家 / 【待客户确认】 | `04-eval/labeling-guide.md:135` | 客户（经张宝文 / Kim 对接） |
| 194 | 经营基础 / 是否要求已有实体门店或团队、经营年限（官网对外写的是希望申请方已有至少 1 年的既有架构） / 【待客户确认】 | `04-eval/labeling-guide.md:136` | 客户（经张宝文 / Kim 对接） |
| 195 | 现有业务 / 是否要求有两轮或电动车经验；在售竞品是否影响判断 / 【待客户确认】 | `04-eval/labeling-guide.md:137` | 客户（经张宝文 / Kim 对接） |
| 196 | 采购规模 / 首单与年采购量的最低预期；低于多少按个人或团购处理 / 【待客户确认】 | `04-eval/labeling-guide.md:138` | 客户（经张宝文 / Kim 对接） |
| 197 | 资质能力 / 进口、认证、售后维修能力是否为必要条件 / 【待客户确认】 | `04-eval/labeling-guide.md:139` | 客户（经张宝文 / Kim 对接） |
| 198 | 联系人 / 需要对方提供哪些信息才值得销售跟进：公司名、职位、官网、邮箱等 / 【待客户确认】 | `04-eval/labeling-guide.md:140` | 客户（经张宝文 / Kim 对接） |
| 199 | 直接排除 / 明确不跟进的情形：个人代购、只要样车、要求寄售等 / 【待客户确认】 | `04-eval/labeling-guide.md:141` | 客户（经张宝文 / Kim 对接） |
| 200 | 优先级 / 什么样的线索要当天处理 / 【待客户确认】 | `04-eval/labeling-guide.md:142` | 客户（经张宝文 / Kim 对接） |
| 201 | 销售在 Botmaker 结束会话时选择结束分类，conversation-close 事件把它带回来，服务据此回写 status。分类名称需要在 Botmaker 后台的结束分类功能中预先建好【待核实】，名称与含义由客户销售确认【待客户确认】。 | `05-integration/botmaker-api-notes.md:79` | 客户（经张宝文 / Kim 对接） |
| 202 | 假设：日均咨询在成本模型的低到高档之间（单机足够）；服务器账号、域名解析都开在客户名下；服务器放在中国大陆以外，保证 Botmaker 能稳定回调；具体云厂商与机房【待客户确认】。 | `05-integration/deployment.md:4` | 客户（经张宝文 / Kim 对接） |
| 203 | 线索库里有个人数据：号码、姓名、公司、对话摘要。客户多在欧洲时，机房优先选欧洲经济区内，并与云厂商签数据处理协议；选其他地区前请客户法务确认。【待客户确认】 | `05-integration/deployment.md:146` | 客户（经张宝文 / Kim 对接） |
| 204 | 云厂商、机房地区、由谁开账号 / 【待客户确认】 / 客户、张宝文 | `05-integration/deployment.md:175` | 客户（经张宝文 / Kim 对接） |
| 205 | 子域名与 DNS 解析由谁操作 / 【待客户确认】 / 客户 | `05-integration/deployment.md:176` | 客户（经张宝文 / Kim 对接） |
| 206 | 通知渠道用飞书还是企业微信 / 【待客户确认】 / 客户销售 | `05-integration/deployment.md:179` | 客户（经张宝文 / Kim 对接） |
| 207 | defines the close categories in Botmaker 【待核实】【待客户确认】 (see botmaker-api-notes.md). | `05-integration/webhook-service/app/normalize.py:53` | 客户（经张宝文 / Kim 对接） |
| 208 | "_note": "【待核实】结构依据 Botmaker 帮助中心的 webhook 示例（SOURCES S-B6）整理，尚未用真实回调样本核对；拿到真实样本后替换本文件并同步 app/models.py。号码、姓名、公司均为虚构。 场景：销售在 Botmaker 结束会话并选择结束分类（typification），用于回写线索状态。分… | `05-integration/webhook-service/fixtures/event_conversation_close.json:2` | 客户（经张宝文 / Kim 对接） |
| 209 | 假设：在测试号或灰度入口上执行；测试人用自己的手机号，语种列为完整版的安排；精简版只保留 2 个语种，此处以英语加德语为例，第二语种【待客户确认】；示例里的公司与人名均为虚构；用例不涉及任何参数、价格、质保条款的具体内容。 | `06-acceptance/uat-test-cases.md:4` | 客户（经张宝文 / Kim 对接） |
| 210 | U19 / 营销同意步骤 / DE / C 端问题解决后出现同意询问；会话一按 "Yes, keep me posted"，会话二按 "No, thanks" / 会话一 consent_marketing true；会话二 false；未询问的其他线索为空 / 记录后结束会话 / 无卡片 / 三种取值都正确；该步骤是否启用【待客户确认】… | `06-acceptance/uat-test-cases.md:36` | 客户（经张宝文 / Kim 对接） |
| 211 | 德语 DE / U02、U06、U19、U20 / 保留（以德语为例，第二语种【待客户确认】） | `06-acceptance/uat-test-cases.md:65` | 客户（经张宝文 / Kim 对接） |
| 212 | 假设：碰面约 2 小时；对方到场的有 Kim（海外社媒运营）、至少一位销售负责人，最好有一位能拍板账号与付款的领导【待客户确认】。 | `07-project/meeting-prep.md:4` | 客户（经张宝文 / Kim 对接） |
| 213 | 假设：摩兽业务/FDE 一方以 Kim 为对接人；摩兽销售由销售主管代表【待客户确认】；工作项与周次对应 timeline.md。 | `07-project/raci.md:5` | 客户（经张宝文 / Kim 对接） |
| 214 | R10 / **隐私合规**：客户中有欧盟用户；线索与通知会进入境内协作工具 / 中 / 高 / 开场即告知 AI 身份与隐私政策链接；只存业务必需字段；通知里号码打码；删除请求有流程；数据保留期限与跨境安排提交客户法务复核【待客户确认】 / 摩兽业务（法务对接）；集成工程师（技术措施） / 03-whatsapp/compliance.… | `07-project/risk-register.md:19` | 客户（经张宝文 / Kim 对接） |
| 215 | 代写 FAQ 内容与专业翻译（Bot 话术的多语种版本由 AI 初译、客户审校）。【待客户确认】 | `99-internal/pricing-internal.md:55` | 客户（经张宝文 / Kim 对接） |
| 216 | 车型名称（家族） / MC10（含 TrailX、StreetX）、UKKO（含 Ukko S+、UkkoPro）、M05、MINO（含 Mino B）、M03、Pesgo（含 Plus、C）。现售清单以客户提供为准【待客户确认】。 / （链接见出处） ； （链接见出处） | `SOURCES.md:68` | 客户（经张宝文 / Kim 对接） |
| 217 | 市场与网络 / 官网 FAQ 提到中国、意大利、欧洲、日本、韩国、澳大利亚、北美；另有美国站、南非站、菲律宾经销商站；欧洲站有 "Dealer Partnership Program" 与 "EU Warehouse Support"；总部杭州，欧洲服务中心在比利时鲁汶。各国经销商名单【待客户确认】。 / 同上；搜索结果中的 tromox… | `SOURCES.md:69` | 客户（经张宝文 / Kim 对接） |
| 218 | 经销申请 / 官网设经销商/分销商申请表单；FAQ 写明希望申请方"已有至少 1 年的既有架构"、有二级网络更佳。有效线索标准以销售填写的为准【待客户确认】。 / （链接见出处） | `SOURCES.md:70` | 客户（经张宝文 / Kim 对接） |
| 219 | ISO 639-1 codes the MVP bot is expected to handle. Final list is 【待客户确认】. | `shared/tromox_lead/enums.py:92` | 客户（经张宝文 / Kim 对接） |
| 220 | FieldSpec("ai_summary", "string", SRC_AI, "给销售看的一两句话摘要（默认简体中文【待客户确认】）", ai_extracted=True), | `shared/tromox_lead/fields.py:45` | 客户（经张宝文 / Kim 对接） |
| 221 | line-up must be confirmed by the client 【待客户确认】. | `shared/tromox_lead/products.py:5` | 客户（经张宝文 / Kim 对接） |
