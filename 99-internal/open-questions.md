# 待决问题汇总（内部）

> 用途：全仓库所有【待核实】【待客户确认】【张宝文确认】的汇总，按负责人分组；每条都有负责人与出处。读者：沈思锴、张宝文。**内部文件，不进客户文档。**
> 第 1 节为人工整理的重点清单；第 2 节起由 `scripts/collect_open_questions.py` 自动生成，请勿手改，改完文档后重跑脚本。

## 1. 重点清单（人工整理，按负责人分组）

### 1.1 我要做的（集成工程师 沈思锴）

2026-09-22 二次核实已解决原第 6、7、8 条："每号码每月 1,000 条免费"由 Meta 官方确认（SOURCES S-M3）；法、意、西等市场官方费率已填入成本模型（S-M4）；未认证可无上限回复入站会话、分级现行数值已核实（S-M8、S-M10）。要书面问 Botmaker 的问题已合并成一份清单：`02-botmaker/botmaker-sales-questions.md`。

| # | 事项 | 怎么核实 | 影响什么 | 期限 |
|---|---|---|---|---|
| 1 | Botmaker 内置 AI Agent 把抽取字段写入变量是否稳定、能否固定输出 JSON | 试用账号跑 20 条样例，`02-botmaker/trial-test-plan.md` | 路线 A / B 决策（`01-design/adr/0003-ai-route-a-b.md`）；走 B 加 1 人天 | 2026-10-16 |
| 2 | 新账号是 Botmaker 3.0 还是经典界面；3.0 版默认模型 "Open AI 5.4" 且暂不能换（SOURCES S-B8），离线评测能否与生产用同一模型 | 试用账号开通当天看界面与 Account 页的模型名；同时书面问 | 路线 A 的"同一模型"前提；ADR 0006 选型 | 开工前 |
| 3 | 真实 webhook 回调样本、单条失败的重试策略、`whatsappReferral` 字段是否真的出现 | 试用账号把回调指到测试部署；故意返回 500 观察 | `05-integration` 的 fixture 与归一化；来源追踪（S-B5、S-B12） | W1 |
| 4 | 每条 WhatsApp 线路的"Central 转接"已关闭，机器人在 WhatsApp 上正常回复（S-B16，10/1 起默认开启） | 试用账号接入线路后立刻检查并关闭；上线前逐线路复查 | 机器人是否在 WhatsApp 上静默 | W1 起每次接线路 |
| 5 | 10/1 之后 Botmaker 如何结算客服消息（是否加价、是否计入套餐对话数）；超量单价 0.07 还是 0.025 USD；DAILY USER 计数口径 | 书面问 Botmaker 销售 | 成本模型 `bsp_markup_service`、套餐费（S-B3、S-B13） | 开工前 |
| 6 | webhook 附加功能的单价与开通方式 | 书面问 Botmaker 销售 | 报价单第三方费用多一项（S-B5） | 开工前 |
| 7 | Botmaker AI token 单价与可选模型清单 | 后台 Settings > Account > Products and consumption，或问销售 | 成本模型 `botmaker_ai_usd_per_1m_tokens`；模型选型（S-B7、S-B8） | 开工前 |
| 8 | AI 数据条款：AI Agent 对话是否用于训练、OpenAI 侧是否不训练、能否签 DPA、子处理方清单；Co-pilot 训练条款与 WhatsApp 条款的冲突 | 书面问 Botmaker；拿到书面答复前不启用 Co-pilot | ADR 0006 一票否决项；合规（S-B17、S-M5） | 开工前 |
| 9 | 经 Botmaker 接入时，Meta 要求 9/30 前绑定的支付方式由谁绑定 | 书面问 Botmaker | 10/1 起超出免费额度的服务消息会不会停投（S-M9） | 接入前 |
| 10 | 客户号码走 Coexistence 时能否接入：国家限制已取消，仅 +86 号码官方未点名 | 在接入流程里实测（仅选方式 b 且用 +86 号时） | 号码策略（`01-design/adr/0002-number-strategy.md`，S-M7） | W1 |
| 11 | 从中国大陆访问 Botmaker 后台与 API 是否稳定 | 请客户在办公网络实测登录与坐席界面 | 销售能否正常接手；是否改用 Coexistence 手机端回复 | W0 |
| 12 | 变量名是否允许下划线、是否区分大小写（S-B18：空格、连字符、星号已知不允许） | 试用账号建 `b2b_type`、`B2B_Type` 等 | 不允许下划线时全仓字段名要改（`shared/tromox_lead/`） | W1 |
| 13 | 再触达模板是否会被 Meta 归为 marketing 类 | W2 第一天提交审核看结果 | 模板单价与话术 | W2 |
| 14 | 非拉美主体能否由 Botmaker 开票、发票抬头与税务（主体与界面语言已查明：BOTMAKER INC 或阿根廷、巴西关联公司；界面英西葡法，无中文，S-B14） | 问销售 | 客户财务流程；运营培训用哪种语言界面 | 开工前 |

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
| 【待核实】 | 集成工程师（沈思锴） | 267 |
| 【张宝文确认】 | 张宝文 | 85 |
| 【待客户确认】 | 客户（经张宝文 / Kim 对接） | 229 |

## 3. 我要做的：平台、政策、价格类事实核实

负责人：集成工程师（沈思锴）

| # | 事项 | 出处 | 负责人 |
|---|---|---|---|
| 1 | 标记说明：【待核实】＝平台细节仍在核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝由张宝文最终确定。 | `00-client/培训计划.md:4` | 集成工程师（沈思锴） |
| 2 | 标记说明：【待核实】＝平台要求仍在向官方核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝由张宝文最终确定。 | `00-client/客户需提供清单.md:4` | 集成工程师（沈思锴） |
| 3 | 备齐下表材料，在 Meta 商务管理平台的商家认证功能中提交【待核实】。 | `00-client/客户需提供清单.md:29` | 集成工程师（沈思锴） |
| 4 | 具体材料以 Meta 后台的提示为准【待核实】。 | `00-client/客户需提供清单.md:40` | 集成工程师（沈思锴） |
| 5 | Botmaker 账号与付款方式 / 平台开在摩兽名下，摩兽为所有者 / 用公司邮箱注册；平台以美元计价、信用卡支付，需要一张可付美元的公司信用卡【待客户确认】。接入号码时可能还要在 Meta 侧为 WhatsApp 消息费登记同一张卡：Meta 规定没有登记付款方式的账户，每个号码每月的免费消息额度用完后，回复客户的消息将无法送达；是否… | `00-client/客户需提供清单.md:91` | 集成工程师（沈思锴） |
| 6 | 号码要求 / 以公司名义办理；能接收短信或语音验证码；没有在 WhatsApp 上注册过，注册过需先注销；手机号或固定电话均可【待核实】 / 已在 WhatsApp Business App 上使用；App 版本 2.24.17 及以上；Meta 已取消此前的国家限制，中国大陆号码以实际接入结果为准【待核实】 | `00-client/客户需提供清单.md:110` | 集成工程师（沈思锴） |
| 7 | 标记说明：【待核实】＝平台政策或价格仍在向官方核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝商务数字与承诺由张宝文最终确定。 | `00-client/报价单.md:5` | 集成工程师（沈思锴） |
| 8 | 下表为估算【待核实】，单位除注明外为 USD/月。摩兽直接向平台开户付款，我方不经手。 | `00-client/报价单.md:57` | 集成工程师（沈思锴） |
| 9 | Botmaker 套餐 / Botmaker / 149 / 149 / 191 / Standard 套餐 149 USD/月，含 3,000 个对话、10 个坐席；超出部分按 Botmaker 官网定价页每个对话 0.07 USD 估算，平台两处公开说法不一致，以书面确认为准【待核实】 | `00-client/报价单.md:61` | 集成工程师（沈思锴） |
| 10 | WhatsApp 消息费 / Meta，经 Botmaker 结算 / 20 / 140 / 950 / 2026-10-01 起窗口内回复按条计费，单价按 Meta 官方费率卡、随客户所在国家变化；每个号码每月前 1,000 条免费；Botmaker 加收的服务费比例【待核实】 | `00-client/报价单.md:62` | 集成工程师（沈思锴） |
| 11 | AI 用量费 / Botmaker / 不足 10 / 50 / 680 / 按 AI 处理的文字量计费；单价未公开【待核实】 | `00-client/报价单.md:63` | 集成工程师（沈思锴） |
| 12 | 线索回传接口（webhook）附加功能 / Botmaker / 未公开 / 未公开 / 未公开 / 把线索实时推送到线索库与销售群要用到这项功能；Botmaker 列为额外付费项，单价未公开【待核实】，未计入下方合计 | `00-client/报价单.md:65` | 集成工程师（沈思锴） |
| 13 | 第三方费用由平台直接向摩兽出具账单，以美元计价、信用卡支付；平台能否提供符合摩兽财务要求的发票【待核实】。 | `00-client/报价单.md:114` | 集成工程师（沈思锴） |
| 14 | Botmaker 对窗口内回复的结算方式（是否加收服务费、Meta 每月 1,000 条免费额度如何体现）、AI 用量单价、套餐超量单价、线索回传接口附加功能的单价 / 【待核实】 | `00-client/报价单.md:141` | 集成工程师（沈思锴） |
| 15 | 需要注意 / 号码要能接收短信或语音验证码，且没有在 WhatsApp 上注册过（注册过需先注销）；社媒入口的链接要换成新号 / App 版本需 2.24.17 及以上；接入当天持机人要在场扫码；之后至少每 14 天打开一次 App，否则连接会断开；模板消息只能从平台发送；广播列表停用，一对一聊天中的阅后即焚、一次性查看、实时位置会被关闭… | `00-client/方案书.md:229` | 集成工程师（沈思锴） |
| 16 | 能。官方提供并存方式（Coexistence），Botmaker 官方支持，条件见上表方式 b。是否选用，主要取决于这个号码对现有业务有多重要；Meta 已取消此前的国家限制，若是中国大陆号码，以实际接入结果为准【待核实】。 | `00-client/方案书.md:240` | 集成工程师（沈思锴） |
| 17 | 以下为估算【待核实】，按 2026-10-01 之后的计费规则计算；拿到摩兽真实的咨询量、国家分布和广告投放情况后会重新测算。 | `00-client/方案书.md:389` | 集成工程师（沈思锴） |
| 18 | 网络访问 / Meta、WhatsApp、Botmaker 后台从中国大陆访问需要跨境网络 / 沿用摩兽海外社媒团队现有的合规跨境网络环境；访问稳定性【待核实】 | `00-client/方案书.md:440` | 集成工程师（沈思锴） |
| 19 | 标记说明：【待核实】＝平台细节仍在核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝商务数字与承诺由张宝文最终确定。 | `00-client/维护服务说明.md:4` | 集成工程师（沈思锴） |
| 20 | 假设：Botmaker 后台的具体菜单名称以培训时看到的实际界面为准【待核实】；各指标的目标值为建议值【待客户确认】；审核人为建议分工【待客户确认】。 | `00-client/运维手册.md:5` | 集成工程师（沈思锴） |
| 21 | 导入 / 在 Botmaker 后台的知识库（Knowledge Base）功能中新增或修改【待核实】 / 运营 | `00-client/运维手册.md:35` | 集成工程师（沈思锴） |
| 22 | 咨询量（按天、按周） / Botmaker 数据看板【待核实】、线索库 / 趋势；哪个帖子带来高峰 / 突增时提醒销售；突降时检查链接是否失效 | `00-client/运维手册.md:128` | 集成工程师（沈思锴） |
| 23 | 销售首次响应时间 / Botmaker 数据看板【待核实】 / 工作时间内 B 端线索 2 小时内【待客户确认】 / 反馈给销售负责人 | `00-client/运维手册.md:133` | 集成工程师（沈思锴） |
| 24 | 号码质量评级与连接状态 / Meta 后台的 WhatsApp 管理功能【待核实】 / 评级保持良好；号码显示为已连接 / 评级下降时立即停发模板并找技术；显示未连接时立即找技术 | `00-client/运维手册.md:138` | 集成工程师（沈思锴） |
| 25 | 假设：响应时限、周末值班安排、线索分工为建议值【待客户确认】；Botmaker 后台的按钮名称以培训时看到的实际界面为准【待核实】；结束分类的名称为暂定【待核实】【待客户确认】。 | `00-client/销售接手SOP.md:5` | 集成工程师（沈思锴） |
| 26 | 把会话分配给自己【待核实】。接手之后，AI 不再回复这位客户。 | `00-client/销售接手SOP.md:49` | 集成工程师（沈思锴） |
| 27 | 在 Botmaker 的会话里选择模板发送【待核实】。模板的审核类别由 Meta 决定，可能影响单条费用【待核实】。 | `00-client/销售接手SOP.md:98` | 集成工程师（沈思锴） |
| 28 | 结束会话时，在 Botmaker 里选择一个结束分类，系统会据此更新线索库里的状态。名称为暂定【待核实】【待客户确认】。 | `00-client/销售接手SOP.md:102` | 集成工程师（沈思锴） |
| 29 | 同事休假或离职，会话没人管 / 由销售负责人把会话转给其他销售【待核实】 | `00-client/销售接手SOP.md:122` | 集成工程师（沈思锴） |
| 30 | 中文后台 / 官网与帮助中心为英、西、葡三语，后台语言【待核实】（SOURCES S-B14） / 任务书前提为"有中文后台"，本次未复核【待核实】 / 阿里云控制台，任务书前提为"有中文后台"，本次未复核【待核实】 | `01-design/adr/0001-platform-choice.md:31` | 集成工程师（沈思锴） |
| 31 | 内置 AI Agent 与知识库 / 有；按 token 另计费，单价未公开（SOURCES S-B7） / 【待核实】 / 【待核实】 | `01-design/adr/0001-platform-choice.md:32` | 集成工程师（沈思锴） |
| 32 | 计价货币 / USD（SOURCES S-B3） / 【待核实】 / 【待核实】 | `01-design/adr/0001-platform-choice.md:33` | 集成工程师（沈思锴） |
| 33 | 备注 / 主要市场在拉美，有时差；开票与合同主体【待核实】 / 若内置 AI 能力不足，需要路线 B 式的外部调用承担更多工作 / 国内主体签约与开票可能更顺【待核实】；同上 | `01-design/adr/0001-platform-choice.md:34` | 集成工程师（沈思锴） |
| 34 | 1 之后 Botmaker 如何结算客服消息 / 【待核实】SOURCES S-B13 | `01-design/adr/0001-platform-choice.md:58` | 集成工程师（沈思锴） |
| 35 | 后台界面语言、发票与合同主体 / 【待核实】SOURCES S-B14 | `01-design/adr/0001-platform-choice.md:59` | 集成工程师（沈思锴） |
| 36 | 中国大陆访问稳定性 / 【待核实】SOURCES S-B15 | `01-design/adr/0001-platform-choice.md:60` | 集成工程师（沈思锴） |
| 37 | 超量后是否允许长期不升档 / 【待核实】03-whatsapp/cost-model.md 第 4 节 | `01-design/adr/0001-platform-choice.md:61` | 集成工程师（沈思锴） |
| 38 | 主手机至少每 14 天打开一次 App，否则连接自动断开；Meta 另写伴侣设备约 30 天不活跃也会被断开，伴侣设备指该号码在其他设备上的登录还是平台连接本身，原文未写明【待核实】（SOURCES S-M6）；模板只能从 Botmaker 发；平台不支持群聊；语音与视频通话只能在手机端（SOURCES S-B4）。 | `01-design/adr/0002-number-strategy.md:30` | 集成工程师（沈思锴） |
| 39 | Coexistence 的国家限制已全部取消（欧盟、英国 2025-10-23 放开，南非、尼日利亚 2026-04-15 放开等，SOURCES S-M7）；只有中国大陆 +86 号码没有任何官方原文点名支持，接入流程仍保留"本地区不可用"的错误码，若客户号码为 +86，以接入流程中的实际结果为准【待核实】。 | `01-design/adr/0002-number-strategy.md:31` | 集成工程师（沈思锴） |
| 40 | 同一号码上 Bot 与真人并存：销售在手机 App 里回复后，平台侧能否自动让 Bot 对该会话保持静音【待核实】，列入试用验证（02-botmaker/trial-test-plan.md）。 | `01-design/adr/0002-number-strategy.md:32` | 集成工程师（沈思锴） |
| 41 | 客户号码若为中国大陆 +86，能否走 Coexistence（其他国家码的限制已取消） / 【待核实】SOURCES S-M7 | `01-design/adr/0002-number-strategy.md:59` | 集成工程师（沈思锴） |
| 42 | Coexistence 下真人在 App 回复后 Bot 的静音行为 / 【待核实】 | `01-design/adr/0002-number-strategy.md:60` | 集成工程师（沈思锴） |
| 43 | 路线 A：离线评测用与 Botmaker 所选模型相同的模型（选型见 0006-model-selection.md），抽取规则与 JSON 块由 scripts/gen_schema_artifacts.py 从同一份源头注入两个 prompt，逐字相同。平台会在我们的指令之外再包一层自己的上下文，离线结果只能近似生产；所以决策门在平台… | `01-design/adr/0003-ai-route-a-b.md:20` | 集成工程师（沈思锴） |
| 44 | AI Agent 写变量的稳定性、是否支持 JSON 输出 / 【待核实】SOURCES S-B9，由决策门回答 | `01-design/adr/0003-ai-route-a-b.md:43` | 集成工程师（沈思锴） |
| 45 | Code Action 调用频率、并发与每月执行次数上限（2026-09-22 再查，原文仍未写） / 【待核实】SOURCES S-B10 | `01-design/adr/0003-ai-route-a-b.md:44` | 集成工程师（沈思锴） |
| 46 | Botmaker 账号的界面代际与能否指定模型（路线 A"同一模型"的前提） / 【待核实】SOURCES S-B8，试用 T-12 | `01-design/adr/0003-ai-route-a-b.md:45` | 集成工程师（沈思锴） |
| 47 | 卡片里回到 Botmaker 会话的链接格式 / 【待核实】 | `01-design/adr/0005-notification-channel.md:44` | 集成工程师（沈思锴） |
| 48 | Botmaker 内置模型 / 路线 A 的自然选择。未指定时默认为帮助中心所写的 "GPT-4 Mini"，可按 Bot 或按 AI Agent 切换；可选清单未公开。帮助中心 "Botmaker 3.0 - AI Agents" 栏目另写 3.0 版默认模型为 "Open AI 5.4"、目前不能换；两种说法很可能分属两代界面，新账号… | `01-design/adr/0006-model-selection.md:17` | 集成工程师（沈思锴） |
| 49 | 成本 / 单价未公开【待核实】；成本模型按每百万 token 1.0 至 5.0 USD 的占位区间估算 / 公开价位低；路线 B 的模型费在任何档位都很小（03-whatsapp/cost-model-results.md） / 低 | `01-design/adr/0006-model-selection.md:29` | 集成工程师（沈思锴） |
| 50 | 数据条款 / 服务条款写 Botmaker 对客户数据的使用限于提供服务，但隐私政策另有"改进服务、研究"用途；Co-pilot 原文写明用于训练 ChatGPT 模型（不启用）；AI Agent 的对话与下游模型供应商（至少两家）是否用于训练、有无 DPA 与子处理方清单，公开页面都没有，须书面问 Botmaker【待核实】（SOURC… | `01-design/adr/0006-model-selection.md:30` | 集成工程师（沈思锴） |
| 51 | Botmaker 账号属 3.0 版还是经典界面、能否指定模型、可选模型清单与 token 单价 / 【待核实】SOURCES S-B7、S-B8 | `01-design/adr/0006-model-selection.md:58` | 集成工程师（沈思锴） |
| 52 | 各候选的"不用于训练"条款依据；Botmaker 的 AI Agent 对话是否用于训练、有无 DPA（书面问 Botmaker） / 【待核实】SOURCES S-B17 | `01-design/adr/0006-model-selection.md:59` | 集成工程师（沈思锴） |
| 53 | 集成服务不参与对话，只做"接收、归一化、入库、通知"。它宕机时对话照常，只是线索入库与通知中断；宕机期间的回调未必补得回：Botmaker 对单条失败是否重发未知【待核实】，10 分钟内失败超过 100 次还会熔断 10 分钟、期间的回调丢失（SOURCES S-B5）。所以健康检查要告警，缺口靠对账补（05-integration/bo… | `01-design/architecture.md:62` | 集成工程师（沈思锴） |
| 54 | Code Action 可调外部 HTTP、单次执行上限 90 秒（SOURCES S-B10）；调用频率上限【待核实】。 | `01-design/architecture.md:111` | 集成工程师（沈思锴） |
| 55 | Botmaker webhook 单条失败的重试与超时策略（熔断规则已证实：10 分钟内失败超过 100 次停发 10 分钟，期间消息丢失） / 【待核实】SOURCES S-B5 | `01-design/architecture.md:174` | 集成工程师（沈思锴） |
| 56 | webhook 真实回调样本与字段 / 【待核实】SOURCES S-B6 | `01-design/architecture.md:175` | 集成工程师（沈思锴） |
| 57 | Code Action 调用频率上限 / 【待核实】SOURCES S-B10 | `01-design/architecture.md:176` | 集成工程师（沈思锴） |
| 58 | Click-to-WhatsApp referral：字段表已列 whatsappReferral，JSON 示例没有，待真实样本核对；集成服务目前只认 referral 键 / 【待核实】SOURCES S-B12 | `01-design/architecture.md:177` | 集成工程师（沈思锴） |
| 59 | 销售所在网络能否稳定打开 Botmaker 坐席界面 / 【待核实】SOURCES S-B15 | `01-design/architecture.md:178` | 集成工程师（沈思锴） |
| 60 | 写入变量 / source_code（平台内写入方式【待核实】；集成服务会用同一规则再解析一次，以服务端为准） | `01-design/conversation-flow.md:45` | 集成工程师（沈思锴） |
| 61 | 会话级变量复位 / 进入本状态时把 escalation_flag 置为 false、escalation_reason 置空。Botmaker 的会话变量很可能按联系人长期保留【待核实】；不复位的话，老客户再次来访的第一条消息就会带着上一次的升级标记，再次触发销售通知。线索类字段（公司、类型、国家等）不复位，老客户不用重答 | `01-design/conversation-flow.md:55` | 集成工程师（沈思锴） |
| 62 | 动作 / 结束分类经事件回调回写线索 status（映射见 routing-rules.md 第 5 节）；客户再次来访回到 S1_GREETING 或直接续接原队列【待核实】 | `01-design/conversation-flow.md:203` | 集成工程师（沈思锴） |
| 63 | 一个联系人一条线索**：以 E.164 号码为去重键，lead_id 由它哈希生成；同一客户多次来访更新同一条记录，回调重放不会产生重复线索。平台未给出号码时（客户以用户名联系、回调里只有业务范围用户标识【待核实】），改用平台客户 ID 作键（bm:<customerId>），phone 与 country_by_phone 留空，国家改… | `01-design/lead-schema.md:8` | 集成工程师（沈思锴） |
| 64 | Botmaker 会话变量与字段同名**（shared/tromox_lead/fields.py 中的 BOTMAKER_VARIABLES）。若平台不接受下划线变量名【待核实】，集成服务的归一化同时接受驼峰写法（b2bType 等）。 | `01-design/lead-schema.md:12` | 集成工程师（沈思锴） |
| 65 | phone / string (E.164) \ / null / 系统 / 客户 WhatsApp 号码，统一为 E.164（如 +4915112345678）；客户以用户名联系、平台只给出业务范围用户 ID 时为空【待核实】 /  / 是 | `01-design/lead-schema.md:20` | 集成工程师（沈思锴） |
| 66 | referral / object \ / null / 系统 / Click-to-WhatsApp 广告 referral（source_id、source_url、headline 等）；是否透传【待核实】 | `01-design/lead-schema.md:37` | 集成工程师（沈思锴） |
| 67 | 销售结束会话时在 Botmaker 选择结束分类（typification），集成服务据此回写 status；映射表见 05-integration/botmaker-api-notes.md。【待核实】 | `01-design/lead-schema.md:112` | 集成工程师（沈思锴） |
| 68 | "description": "Click-to-WhatsApp ad referral. Whether Botmaker passes it through is 【待核实】.", | `01-design/lead.schema.json:54` | 集成工程师（沈思锴） |
| 69 | 停用 AI / 转人工后对该会话静音 Bot，避免 AI 与销售同时回复；会话结束后恢复。平台内的具体动作名称【待核实】；API 侧聊天对象带 isBotMuted 字段（SOURCES S-B2） | `01-design/routing-rules.md:119` | 集成工程师（沈思锴） |
| 70 | 结束分类与线索状态的映射（分类名称【待核实】【待客户确认】）： | `01-design/routing-rules.md:126` | 集成工程师（沈思锴） |
| 71 | 窗口规则：客户最后一条消息之后 24 小时内可以自由回复；窗口关闭后只能发经 Meta 预审的模板消息。窗口截止时间 = last_message_ts + 24 小时；Botmaker 的聊天对象直接给出 whatsAppWindowCloseDatetime（SOURCES S-B2），通知卡片上以北京时间显示截止时间。客户每回复一次… | `01-design/routing-rules.md:158` | 集成工程师（沈思锴） |
| 72 | 模板属 utility 类，措辞不带促销内容；Meta 可能改判为 marketing 类【待核实】。模板正文见 02-botmaker/templates/。 | `01-design/routing-rules.md:176` | 集成工程师（沈思锴） |
| 73 | Meta 在广告带来的首条消息上附带 referral 数据（来源类型、广告 id、来源 URL、标题、正文、点击 id）。线索结构里已留好 referral 对象，字段为 source_type、source_id、source_url、headline、body、ctwa_clid。Botmaker 回调字段表里的对应对象只有 sou… | `01-design/source-tracking.md:94` | 集成工程师（沈思锴） |
| 74 | Botmaker 是否把 referral 明细放进 webhook 回调 / 【待核实】帮助中心回调字段表列有 messages[].whatsappReferral（子键 sourceId、sourceURL、headline、body），但同文 JSON 示例里没有这个对象，真实回调未见（SOURCES S-B6、S-B12）；广告… | `01-design/source-tracking.md:98` | 集成工程师（沈思锴） |
| 75 | 假设：Botmaker 标签名可使用小写字母、数字与下划线【待核实】；若不支持下划线，统一去掉下划线改驼峰，映射关系不变。 | `01-design/tag-taxonomy.md:4` | 集成工程师（沈思锴） |
| 76 | 假设：支持语种、工作时间、回复时限、隐私政策链接均为默认值【待客户确认】；AI Agent 可用的动作（转人工、跳转流程）与变量写入方式以试用账号实测为准【待核实】（SOURCES S-B9）。 | `02-botmaker/ai-agent-system-prompt.md:5` | 集成工程师（沈思锴） |
| 77 | 交接话术由谁发有两种部署方式，按试用结果二选一【待核实】：默认由 AI 发（可即时翻译，不用在流程里维护各语种版本）；若 AI Agent 能直接触发"转人工"流程节点且该节点自带各语种话术，则把上面一句改为 "When you hand over, trigger the handover and send nothing: the f… | `02-botmaker/ai-agent-system-prompt.md:145` | 集成工程师（沈思锴） |
| 78 | "是否在工作时间"由流程判断并通过变量或节点分支告诉 AI【待核实】；AI 自己不推算时间。 | `02-botmaker/ai-agent-system-prompt.md:146` | 集成工程师（沈思锴） |
| 79 | 是否需要平台支持结构化 JSON 输出 / 不需要。平台是否支持 JSON 输出【待核实】；若支持，可作为后续优化，把 16 个字段合成一次写入 / 不依赖平台，由外部调用保证固定 JSON | `02-botmaker/ai-agent-system-prompt.md:265` | 集成工程师（沈思锴） |
| 80 | 连续无关消息的限流（例如同一会话内拒答超过若干次后不再回复）如需要，在流程层处理【待核实】，不写进 prompt。 | `02-botmaker/ai-agent-system-prompt.md:270` | 集成工程师（沈思锴） |
| 81 | 答复回填：Q1–Q3 改 03-whatsapp/cost-model-inputs.csv 后重跑 cost_model.py，再同步报价单；Q5、Q6 回填 05-integration/botmaker-api-notes.md 与 01-design/source-tracking.md；Q7、Q8 回填 ADR 0006；其余回… | `02-botmaker/botmaker-sales-questions.md:26` | 集成工程师（沈思锴） |
| 82 | 假设：账号、号码、Meta 商务账户全部开在客户名下，集成工程师只持有 Botmaker 后台的操作席位（Meta 侧默认不需要管理员权限，见 03-whatsapp/meta-onboarding-checklist.md 第 2 节第 6 项）；后台界面以英文为准；界面路径只写已在帮助中心读到的（见 SOURCES.md），其余一律写… | `02-botmaker/setup-guide.md:4` | 集成工程师（沈思锴） |
| 83 | 前置：客户已按 03-whatsapp/meta-onboarding-checklist.md 准备好 Meta 商务账户与号码；操作人所在网络可稳定访问 Botmaker 后台（SOURCES S-B15）【待核实】。 | `02-botmaker/setup-guide.md:5` | 集成工程师（沈思锴） |
| 84 | 套餐先不付费，试用期验证完（trial-test-plan.md）再由客户绑卡开 Standard（149 USD/月，按 DAILY USER 计数，SOURCES S-B3）。开通 WhatsApp 商业平台账户另有一次性 99 USD。超出套餐的单价两页不一致：定价页写 Standard 每个额外对话 0.07 USD，FAQ 写 … | `02-botmaker/setup-guide.md:37` | 集成工程师（沈思锴） |
| 85 | 账号内的时区、语言等全局设置：在 Botmaker 后台的账号设置功能中完成【待核实】；号码的时区在第 2 步接入时填写（SOURCES S-B4）。后台界面语言只有英、西、葡、法四种，没有中文（SOURCES S-B14），统一用英文。 | `02-botmaker/setup-guide.md:38` | 集成工程师（沈思锴） |
| 86 | Meta 消息费的支付方式：Meta 要求 2026-09-30 前绑定支付方式，否则 10/1 起用完每号码每月 1,000 条免费额度后，服务消息停投（SOURCES S-M9、S-M3）。经 Botmaker 接入时是由 Botmaker 结算，还是要客户在 WhatsApp 商业账户上自绑【待核实】：接入号码（第 2 步）前由客户… | `02-botmaker/setup-guide.md:39` | 集成工程师（沈思锴） |
| 87 | 验证方法**：客户管理员与集成工程师都能登录同一个项目；在 Botmaker 后台的成员管理功能中【待核实】能看到客户邮箱为所有者。截图存入交付记录（验收项 C5）。 | `02-botmaker/setup-guide.md:41` | 集成工程师（沈思锴） |
| 88 | 额外约束 / 号码需能收短信或语音验证码，且当前未注册在任何 WhatsApp 上 / App 版本不低于 2.24.17；至少每 14 天打开一次 App，否则断连；Meta 另写伴侣设备约 30 天不活跃也会断连，所指范围【待核实】（SOURCES S-M6）；吞吐固定 20 条/秒；阅后即焚、一次性查看、实时位置、广播列表停用；国家… | `02-botmaker/setup-guide.md:52` | 集成工程师（沈思锴） |
| 89 | 设置两步验证 PIN 并交客户保管：在 Botmaker 或 Meta 后台的号码设置功能中【待核实】。 | `02-botmaker/setup-guide.md:60` | 集成工程师（沈思锴） |
| 90 | 与销售约定分工：哪些会话由机器人先接、哪些由人在手机上直接回。人从手机 App 回复后机器人是否自动静默【待核实】，在试用账号验证（trial-test-plan.md 的 T-1）。 | `02-botmaker/setup-guide.md:69` | 集成工程师（沈思锴） |
| 91 | 在 Botmaker 后台的变量管理功能中【待核实】建下列 18 个会话变量，**变量名与线索字段名逐字相同**（源头：shared/tromox_lead/fields.py 的 BOTMAKER_VARIABLES）。变量 ID 不能含空格、连字符、星号等特殊字符（SOURCES S-B18）；是否允许下划线、是否区分大小写、长度上限… | `02-botmaker/setup-guide.md:95` | 集成工程师（沈思锴） |
| 92 | S1_GREETING / 一条带 3 个回复按钮的消息 / 按钮标题不超过 20 个字符，最多 3 个：Dealer/Distributor、Rider or Customer、Other；话术含 AI 身份告知与隐私政策链接 {privacy_url}【待客户确认】；**进入本状态先把变量 escalation_flag 置为 fal… | `02-botmaker/setup-guide.md:125` | 集成工程师（沈思锴） |
| 93 | S7_AFTER_HOURS / 工作时间判断：在 Botmaker 后台的营业时间功能中【待核实】配置 {working_hours}【待客户确认】 / 非工作时间转人工时改发夜间话术，AI 继续可答 FAQ | `02-botmaker/setup-guide.md:131` | 集成工程师（沈思锴） |
| 94 | 静默机器人（该会话内 AI 不再自动回复）：在 Botmaker 的转人工动作中【待核实】；API 侧可见 isBotMuted 字段（SOURCES S-B2）。 | `02-botmaker/setup-guide.md:138` | 集成工程师（沈思锴） |
| 95 | 建工单：在流程内直接建工单的节点【待核实】；若流程内没有，退路是由 Code Action 调用 POST /tickets（SOURCES S-B2，60 次/分钟），在试用账号里定。 | `02-botmaker/setup-guide.md:140` | 集成工程师（沈思锴） |
| 96 | 资源（Resources）里挂上第 5 步的知识库；动作（Actions）里只开放"转人工"与必要的流程跳转，其余不开。可用动作清单【待核实】。 | `02-botmaker/setup-guide.md:155` | 集成工程师（沈思锴） |
| 97 | 模型：Bot Designer 左侧工具栏 "Generative model" 设 Bot 默认模型；AI Agent 配置最后一步 "Generative Model" 里可选 "Use a different model" 单独指定（SOURCES S-B8）。未指定时默认 "GPT-4 Mini"。帮助中心 "Botmaker 3… | `02-botmaker/setup-guide.md:156` | 集成工程师（沈思锴） |
| 98 | 不启用 Co-pilot**（坐席回复建议）：Botmaker 官网原文写明 Co-pilot 用坐席与客户的全部对话训练 ChatGPT 模型，而 WhatsApp 条款禁止用业务数据训练 AI 模型（SOURCES S-B17、S-M5）。Co-pilot 的开关位置与默认状态【待核实】，首次进入时确认为关闭。AI Agent 的对话… | `02-botmaker/setup-guide.md:159` | 集成工程师（沈思锴） |
| 99 | 导入方式：在 Botmaker 后台的知识库（Knowledge Base）功能中上传【待核实】；也可用 API POST /knowledge-bases 新建、PUT /knowledge-bases 更新（SOURCES S-B2，type 可取 www、doc、content、articles、other，language 含 E… | `02-botmaker/setup-guide.md:172` | 集成工程师（沈思锴） |
| 100 | 队列在 Botmaker 后台的服务队列（Service queues / attention queues）功能中建【待核实】；API 侧只能查与改，不能建（SOURCES S-B2，GET /attention-queues 限 5 次/分钟）。 | `02-botmaker/setup-guide.md:190` | 集成工程师（沈思锴） |
| 101 | 转人工时建工单，标题建议 [B2B][DE] 公司名 - 产品，正文放 ai_summary 与关键字段。工单自定义字段【待核实】；MVP 不依赖自定义字段。 | `02-botmaker/setup-guide.md:194` | 集成工程师（沈思锴） |
| 102 | 写入方式按优先级：流程节点里的打标签动作（seg_ 跟按钮走）【待核实】；不能在流程里算的（country_、src_、prio_）由集成服务算好存进线索库的 tags 字段，是否同时回写 Botmaker 会话标签（PATCH /chats/{chatReference}，3 次/秒，SOURCES S-B2）在试用后定【待核实】。标签… | `02-botmaker/setup-guide.md:205` | 集成工程师（沈思锴） |
| 103 | 销售结束会话时必须选一个结束分类，集成服务据此回写线索状态（事件回调里带 typification，SOURCES S-B6）。分类名【待核实】【待客户确认】： | `02-botmaker/setup-guide.md:209` | 集成工程师（沈思锴） |
| 104 | 开通 webhook 功能：它是额外计费、默认关闭的功能，由客户所有者在账户设置里开通；单价未公开【待核实】，开通前由客户向 Botmaker 书面要价并同意（SOURCES S-B5）。同一渠道最多挂 1 个 webhook：本项目的 WhatsApp 渠道只挂集成服务这一个，其他系统要用回调数据由集成服务转发。 | `02-botmaker/setup-guide.md:226` | 集成工程师（沈思锴） |
| 105 | Bot 消息（Bot Messages） / 试用期勾，稳定后可关 / AI 写完变量后，变量变更可能随下一条 Bot 消息送达【待核实】；确认变量能随用户消息可靠送达后关掉，减少回调量 | `02-botmaker/setup-guide.md:238` | 集成工程师（沈思锴） |
| 106 | 单条回调失败是否重试、重试间隔、超时阈值、有无重放，原文均未写【待核实】；已知的是熔断规则：10 分钟内失败超过 100 次，接下来 10 分钟停发新消息，这段时间的消息丢失（SOURCES S-B5）。所以集成服务按"先落盘原始事件、立即返回 200、再处理"设计，并按消息 _id_ 做幂等（帮助中心字段表写作 _id，与示例不一致，以… | `02-botmaker/setup-guide.md:243` | 集成工程师（沈思锴） |
| 107 | 用测试手机发一条消息，集成服务日志里出现一条 type=message 的原始事件，字段与 05-integration/webhook-service/fixtures/ 的样例对得上；对不上的字段回填 fixture 并去掉相应的【待核实】。 | `02-botmaker/setup-guide.md:248` | 集成工程师（沈思锴） |
| 108 | 运行环境：Node.js v22；外部 HTTP 用内置 rp；单次执行超时 90 秒；每次最多写 200 个变量、每个变量值不超过 100 KB（SOURCES S-B10）。调用频率上限【待核实】。 | `02-botmaker/setup-guide.md:257` | 集成工程师（沈思锴） |
| 109 | 在 Botmaker 后台的代码功能中新建并发布一个 Code Action【待核实】，然后在 Bot Designer 里通过 "More > Action > Code Actions" 把它挂到 S2、S4 之后以及转人工之前（SOURCES S-B10）。 | `02-botmaker/setup-guide.md:258` | 集成工程师（沈思锴） |
| 110 | 外部分类接口的归属（直连模型的 OpenAI-compatible 接口，还是在集成服务里加一个分类端点）由 01-design/adr/0003-ai-route-a-b.md 定；无论哪种，密钥都不写进代码正文，用 Botmaker 的常量或密钥配置功能保存【待核实】。 | `02-botmaker/setup-guide.md:259` | 集成工程师（沈思锴） |
| 111 | 骨架（只用了帮助中心文章里出现过的对象与方法；字段名以试用账号实测为准【待核实】）： | `02-botmaker/setup-guide.md:260` | 集成工程师（沈思锴） |
| 112 | 角色与权限在 Botmaker 后台的成员与角色功能中配置【待核实】；平台支持自定义角色（SOURCES S-B2 的 roles 资源）。 | `02-botmaker/setup-guide.md:320` | 集成工程师（沈思锴） |
| 113 | 所有登录账号开启两步验证：在 Botmaker 后台的安全设置功能中【待核实】。 | `02-botmaker/setup-guide.md:322` | 集成工程师（沈思锴） |
| 114 | 假设：三条模板都按 utility（事务通知）类别提交；Meta 可能把它们改判为 marketing（营销）类，费率与发送条件随之变化【待核实】；ES / DE / FR / PT 译文为占位，语种清单与译文均【待客户确认】，须由母语者审核后再提交。 | `02-botmaker/templates/README.md:4` | 集成工程师（沈思锴） |
| 115 | 类别选 utility / 内容必须围绕客户自己发起的那次咨询，不含促销、优惠、新品推荐、节日问候；出现这些内容会被改判为 marketing【待核实】 | `02-botmaker/templates/README.md:28` | 集成工程师（沈思锴） |
| 116 | 变量不要太多 / 正文里固定文字要明显多于变量，否则容易被拒【待核实】 | `02-botmaker/templates/README.md:32` | 集成工程师（沈思锴） |
| 117 | 按钮 / 只用快捷回复按钮，标题不超过 25 个字符【待核实】；第二个按钮给客户一个体面的"不需要了"，减少被拉黑与举报 | `02-botmaker/templates/README.md:34` | 集成工程师（沈思锴） |
| 118 | 提交入口：在 Botmaker 后台的 WhatsApp 模板管理功能中【待核实】；也可用 API POST /whatsapp/templates（限 1 次/秒，SOURCES S-B2）。审核通常较快，但 W2 第一天就提交，不要等到 UAT（07-project/timeline.md）。 | `02-botmaker/templates/README.md:39` | 集成工程师（沈思锴） |
| 119 | 每月看一次模板的送达、已读与回复情况：在 Botmaker 后台的模板或通知报表功能中【待核实】。 | `02-botmaker/templates/README.md:56` | 集成工程师（沈思锴） |
| 120 | 假设：类别 utility；是否被 Meta 改判为 marketing【待核实】；译文与语种【待客户确认】。 | `02-botmaker/templates/tromox_info_request_v1.md:4` | 集成工程师（沈思锴） |
| 121 | 假设：类别 utility；是否被 Meta 改判为 marketing【待核实】；译文与语种【待客户确认】；仅完整版包含本模板。 | `02-botmaker/templates/tromox_support_update_v1.md:4` | 集成工程师（沈思锴） |
| 122 | 用途：开工第 1 周在试用账号里把所有【待核实】的平台行为测一遍，并用 20 条样例决定 AI 走路线 A 还是路线 B；结果是 01-design/adr/0003-ai-route-a-b.md 的决策依据。读者：集成工程师；结论抄送张宝文。 | `02-botmaker/trial-test-plan.md:3` | 集成工程师（沈思锴） |
| 123 | 之后客服消息与 AI token 在账单里怎么体现 / T-7 / 成本模型的两个【待核实】输入 | `02-botmaker/trial-test-plan.md:17` | 集成工程师（沈思锴） |
| 124 | 回调接收 / 集成服务的测试部署（05-integration/deployment.md），打开原始事件落盘；不使用第三方抓包网站，避免测试数据外流。webhook 是额外计费、默认关闭的功能，要先在账户设置里开通（SOURCES S-B5）；试用账号能否开通、是否收费【待核实】，开通前征得客户同意 | `02-botmaker/trial-test-plan.md:31` | 集成工程师（沈思锴） |
| 125 | T-11 / 回调里没有号码的联系人 / 查看 contactId 是否总是号码；若测试中出现业务范围用户标识（以用户名联系的客户），保存 1 份样本【待核实】 / 确认集成服务按平台客户 ID 入库并照常通知，号码与号码国家留空 / 05-integration/botmaker-api-notes.md；01-design/lead-… | `02-botmaker/trial-test-plan.md:48` | 集成工程师（沈思锴） |
| 126 | 各平台事实的核实结论，去掉已解决的【待核实】 / SOURCES.md（S-B3 至 S-B18、S-M6、S-M7、S-M9） | `02-botmaker/trial-test-plan.md:141` | 集成工程师（沈思锴） |
| 127 | 模型提供方不得用我们的数据训练或改进模型 / 选有明确"接口数据不用于训练"条款的企业级或接口级服务；消费级产品一律不用 / 选型时逐家核对条款【待核实】 | `03-whatsapp/compliance.md:39` | 集成工程师（沈思锴） |
| 128 | Botmaker 内置模型同样适用 / 公开页面没有数据处理协议、子处理方清单或通用的"不用于训练"条款；AI Agent 与生成式回复的对话是否用于训练、下游模型供应商是否训练，原文都没写。已知下游模型供应商至少两家：3.0 版默认模型 "Open AI 5.4"（SOURCES S-B8），搭建用的 AI Assistant 使用 A… | `03-whatsapp/compliance.md:41` | 集成工程师（沈思锴） |
| 129 | 本方案的主动消息只有一种**：针对客户自己发起的咨询做后续跟进（02-botmaker/templates/），按 utility 类别提交；是否被改判为 marketing【待核实】。 | `03-whatsapp/compliance.md:51` | 集成工程师（沈思锴） |
| 130 | 同意记录要可举证**：何时、在哪个会话、客户点了哪个按钮。线索库里至少保留同意时间与来源会话的标识【待核实】实现方式。 | `03-whatsapp/compliance.md:55` | 集成工程师（沈思锴） |
| 131 | WhatsApp / Meta / 平台方 / 其角色以 Meta 的条款为准【待核实】 | `03-whatsapp/compliance.md:67` | 集成工程师（沈思锴） |
| 132 | AI 身份告知 / 开场第一句说明是 AI 虚拟助手；被问到时如实回答。欧盟《人工智能法》对聊天机器人的透明度义务及其适用时间【待核实】 / 已写入话术与 prompt | `03-whatsapp/compliance.md:74` | 集成工程师（沈思锴） |
| 133 | 运营在 1 个工作日内登记到请求台账；法定答复期限通常为一个月【待核实】，内部目标 10 个工作日内完成【待客户确认】。 | `03-whatsapp/compliance.md:83` | 集成工程师（沈思锴） |
| 134 | 删除范围：线索库按 phone 删除该线索记录与原始事件；Botmaker 内的联系人与会话记录，在 Botmaker 后台的联系人管理功能中删除或匿名化【待核实】；已导出的表格与备份同步处理。 | `03-whatsapp/compliance.md:84` | 集成工程师（沈思锴） |
| 135 | Botmaker / 消息全文、联系人、变量、工单 / Botmaker 的云环境（其对外 IP 属 Google Cloud 网段，推断，SOURCES S-B15）；具体区域【待核实】 / 索取数据处理协议与数据驻留说明 | `03-whatsapp/compliance.md:93` | 集成工程师（沈思锴） |
| 136 | 会话记录 / Botmaker / 与线索保留期对齐；Botmaker 后台 Settings > Security 可按天数自动删除个人数据与文件（SOURCES S-B17），可设天数的上限能否覆盖 24 个月【待核实】 / 到期由平台自动删除 | `03-whatsapp/compliance.md:108` | 集成工程师（沈思锴） |
| 137 | bsp_markup_service,0.20,0.20,0.20,比例,【待核实】,SOURCES S-B13：Botmaker 对客服消息的加价未公布（帮助中心只说请找客户经理），暂按通知类同为 20% 假设 | `03-whatsapp/cost-model-inputs.csv:13` | 集成工程师（沈思锴） |
| 138 | botmaker_ai_usd_per_1m_tokens,1.0,2.5,5.0,USD/百万 token,【待核实】,SOURCES S-B7：单价未公开，此为占位区间 | `03-whatsapp/cost-model-inputs.csv:16` | 集成工程师（沈思锴） |
| 139 | ext_model_usd_per_1m_input,0.15,1.00,3.00,USD/百万 token,【待核实】,占位区间（小模型到旗舰模型的公开价位量级），以选定模型官网价为准 | `03-whatsapp/cost-model-inputs.csv:20` | 集成工程师（沈思锴） |
| 140 | ext_model_usd_per_1m_output,0.60,5.00,15.00,USD/百万 token,【待核实】,同上 | `03-whatsapp/cost-model-inputs.csv:21` | 集成工程师（沈思锴） |
| 141 | cost-model-inputs.csv / 低/中/高三档的全部输入，含状态列（假设 / 【待核实】 / 【待客户确认】 / 已复核） / 是 | `03-whatsapp/cost-model.md:14` | 集成工程师（沈思锴） |
| 142 | 月度免费额度抵扣：M_free = min(M − M_fep, free_service_msgs_per_month)（每号码每月 1,000 条，Meta 官方已确认，SOURCES S-M3）。免费入口窗口内的消息不占额度是由官方计费类型推断的【待核实】；MVP 只用 1 个号码。 | `03-whatsapp/cost-model.md:37` | 集成工程师（沈思锴） |
| 143 | Botmaker 套餐：在 Standard / Scale / Pro 中取"月费 + 超量 × 该档超量单价"最低者，超量单价按定价页取 0.07 / 0.06 / 0.05 USD（SOURCES S-B3；FAQ 写 0.025，两页矛盾【待核实】）。 | `03-whatsapp/cost-model.md:42` | 集成工程师（沈思锴） |
| 144 | "对话"的定义**：Botmaker 服务条款按 DAILY USER 计数，即 24 小时内收发过消息的外部用户（SOURCES S-B3）；同一客户隔天再来会再算一次。模型按"一个新咨询算一个对话"处理，客户多日往返时会低估。【待核实】 | `03-whatsapp/cost-model.md:49` | 集成工程师（沈思锴） |
| 145 | 套餐升档**：按定价页的分档超量单价，月对话数超过约 4,430 时 Scale 比"Standard + 超量"便宜，超过约 9,170 时 Pro 比 Scale 便宜；坐席数（10 / 20 / 50）也可能决定档位。超量是否允许长期不升档【待核实】。 | `03-whatsapp/cost-model.md:50` | 集成工程师（沈思锴） |
| 146 | 不含**：广告投放费、号码月租、销售人力、我们的服务费；Botmaker webhook 附加功能费（额外计费、单价未公开【待核实】，SOURCES S-B5），报价单里单列为"未公开"。 | `03-whatsapp/cost-model.md:54` | 集成工程师（沈思锴） |
| 147 | 假设：客户已有运营 Facebook / Instagram 的商务账户【待客户确认】；未认证时的收发范围、号码数上限、显示名审核机制、认证审核时长、发送量分级与质量评级已于 2026-09-22 按 Meta 原文逐条核实（SOURCES S-M8、S-M10）；认证材料清单、提交入口、显示名命名规范等细节未逐条核对原文，仍标【待核实】… | `03-whatsapp/meta-onboarding-checklist.md:4` | 集成工程师（沈思锴） |
| 148 | 官网域名验证 / 在商务账户里完成域名验证，有助于认证与后续广告归因【待核实】 / 客户 IT | `03-whatsapp/meta-onboarding-checklist.md:26` | 集成工程师（沈思锴） |
| 149 | WhatsApp 消息费的支付 / Meta 规定：2026-09-30 前账户上没有支付方式的，10/1 起每个号码每月 1,000 条免费服务消息照常投递、用完后停投（SOURCES S-M9、S-M3）；本项目开工周才接入，接入时就要有支付方式。经 BSP 接入时，模板消息费由 Botmaker 代收并加服务费（SOURCES S-… | `03-whatsapp/meta-onboarding-checklist.md:29` | 集成工程师（沈思锴） |
| 150 | 材料清单（境内公司为例）【待核实】 | `03-whatsapp/meta-onboarding-checklist.md:43` | 集成工程师（沈思锴） |
| 151 | 由客户管理员在 Meta 商务账户的安全中心发起认证【待核实】，按提示上传材料并选择验证方式（公司域名邮箱、电话或域名验证）。 | `03-whatsapp/meta-onboarding-checklist.md:56` | 集成工程师（沈思锴） |
| 152 | 备选：合作伙伴代认证多数几分钟内出结果、最长 24 小时，但只有部分合作伙伴能做，每个客户最多提交 3 次（SOURCES S-M8）；Botmaker 是否具备此资格【待核实】。自行提交被拖延时再考虑。 | `03-whatsapp/meta-onboarding-checklist.md:60` | 集成工程师（沈思锴） |
| 153 | 限制 / 号码当前不能注册在任何 WhatsApp 上 / App 版本不低于 2.24.17；主手机至少每 14 天打开一次 App，否则断连（SOURCES S-B4、S-M6）；Meta 另写伴侣设备约 30 天不活跃也会被断开，伴侣设备指该号码在电脑等处登录的其他设备还是平台连接本身，原文未写明【待核实】（SOURCES S-M6… | `03-whatsapp/meta-onboarding-checklist.md:69` | 集成工程师（沈思锴） |
| 154 | 未在任何 WhatsApp 上注册 / 曾注册过的先在 App 内注销账号再接入；注销后的等待期【待核实】 | `03-whatsapp/meta-onboarding-checklist.md:78` | 集成工程师（沈思锴） |
| 155 | 国家码的选择【待客户确认】 / 权衡三点：目标市场客户对号码的观感；公司能否长期持有并稳定收验证码；境内号码接入的可行性【待核实】 | `03-whatsapp/meta-onboarding-checklist.md:79` | 集成工程师（沈思锴） |
| 156 | 不用临时号码 / 不使用接码平台或来路不明的虚拟号；如用云通信厂商的正规号码，须确认能长期持有并能收验证码【待核实】 | `03-whatsapp/meta-onboarding-checklist.md:80` | 集成工程师（沈思锴） |
| 157 | 国家码：Coexistence 的国家限制已全部取消（SOURCES S-M7）；只有中国大陆 +86 号码没有官方原文点名，接入流程仍保留"本地区不可用"的错误码 3441042，若用 +86 号码，以接入流程的实际结果为准【待核实】，建议先用一个测试号在试用账号里走一遍（02-botmaker/trial-test-plan.md 的… | `03-whatsapp/meta-onboarding-checklist.md:87` | 集成工程师（沈思锴） |
| 158 | 指定专人保管该手机，并至少每 14 天打开一次 App；该号码另在其他设备上登录的，稳妥起见每台至少 30 天内用一次（伴侣设备 30 天规则的所指范围【待核实】，见第 4 节表格，SOURCES S-M6） | `03-whatsapp/meta-onboarding-checklist.md:89` | 集成工程师（沈思锴） |
| 159 | 规则要点（第 1 至 3 条是命名规范，未逐条核对原文【待核实】；第 4、5 条已按 Meta 原文核实，SOURCES S-M8）： | `03-whatsapp/meta-onboarding-checklist.md:97` | 集成工程师（沈思锴） |
| 160 | 显示名审核与商家认证是两件事：认证过了，显示名仍可能被拒。显示名每 30 天最多改 10 次；获批后须在 14 天内重新注册号码（要用到第 6 节的 PIN；经 Botmaker 接入时由谁操作【待核实】，接入当天一并问清）。 | `03-whatsapp/meta-onboarding-checklist.md:102` | 集成工程师（沈思锴） |
| 161 | 名称旁的认证徽标需另行申请，条件与流程【待核实】；MVP 不依赖它。 | `03-whatsapp/meta-onboarding-checklist.md:104` | 集成工程师（沈思锴） |
| 162 | 经 Botmaker 嵌入式注册时 PIN 由谁设置、在哪里查看或重置【待核实】，接入当天问清并记录。 | `03-whatsapp/meta-onboarding-checklist.md:109` | 集成工程师（沈思锴） |
| 163 | 遗忘 PIN 的重置流程与等待期【待核实】。 | `03-whatsapp/meta-onboarding-checklist.md:111` | 集成工程师（沈思锴） |
| 164 | 监控：每周看一次号码质量评级与号码是否为已连接状态，写入 00-client/运维手册.md 的周检项；集成工程师另看商务组合当前的发送额度档位，并留意 WABA 是否被限制。在 Botmaker 或 Meta 的 WhatsApp 管理后台看，具体入口【待核实】；也可用 GET /whatsapp/accounts/{number}/s… | `03-whatsapp/meta-onboarding-checklist.md:122` | 集成工程师（沈思锴） |
| 165 | 最多注册 2 个号码，完成认证或升到 2,000 档后自动放宽到 20 个。MVP 生产只用 1 个号码，但试用期接入的备用测试号与 T-1 的 Coexistence 测试号若登记在同一商务组合下，同样占名额；认证通过前正式号可能排不上，删除测试号能否释放名额【待核实】。试用号码的安排见 02-botmaker/trial-test-p… | `03-whatsapp/meta-onboarding-checklist.md:129` | 集成工程师（沈思锴） |
| 166 | 参考单价（USD / 百万 token，输入 / 输出；为 2026-06-24 的缓存价，开跑前以官网价格页为准【待核实】）：claude-opus-5 5 / 25；claude-sonnet-5 2 / 10；claude-haiku-4-5 1 / 5。其他服务商的单价请查各自官网，不要凭印象填。 | `04-eval/README.md:132` | 集成工程师（沈思锴） |
| 167 | 路线 A（Botmaker 内置 AI Agent）的模型在平台内，无法离线直调；离线评测用来迭代规则与示例，平台内的实际表现以 02-botmaker/trial-test-plan.md 的 20 条样例为准。【待核实】内置模型能否通过同款接口在平台外复现。 | `04-eval/README.md:152` | 集成工程师（沈思锴） |
| 168 | 依据：公开的接口描述文件与帮助中心文章（SOURCES S-B2、S-B5、S-B6、S-B10、S-B11、S-B12、S-B18）。未登录、未调用任何真实接口；凡未在一手来源读到的内容均标【待核实】。 | `05-integration/botmaker-api-notes.md:4` | 集成工程师（沈思锴） |
| 169 | 不要用 GET /messages、GET /billing/whatsapp/billed-conversations 做轮询：接口描述写明这两个端点"会增加 BI 数据源费用"。对话数据以 webhook 推送为准。唯一的例外是回调缺口（第 7 节）：熔断期间的消息原文写明丢失、有无补发未写，单条失败是否重发也未写（SOURCES S… | `05-integration/botmaker-api-notes.md:10` | 集成工程师（沈思锴） |
| 170 | Token 权限范围能否收窄（只读、限端点）：未见说明。【待核实】 | `05-integration/botmaker-api-notes.md:23` | 集成工程师（沈思锴） |
| 171 | POST /chats-actions/trigger-intent / 触发某个意图或**发送 WhatsApp 模板**（intentIdOrName 填模板名），可同时设置 variables、tags / 可选（二期的程序化再触达） / 未注明【待核实】 | `05-integration/botmaker-api-notes.md:35` | 集成工程师（沈思锴） |
| 172 | chatReference 有两种写法（接口描述原文）：Botmaker 的 chatId；或 channelId + : + contactId（channelId 从 GET /channels 取，形如 <项目>-whatsapp-<公司号码>；contactId 对 WhatsApp 即客户号码）。webhook 回调里的 cus… | `05-integration/botmaker-api-notes.md:43` | 集成工程师（沈思锴） |
| 173 | 开通与计费 / webhook 是额外计费的功能，默认不开，要先在账户设置里开通；单价未公开【待核实】 / SOURCES S-B5 | `05-integration/botmaker-api-notes.md:50` | 集成工程师（沈思锴） |
| 174 | 未知：** 单条失败是否重试、重试间隔、超时阈值、是否要求 2xx 以外的特定响应、有无重放，原文均未写。【待核实】 | `05-integration/botmaker-api-notes.md:62` | 集成工程师（沈思锴） |
| 175 | 回调结构（v1.1，【待核实】） | `05-integration/botmaker-api-notes.md:66` | 集成工程师（沈思锴） |
| 176 | 变量名写法**：流程里的会话变量与线索字段同名（下划线）。帮助中心写明变量 ID 不能含空格、连字符、星号等特殊字符，是否允许下划线没写（SOURCES S-B18）【待核实】。若平台不接受下划线，改用驼峰（b2bType、productInterest），服务两种都认、代码不用改；但流程、AI Agent 指令、配置指南里的变量名都要跟… | `05-integration/botmaker-api-notes.md:78` | 集成工程师（沈思锴） |
| 177 | 变量随哪类回调下发**：示例里 variables 出现在消息回调中。服务对每一条消息回调都重新评估是否需要通知，不依赖"变量一定跟着用户消息来"。【待核实】 | `05-integration/botmaker-api-notes.md:79` | 集成工程师（沈思锴） |
| 178 | 按钮点击的形态**：接口描述里消息内容类型有 button-click 与 selectedButton，回调示例里没有。流程应在按钮动作里直接给变量赋值（如 segment=B2B），服务只认变量，不解析按钮文本。【待核实】 | `05-integration/botmaker-api-notes.md:80` | 集成工程师（沈思锴） |
| 179 | 变量跨会话保留**：Botmaker 的会话变量按联系人保存。流程须在新会话开场（S1_GREETING）把 escalation_flag、escalation_reason 重置，否则老客户再次来访时，第一条消息就会带着上次的升级标记触发一次通知。【待核实】 | `05-integration/botmaker-api-notes.md:81` | 集成工程师（沈思锴） |
| 180 | CTWA referral**：帮助中心回调字段表列有 messages[].whatsappReferral，子键 sourceId、sourceURL、headline、body；同文 JSON 示例里没有这个对象。字段表里没有来源类型与点击 id，ctwa_clid 在帮助中心与 API 描述文件中都未出现（SOURCES S-B6… | `05-integration/botmaker-api-notes.md:82` | 集成工程师（沈思锴） |
| 181 | 只有 WhatsApp 的 contactId 是号码**：其他渠道（Instagram、Messenger）的回调 MVP 直接跳过（结果为 skipped_no_contact）；二期接私信渠道时沿用"平台客户 ID"去重键即可。WhatsApp 渠道里 contactId 不是号码的客户（只给出业务范围用户标识【待核实】）不跳过：按… | `05-integration/botmaker-api-notes.md:83` | 集成工程师（沈思锴） |
| 182 | 销售在 Botmaker 结束会话时选择结束分类，conversation-close 事件把它带回来，服务据此回写 status。分类名称需要在 Botmaker 后台的结束分类功能中预先建好【待核实】，名称与含义由客户销售确认【待客户确认】。 | `05-integration/botmaker-api-notes.md:87` | 集成工程师（沈思锴） |
| 183 | Token 无效或过期 / 401 或 403【待核实】具体状态码 / 到 Token 生成页重新生成，或用刷新接口；更新部署环境的密钥配置 | `05-integration/botmaker-api-notes.md:105` | 集成工程师（沈思锴） |
| 184 | 我方回调服务不可用 / 10 分钟内失败超过 100 次触发熔断，接下来 10 分钟停发，这段时间的消息丢失（SOURCES S-B5）；单条失败是否重试未知【待核实】 / 健康检查加告警，尽快恢复；恢复后用 python -m app.replay 重放已落盘未处理的事件。它只能重放落了盘的，熔断期间以及单条失败后没重发的回调补不回：先… | `05-integration/botmaker-api-notes.md:112` | 集成工程师（沈思锴） |
| 185 | CTWA referral：字段表已列 messages[].whatsappReferral（SOURCES S-B12），待真实样本核对对象名、层级、是否含点击 id；服务目前只认 referral / 需要真实广告流量；无广告前保持【待核实】 / 集成工程师、客户运营 | `05-integration/botmaker-api-notes.md:123` | 集成工程师（沈思锴） |
| 186 | VPS / 约 6 至 12 USD / 与 03-whatsapp/cost-model-inputs.csv 的 hosting_usd_per_month（低、中档 6 USD，高档 12 USD）一致；具体厂商报价【待核实】 | `05-integration/deployment.md:21` | 集成工程师（沈思锴） |
| 187 | Botmaker webhook 功能 / 单价未公开【待核实】 / 额外计费、默认关闭的功能，不开就收不到回调（SOURCES S-B5）；计在 Botmaker 账单里，不属于本机费用 | `05-integration/deployment.md:25` | 集成工程师（沈思锴） |
| 188 | 切换有数秒不可用。Botmaker 对单条回调失败是否重试尚不清楚【待核实】；若不重试，这几秒里的回调会丢失，app.replay 也补不回（它只重放已落盘的事件）。数秒的切换一般碰不到熔断线（10 分钟内失败超过 100 次，SOURCES S-B5）。所以更新放在咨询低谷（北京时间上午，欧美的深夜）进行；更新后看一眼 /health … | `05-integration/deployment.md:105` | 集成工程师（沈思锴） |
| 189 | 所选厂商的实际月费是否落在 6 至 12 USD / 【待核实】 / 集成工程师 | `05-integration/deployment.md:141` | 集成工程师（沈思锴） |
| 190 | Botmaker 单条回调失败的重试策略（决定更新窗口的宽严；熔断规则已知，SOURCES S-B5） / 【待核实】 / 集成工程师 | `05-integration/deployment.md:142` | 集成工程师（沈思锴） |
| 191 | Botmaker webhook 功能的单价 / 【待核实】 / 集成工程师 | `05-integration/deployment.md:143` | 集成工程师（沈思锴） |
| 192 | 接口路径、请求体与返回体按飞书开放平台公开文档整理（租户令牌、记录查询 records/search、记录创建、记录更新），未用真实租户跑通。尤其是查询接口的 filter 写法与「单选列自动补选项」的行为。【待核实】 | `05-integration/feishu-bitable-setup.md:78` | 集成工程师（沈思锴） |
| 193 | 日期列接受毫秒时间戳、复选框列接受布尔、多选列接受字符串数组，是按文档写的；若某列类型建错（例如把日期建成文本），写入会报错码，日志里能看到。【待核实】 | `05-integration/feishu-bitable-setup.md:79` | 集成工程师（沈思锴） |
| 194 | 频控：飞书对单个应用的写接口有每秒次数限制，MVP 的线索量远低于该限制；历史导入一次写几千行时要分批。【待核实】 | `05-integration/feishu-bitable-setup.md:81` | 集成工程师（沈思锴） |
| 195 | 建在知识库里的多维表格，其网址 token 是知识库节点的，不能直接当 app_token；需要把表格移出知识库或换用节点接口取 app_token。【待核实】 | `05-integration/feishu-bitable-setup.md:82` | 集成工程师（沈思锴） |
| 196 | 假设：回调结构按 Botmaker 帮助中心示例建模（SOURCES S-B6），真实样本到手前标【待核实】；服务部署在境外，见 ../deployment.md；Botmaker API 端点与限流见 ../botmaker-api-notes.md。 | `05-integration/webhook-service/README.md:4` | 集成工程师（沈思锴） |
| 197 | 状态回写 / 坐席消息出现时线索转 contacted；conversation-close 事件里的结束分类（typification）映射为线索状态，映射表见 ../botmaker-api-notes.md 第 6 节。【待核实】 | `05-integration/webhook-service/README.md:29` | 集成工程师（沈思锴） |
| 198 | app/models.py / Botmaker v1.1 回调模型，宽松解析【待核实】 | `05-integration/webhook-service/README.md:38` | 集成工程师（沈思锴） |
| 199 | fixtures/ / 6 个回调样例，顶层 _note 注明结构【待核实】 | `05-integration/webhook-service/README.md:44` | 集成工程师（沈思锴） |
| 200 | BOTMAKER_CHAT_URL_TEMPLATE / （链接见出处） / 卡片上的"接手"链接【待核实】 | `05-integration/webhook-service/README.md:122` | 集成工程师（沈思锴） |
| 201 | 真实回调的字段名与层级是否与 fixture 一致，尤其 contactId、customerId、messages[]._id_、variables。【待核实】 | `05-integration/webhook-service/README.md:144` | 集成工程师（沈思锴） |
| 202 | 按钮点击在回调里的形态，以及变量是随用户消息、Bot 消息还是单独事件下发。【待核实】 | `05-integration/webhook-service/README.md:145` | 集成工程师（沈思锴） |
| 203 | Botmaker 是否接受带下划线的变量名：已知变量 ID 不能含空格、连字符、星号（SOURCES S-B18），下划线原文未写。不接受时用驼峰，服务两种都认；流程、AI Agent 指令里的变量名与标签名要全仓跟着改。【待核实】 | `05-integration/webhook-service/README.md:146` | 集成工程师（沈思锴） |
| 204 | 回调是否包含分配坐席类事件（assigned-to-agent、queue-set）；没有时线索在首条坐席消息出现时才转 contacted。【待核实】 | `05-integration/webhook-service/README.md:147` | 集成工程师（沈思锴） |
| 205 | Botmaker 对单条回调失败的重试、间隔与超时策略（熔断规则已证实，见第 1 节"先落盘"一行）。【待核实】 | `05-integration/webhook-service/README.md:148` | 集成工程师（沈思锴） |
| 206 | CTWA 广告 referral：回调字段表列有 messages[].whatsappReferral（sourceId、sourceURL、headline、body），JSON 示例里没有（SOURCES S-B12）。服务目前只认名为 referral 的对象，照字段表的写法到达时读不到；拿到真实样本核对后再决定是否解析，届时改 … | `05-integration/webhook-service/README.md:149` | 集成工程师（沈思锴） |
| 207 | 卡片链接的实际地址格式（公开接口描述里出现过三种写法）。【待核实】 | `05-integration/webhook-service/README.md:150` | 集成工程师（沈思锴） |
| 208 | 会话变量跨会话保留：流程需在新会话开场时重置 escalation_flag 与 escalation_reason，否则老客户再次来访会在第一条消息就触发一次通知。【待核实】已交接的线索不受此影响（不再因重判发卡）。 | `05-integration/webhook-service/README.md:151` | 集成工程师（沈思锴） |
| 209 | contactId 是否永远是号码：Botmaker 的公开接口描述里已出现 BSUID（WhatsApp 的商家范围用户标识）相关字段与事件。若部分客户只给出标识而不给号码，"按号码判国家、按号码去重"对这部分客户不成立。服务的处理：WhatsApp 渠道的回调只要带 customerId，线索照常入库并照常通知销售，去重键改用 bm:… | `05-integration/webhook-service/README.md:152` | 集成工程师（沈思锴） |
| 210 | 飞书多维表格镜像（feishu_bitable）的接口形态（租户令牌、records/search 按 lead_id 过滤、创建 / 更新记录、各列类型接受的值）按飞书开放平台公开文档整理，未用真实租户核实；拿到客户租户后按 05-integration/feishu-bitable-setup.md 第 6 节验一遍。【待核实】 | `05-integration/webhook-service/README.md:154` | 集成工程师（沈思锴） |
| 211 | 【待核实】 The structure follows the example in Botmaker's help centre (SOURCES S-B6) and has | `05-integration/webhook-service/app/models.py:3` | 集成工程师（沈思锴） |
| 212 | referral: dict[str, Any] / None = None                          # 【待核实】 CTWA passthrough | `05-integration/webhook-service/app/models.py:30` | 集成工程师（沈思锴） |
| 213 | referral: dict[str, Any] / None = None                          # 【待核实】 | `05-integration/webhook-service/app/models.py:66` | 集成工程师（沈思锴） |
| 214 | defines the close categories in Botmaker 【待核实】【待客户确认】 (see botmaker-api-notes.md). | `05-integration/webhook-service/app/normalize.py:53` | 集成工程师（沈思锴） |
| 215 | ASSIGNMENT_EVENTS = {"assigned-to-agent", "queue-set"}  # 【待核实】 whether webhooks emit these | `05-integration/webhook-service/app/normalize.py:62` | 集成工程师（沈思锴） |
| 216 | 【待核实】; individual variables win over it. Nullish values are dropped so they can | `05-integration/webhook-service/app/normalize.py:114` | 集成工程师（沈思锴） |
| 217 | Botmaker's API already models as BSUID 【待核实】) being mistaken for a phone number. | `05-integration/webhook-service/app/normalize.py:149` | 集成工程师（沈思锴） |
| 218 | """CTWA ad referral, if Botmaker passes it through 【待核实】 (top level or per message).""" | `05-integration/webhook-service/app/normalize.py:177` | 集成工程师（沈思锴） |
| 219 | 【待核实】 - the lead is still recorded, keyed by Botmaker's customer id, with phone | `05-integration/webhook-service/app/normalize.py:240` | 集成工程师（沈思锴） |
| 220 | "_note": "【待核实】结构依据 Botmaker 帮助中心的 webhook 示例（SOURCES S-B6）整理，尚未用真实回调样本核对；拿到真实样本后替换本文件并同步 app/models.py。号码、姓名、公司均为虚构。 场景：销售在 Botmaker 结束会话并选择结束分类（typification），用于回写线索状态。分… | `05-integration/webhook-service/fixtures/event_conversation_close.json:2` | 集成工程师（沈思锴） |
| 221 | Meta 服务消息的支付方式已落实：Botmaker 书面确认由其结算，或客户已在 WhatsApp 商业账户上绑定（Meta 截止 2026-09-30，未绑定则 10/1 起用完每号码每月 1,000 条免费额度后服务消息停投）；由谁绑定【待核实】（SOURCES S-M9、S-M3） / Botmaker 书面答复或 Meta 后台… | `06-acceptance/go-live-checklist.md:16` | 集成工程师（沈思锴） |
| 222 | 走 Coexistence 时：App 版本不低于 2.24.17；"至少每 14 天打开一次 App"已写入运营例行事项并指定责任人（主设备约 14 天不活跃会被断开；Meta 另写伴侣设备约 30 天不活跃也会断开，所指范围【待核实】）；客户知道并存号码不能用 API 注销，断开要在 App 里操作，断开后 15 分钟才能重新接入（S… | `06-acceptance/go-live-checklist.md:26` | 集成工程师（沈思锴） |
| 223 | webhook 功能已在账户设置里开通（额外计费、默认关闭；单价未公开【待核实】，已取得 Botmaker 书面报价并经客户同意）；该 WhatsApp 渠道只挂了集成服务这 1 个 webhook；每条上线线路都已收到真实回调（SOURCES S-B5） / Botmaker webhook 页的成功计数；集成服务原始事件日志 | `06-acceptance/go-live-checklist.md:72` | 集成工程师（沈思锴） |
| 224 | 能否办一张公司名下的国际信用卡用于 Botmaker 与 Meta 的账单？ / 第三方费用客户直付能否落地（Botmaker 只收信用卡或借记卡，SOURCES S-B3）；Meta 要求账户上有支付方式，否则 10/1 起每月免费额度用完后服务消息停投，经 Botmaker 接入时由谁绑定【待核实】（S-M9） | `07-project/meeting-prep.md:57` | 集成工程师（沈思锴） |
| 225 | R02 / **计费变化**：2026-10-01 起窗口内回复按条计费（SOURCES S-M1）；每号码每月前 1,000 条服务消息免费已由 Meta 官方确认（S-M3，按号码按月重置、不结转），72 小时免费入口内的消息是否占这份额度仍是推断【待核实】；Botmaker 是否在 Meta 价格上加价、是否计入套餐对话数，原文未写… | `07-project/risk-register.md:11` | 集成工程师（沈思锴） |
| 226 | R04 / **认证延误**：Meta 商家认证与显示名审核是关键路径上唯一不受控的环节；商家认证审核最长 14 个工作日（SOURCES S-M8） / 中至高 / 高 / 节前提交，不等开工；按清单一次备齐材料；被退回当天处理；退路已证实：未认证也能无上限回复客户主动发起的会话，入站链路可先上线，代价是主动发起每 24 小时最多 25… | `07-project/risk-register.md:13` | 集成工程师（沈思锴） |
| 227 | R05 / **Botmaker 时差与支持**：主要市场在拉美，英、西、葡支持，美元计价；后台界面只有英、西、葡、法四种，没有中文；合同主体为 BOTMAKER INC 或其阿根廷、巴西关联公司，适用阿根廷法律；非拉美主体能否开票未确认【待核实】（S-B14） / 中 / 中 / 第 1 周用试用账号把关键问题验完；问题攒批书面提；必要… | `07-project/risk-register.md:14` | 集成工程师（沈思锴） |
| 228 | R16 / **Coexistence 特有问题**：主设备约 14 天不活跃会被自动断开（S-B4、S-M6），Meta 另写伴侣设备约 30 天不活跃也会断开，所指范围【待核实】（S-M6）；并存号码不能用 API 注销，只能由客户在 App 里断开，断开后 15 分钟才能重新接入；接入后 24 小时内未完成历史同步须断开重走（S-M… | `07-project/risk-register.md:25` | 集成工程师（沈思锴） |
| 229 | R20 / **Botmaker webhook 熔断与附加费**：webhook 是额外计费、默认关闭的功能，单价未公开；每个渠道最多挂 1 个；10 分钟内失败超过 100 次会熔断 10 分钟，这段时间的消息丢失，根本到不了集成服务；单条失败是否重试未公开（SOURCES S-B5） / 低至中 / 中 / 开通前书面问清单价【待核… | `07-project/risk-register.md:29` | 集成工程师（沈思锴） |
| 230 | R21 / **Botmaker 数据条款**：官网写明 Co-pilot（坐席回复建议）用坐席与客户的对话训练 ChatGPT 模型；AI Agent 的对话是否用于训练、下游模型供应商是否训练，公开页面都没写，也没有公开的 DPA 与子处理方清单（SOURCES S-B17）；WhatsApp 条款禁止用业务数据训练 AI 模型（S-… | `07-project/risk-register.md:30` | 集成工程师（沈思锴） |
| 231 | R22 / **内置模型不可指定**：Botmaker 3.0 版帮助文章写默认模型 "Open AI 5.4"、目前不能换模型，经典界面的文章则写可按 Bot 或 Agent 切换；新账号落在哪一代、能否指定模型未知（SOURCES S-B8）；不能指定时，路线 A"离线评测与生产同一模型"的前提不成立，离线评测结果只能近似生产 / 中… | `07-project/risk-register.md:31` | 集成工程师（沈思锴） |
| 232 | R23 / **支付方式截止**：Meta 规定 2026-09-30 前账户上没有支付方式的，10/1 起每月免费额度（S-M3）用完后服务消息停投（SOURCES S-M9）；本项目经 Botmaker 接入，是由 Botmaker 结算还是要客户在 WABA 上自绑支付方式，未知【待核实】；漏绑的后果是每个号码当月 1,000 条免… | `07-project/risk-register.md:32` | 集成工程师（沈思锴） |
| 233 | WhatsApp 消息费的支付方式：Meta 规定 10/1 起账户上没有支付方式的，每号码每月 1,000 条免费服务消息用完即停投（SOURCES S-M9）；经 Botmaker 接入时由谁绑定【待核实】，节前向 Botmaker 书面确认，接入当天落实（03-whatsapp/meta-onboarding-checklist.m… | `07-project/timeline.md:75` | 集成工程师（沈思锴） |
| 234 | 你之前对客户说的"WhatsApp 可以和 Botmaker 共存"成立**：我核实过，Botmaker 帮助中心有官方的 Coexistence 接入文章。条件：App 版本要够新、至少每 14 天打开一次 App、模板只能从平台发、广播列表会停用。Meta 已取消 Coexistence 的国家限制（欧盟、英国等都已放开）；只有中国大… | `99-internal/zhang-baowen-brief.md:15` | 集成工程师（沈思锴） |
| 235 | Botmaker 的 AI 是按 token 另外收费的，单价没公开。【待核实】 | `99-internal/zhang-baowen-brief.md:23` | 集成工程师（沈思锴） |
| 236 | 另外两笔 Botmaker 侧的费用还不清楚，已列进要书面问 Botmaker 的清单：把线索推给我们线索库的 webhook 是额外付费功能，单价没公开；套餐超量单价官网两处写法不一样（每个对话 0.07 还是 0.025 USD），估算按贵的算。【待核实】 | `99-internal/zhang-baowen-brief.md:25` | 集成工程师（沈思锴） |
| 237 | 结论标记：**已复核**＝在一手来源读到原文；**部分复核**＝仅第三方来源一致；**未能复核**＝未找到可靠来源，沿用原数字并标【待核实】；**有更新**＝与开工前掌握的信息不同。 | `SOURCES.md:5` | 集成工程师（沈思锴） |
| 238 | "每号码每月前 1,000 条服务消息免费" **已由 Meta 官方定价页确认**（2026-09-10 更新）：按号码计，每月重置、不结转，自 2026-10-01 生效（S-M3）。首轮只在 BSP 文章里读到，是因为读到的是官方页面的旧快照。 / 成本模型的免费额度参数去掉【待核实】；免费额度为 0 的情景只保留作敏感性参考。 | `SOURCES.md:13` | 集成工程师（沈思锴） |
| 239 | Botmaker 的生成式 AI **按 token 另行计费**，单价未公开；默认模型在帮助中心写作 "GPT-4 Mini"，可按 Bot 或按 Agent 切换；但 3.0 版文章写默认 "Open AI 5.4"、目前不能换模型，新账号是哪一代未知（S-B7、S-B8）。 / 路线 A 不是"零模型成本"；成本模型给区间并标【待核… | `SOURCES.md:14` | 集成工程师（沈思锴） |
| 240 | Botmaker webhook 的鉴权头是 auth-bm-token，帮助中心给出了 v1.1 消息回调示例（S-B5、S-B6）；公开 API 描述文件给出了逐端点限流（S-B2）。 / 集成服务的 fixture 按该示例建模；真实样本到手前字段仍标【待核实】。 | `SOURCES.md:15` | 集成工程师（沈思锴） |
| 241 | Botmaker 的 webhook 是**额外计费、默认关闭**的功能，每个渠道只能挂 1 个；10 分钟内失败超过 100 次会熔断 10 分钟，期间的消息丢失（S-B5）。 / 第三方费用多一项未知单价【待核实】；集成服务必须先应答再异步处理，健康检查要告警。 | `SOURCES.md:17` | 集成工程师（沈思锴） |
| 242 | S-B3 / 套餐（USD/月）：Standard 149（3,000 个对话、10 个坐席）；Scale 249（5,000 个对话、20 个坐席）；Pro 499（10,000 个对话、50 个坐席）；Enterprise 面议。"Up to 300 free initial conversations"。通知类消息 "transpa… | `SOURCES.md:26` | 集成工程师（沈思锴） |
| 243 | S-B5 / Webhook 在 Settings > Integrations > Botmaker API 中配置：回调 URL、可选安全 Token（随每次回调放在请求头 auth-bm-token）、渠道选择、消息类型勾选（Bot / 用户 / 坐席消息、消息状态、仅 HSM 状态、事件消息）、"包含变量"开关。**2026-09… | `SOURCES.md:28` | 集成工程师（沈思锴） |
| 244 | S-B6 / Webhook 回调示例（v1.1 消息）：顶层 v、type（message / event）、chatPlatform、contactId、customerId、sessionId、whatsappNumber、firstName、lastName、chatChannelId、customerCreationTime、s… | `SOURCES.md:29` | 集成工程师（沈思锴） |
| 245 | S-B7 / 生成式 AI 计费：按 token 计，"fixed price per block of 1,000,000 tokens"，单价随模型不同，文章未给数字；每次回复约带最近 20 条消息、指令、知识库命中段落；消耗明细在 Settings > Account > "Products and consumption"。建 A… | `SOURCES.md:30` | 集成工程师（沈思锴） |
| 246 | S-B8 / 模型选择：Bot Designer 左侧工具栏 "Generative model"；AI Agent 配置最后一步可 "Use a different model"；未指定时默认 "GPT-4 Mini"（原文如此）；可选模型清单未公开。**2026-09-22 补充**：帮助中心 "Botmaker 3.0 - AI A… | `SOURCES.md:31` | 集成工程师（沈思锴） |
| 247 | S-B9 / AI Agent 可按指令把用户信息写入变量，官方示例写法为 "store it in ${fullName}"。是否支持结构化（JSON）输出：文章未提。【待核实】需在试用账号验证（见 02-botmaker/trial-test-plan.md）。 / 部分复核 / （链接见出处） | `SOURCES.md:32` | 集成工程师（沈思锴） |
| 248 | S-B10 / Code Actions：运行时 Node.js v22；外部 HTTP 用内置 rp（request-promise）；单次执行超时 90 秒；单次最多 200 个用户变量、每个变量值最大 100 KB；用 user.set / user.get 读写变量，result.text / result.gotoRule / … | `SOURCES.md:33` | 集成工程师（沈思锴） |
| 249 | S-B12 / CTWA：Botmaker 有 "Click to WhatsApp Dashboards" 功能，会识别来源为广告 referral 的会话；开通要在 Business Manager 里把 Botmaker 加为只读合作伙伴。**2026-09-22 补充**：西语《Formatos ejemplo de Webhoo… | `SOURCES.md:35` | 集成工程师（沈思锴） |
| 250 | S-B13 / 10/1 之后 Botmaker 如何向客户结算客服消息。"Messages sent as replies to user-initiated conversations or within the 24-hour window are free of charge" 这句旧口径出自**定价页**（en/es/pt 三版… | `SOURCES.md:36` | 集成工程师（沈思锴） |
| 251 | S-B14 / 官网与帮助中心为英/西/葡三语。**2026-09-22 补充**：后台界面语言为英、西、葡、法四种（API 描述文件 AgentRequest.lang 枚举 en / es / pt / fr），机器人语言可选西、英、葡、法。合同主体：服务条款写 BOTMAKER INC（美国特拉华州公司）"or any of its… | `SOURCES.md:37` | 集成工程师（沈思锴） |
| 252 | S-B15 / 从中国大陆访问 Botmaker 后台与 API 的稳定性：无法从本机验证。其对外 IP 属 Google Cloud 网段（推断），大陆直连大概率不稳定，需客户现有的合规跨境网络。【待核实】 / 未能复核（推断） / S-B11 | `SOURCES.md:38` | 集成工程师（沈思锴） |
| 253 | S-B17 / AI 数据条款：官网 AI 页面原文 "Co-pilot uses all interactions between agents and users as training data to improve its response suggestions. These are used to refine ChatGPT… | `SOURCES.md:40` | 集成工程师（沈思锴） |
| 254 | S-B18 / 变量与标签命名：西语、葡语版《¿Cómo crear variables?》（2025-07-10 更新，英文版正文为空）写变量 ID "no puede tener caracteres especiales como espacio, guión, asterisco, etc."；是否允许下划线、是否区分大小写、长度… | `SOURCES.md:41` | 集成工程师（沈思锴） |
| 255 | S-M3 / **每个号码每月前 1,000 条服务消息免费**：官方定价页（2026-09-10 更新，changelog 同日条目）原文 "Each business phone number has one shared free tier of 1,000 delivered service messages per month"… | `SOURCES.md:49` | 集成工程师（沈思锴） |
| 256 | S-M6 / Coexistence 官方要求：WhatsApp Business App 版本 2.24.17 及以上；同步接入前 180 天内的消息；并存号码吞吐固定 20 条/秒；"Messages sent by the business via the WhatsApp Business app will continue to… | `SOURCES.md:52` | 集成工程师（沈思锴） |
| 257 | S-M7 / Coexistence 的国家限制**已全部取消**：官方 changelog 记录 2025-05-05 放开印度，2025-10-23 放开澳大利亚、日本、菲律宾、俄罗斯、韩国、土耳其、欧洲经济区、欧盟、英国，2026-04-15 放开尼日利亚、南非；S-M6 官方页面（2026-06-26 版）不再列任何不支持的国家。… | `SOURCES.md:53` | 集成工程师（沈思锴） |
| 258 | S-M9 / 支付方式截止：non-template-messages 页原文，Solution Provider 或直连企业 "that does not have a payment method on file by September 30, 2026"，Meta 自 10/1 起停止投递服务消息；定价页 9/10 版补充为额度内… | `SOURCES.md:55` | 集成工程师（沈思锴） |
| 259 | AI Agent 能否把抽取字段稳定写入变量；是否支持 JSON 输出 / 能按指令写变量（已复核）；稳定性与 JSON 输出**未能复核**，由试用账号 20 条样例决定路线 A/B。【待核实】 / S-B9 | `SOURCES.md:63` | 集成工程师（沈思锴） |
| 260 | Webhook 事件类型与 payload；CTWA referral 是否透传 / 事件类型与 v1.1 示例已取得（部分复核）；referral：回调字段表列有 whatsappReferral（sourceId、sourceURL、headline、body），但 JSON 示例里没有，真实回调未见（部分复核）【待核实】。另：web… | `SOURCES.md:64` | 集成工程师（沈思锴） |
| 261 | Code Actions 能否调外部 HTTP、超时与频率 / 能；超时 90 秒（已复核）；频率上限未能复核。【待核实】 / S-B10 | `SOURCES.md:65` | 集成工程师（沈思锴） |
| 262 | Botmaker 侧 10/1 后客服消息的结算方式 / 10/1 起按条计费、按客户国家定价已由 Botmaker 帮助中心确认；是否加价、是否计入套餐对话数**未能复核**【待核实】。另：每条线路默认开启 Central 转接，须手动关闭。 / S-B13、S-B16 | `SOURCES.md:66` | 集成工程师（沈思锴） |
| 263 | 界面语言、时区、发票/合同主体 / 时区在接入号码时设置（已复核）；后台界面英、西、葡、法四种语言（已复核，无中文）；合同主体为 BOTMAKER INC 或其阿根廷、巴西关联公司（已复核）；非拉美主体开票未能复核【待核实】。 / S-B4、S-B14 | `SOURCES.md:67` | 集成工程师（沈思锴） |
| 264 | 中国大陆访问稳定性 / **未能复核**（推断需跨境网络）。【待核实】 / S-B15 | `SOURCES.md:68` | 集成工程师（沈思锴） |
| 265 | FieldSpec("phone", "string (E.164) / null", SRC_SYSTEM, "客户 WhatsApp 号码，统一为 E.164（如 +4915112345678）；客户以用户名联系、平台只给出业务范围用户 ID 时为空【待核实】", label_column=True), | `shared/tromox_lead/fields.py:26` | 集成工程师（沈思锴） |
| 266 | FieldSpec("referral", "object / null", SRC_SYSTEM, "Click-to-WhatsApp 广告 referral（source_id、source_url、headline 等）；是否透传【待核实】"), | `shared/tromox_lead/fields.py:43` | 集成工程师（沈思锴） |
| 267 | """Click-to-WhatsApp ad referral. Whether Botmaker passes it through is 【待核实】.""" | `shared/tromox_lead/schema.py:44` | 集成工程师（沈思锴） |

## 4. 张宝文要定的：商务数字与承诺

负责人：张宝文

| # | 事项 | 出处 | 负责人 |
|---|---|---|---|
| 1 | 标记说明：【待核实】＝平台细节仍在核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝由张宝文最终确定。 | `00-client/培训计划.md:4` | 张宝文 |
| 2 | 假设：日期按《方案书》第 10 节的时间计划，随开工日调整【张宝文确认】；形式为线上会议加屏幕共享，全程录屏【待客户确认】；参训名单【待客户确认】。 | `00-client/培训计划.md:5` | 张宝文 |
| 3 | 新同事入职，可先看录屏与配套文档，由老同事带着做一遍；需要再次安排培训的，按工作量另行报价【张宝文确认】。 | `00-client/培训计划.md:59` | 张宝文 |
| 4 | 标记说明：【待核实】＝平台要求仍在向官方核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝由张宝文最终确定。 | `00-client/客户需提供清单.md:4` | 张宝文 |
| 5 | 假设：正式开工日按 2026-10-12 计【张宝文确认】；"建议负责人"一栏为建议，请摩兽填入实际姓名【待客户确认】。 | `00-client/客户需提供清单.md:5` | 张宝文 |
| 6 | 版本：v0.2，2026-09-22（按平台事实核实更新）。全部服务金额由张宝文最终确定；定稿时请替换【张宝文确认】标记并删除本行。 | `00-client/报价单.md:4` | 张宝文 |
| 7 | 标记说明：【待核实】＝平台政策或价格仍在向官方核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝商务数字与承诺由张宝文最终确定。 | `00-client/报价单.md:5` | 张宝文 |
| 8 | 精简版 / 【张宝文确认】 | `00-client/报价单.md:36` | 张宝文 |
| 9 | 完整版 / 【张宝文确认】 | `00-client/报价单.md:37` | 张宝文 |
| 10 | 具体包含多少定制开发、调优多久，待需求过一遍后确定【张宝文确认】。 | `00-client/报价单.md:44` | 张宝文 |
| 11 | 月度包含 / 平台与系统对接的技术调整（每月含一定额度，额度【张宝文确认】）；平台政策、计费规则变化的评估与适配建议；故障排查与恢复；AI 规则的结构性调整；每月一份运行小结 | `00-client/报价单.md:92` | 张宝文 |
| 12 | 金额 / 按月计，【张宝文确认】 | `00-client/报价单.md:96` | 张宝文 |
| 13 | 不购买维护服务时，也可按次支持，按工作量另行报价【张宝文确认】。 | `00-client/报价单.md:98` | 张宝文 |
| 14 | 以上为建议【张宝文确认】。付款期限与逾期处理【张宝文确认】。 | `00-client/报价单.md:108` | 张宝文 |
| 15 | 报价是否含税、发票类型与税率【张宝文确认】。 | `00-client/报价单.md:112` | 张宝文 |
| 16 | 开票主体与开票时点【张宝文确认】。 | `00-client/报价单.md:113` | 张宝文 |
| 17 | 调优期内的话术微调、知识库内容更新、规则小幅修正属于上线初期调整，不另计【张宝文确认】。 | `00-client/报价单.md:120` | 张宝文 |
| 18 | 报价有效期【张宝文确认】。 | `00-client/报价单.md:134` | 张宝文 |
| 19 | 两档项目总包金额、维护服务月费与额度、付款节奏、含税与开票 / 【张宝文确认】 | `00-client/报价单.md:138` | 张宝文 |
| 20 | 版本：v0.2，2026-09-22（按平台事实核实更新）。本稿供张宝文修改定稿后转交 Kim；定稿时请删除本行与全部【张宝文确认】标记。 | `00-client/方案书.md:4` | 张宝文 |
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
| 52 | 决策门阈值 95% 与样例数 20 / 【张宝文确认】 | `01-design/adr/0003-ai-route-a-b.md:46` | 张宝文 |
| 53 | Botmaker 内置模型若因数据条款被一票否决，退到路线 B 也不够：路线 B 下对话与 FAQ 仍由内置 AI Agent 承担（0003-ai-route-a-b.md 决策第 2 条），届时 Botmaker 内的 AI 怎么用要重新决策【张宝文确认】。 | `01-design/adr/0006-model-selection.md:50` | 张宝文 |
| 54 | 假设：开工前发出（07-project/timeline.md 的开工日前）；邮件以客户名义还是我方名义发、是否写明客户名称【张宝文确认】；不在邮件里透露我方报价与工作量。平台事实引用 SOURCES.md 条目编号。 | `02-botmaker/botmaker-sales-questions.md:4` | 张宝文 |
| 55 | 门槛 / 不低于 95%（即 140 项中最多错 7 项）走路线 A，否则走路线 B【张宝文确认】 / 06-acceptance/thresholds.json 的 route_a_variable_write_success_min | `02-botmaker/trial-test-plan.md:115` | 张宝文 |
| 56 | 集成服务 / 域名与托管位置： / 客户（托管费属第三方费用，客户直付）；如需代开代管【张宝文确认】 / 集成工程师 / 见 05-integration/deployment.md | `03-whatsapp/meta-onboarding-checklist.md:182` | 张宝文 |
| 57 | 数量 / 真实咨询不少于 150 条，其中 B 端不少于 30 条【张宝文确认】；B 端不足时宁可多翻历史记录补齐，也不要用编造的样本凑数 | `04-eval/labeling-guide.md:10` | 张宝文 |
| 58 | 假设：阈值为集成工程师建议值，**全部需【张宝文确认】**后再写进对客户的承诺；语种范围随报价档位变化。 | `06-acceptance/acceptance-criteria.md:4` | 张宝文 |
| 59 | 评测集：客户历史咨询经标注后的真实数据，**不少于 150 条**【张宝文确认】，其中 B 端不少于 30 条；标注方法见 04-eval/labeling-guide.md。合成数据只用于跑通工具，不计入验收。评测与生产使用同一模型、同一版 prompt。 | `06-acceptance/acceptance-criteria.md:15` | 张宝文 |
| 60 | A1 / B 端召回率（主指标） / ≥ 90%【张宝文确认】 / 标注为 B2B 的样本中，被判为 B2B 的比例。漏掉经销商的代价远高于误判个人，所以召回率优先 | `06-acceptance/acceptance-criteria.md:19` | 张宝文 |
| 61 | A2 / B 端精确率 / ≥ 80%【张宝文确认】 / 被判为 B2B 的样本中，标注确为 B2B 的比例 | `06-acceptance/acceptance-criteria.md:20` | 张宝文 |
| 62 | A3 / 国家准确率 / ≥ 95%【张宝文确认】 / 仅统计有号码前缀的样本；判定国家 = 客户自述国家，没有则取号码国家码 | `06-acceptance/acceptance-criteria.md:21` | 张宝文 |
| 63 | A4 / 产品识别率 / ≥ 85%【张宝文确认】 / 标注了产品的样本中，识别出的产品代码集合与标注完全一致的比例 | `06-acceptance/acceptance-criteria.md:22` | 张宝文 |
| 64 | A5 / 升级率（转人工比例） / ≤ 30%【张宝文确认】 / 被标记需要人工接管的样本比例；B 端字段收集完成后的正常交接也计入 | `06-acceptance/acceptance-criteria.md:23` | 张宝文 |
| 65 | A6 / JSON 解析成功率 / ≥ 98%【张宝文确认】 / 模型输出能被解析并通过字段校验的比例 | `06-acceptance/acceptance-criteria.md:24` | 张宝文 |
| 66 | B1 / uat-test-cases.md 中的 **20 个**端到端场景全部通过 / 20 / 20【张宝文确认】 | `06-acceptance/acceptance-criteria.md:32` | 张宝文 |
| 67 | B2 / 场景覆盖语种 / ≥ 3 个语种（精简版为 2 个）【张宝文确认】 | `06-acceptance/acceptance-criteria.md:33` | 张宝文 |
| 68 | B3 / B 端线索确认到销售收到通知的时延 / ≤ 60 秒【张宝文确认】 | `06-acceptance/acceptance-criteria.md:34` | 张宝文 |
| 69 | 在 Botmaker 试用账号内跑 **20 条**样例（02-botmaker/trial-test-plan.md）：字段写入变量的成功率 **≥ 95%** 走路线 A（内置 AI Agent 抽取），否则走路线 B（外部固定 JSON 调用）。【张宝文确认】 | `06-acceptance/acceptance-criteria.md:41` | 张宝文 |
| 70 | 对月度维护服务有没有需求，还是先自己维护、有事再找？ / 维护服务是否一并报；金额【张宝文确认】 | `07-project/meeting-prep.md:96` | 张宝文 |
| 71 | 假设：第二阶段是否启动、做哪几项，取决于 MVP 调优期结束时的数据；任何金额均【张宝文确认】，本文件不写数字。 | `07-project/phase-2-outline.md:4` | 张宝文 |
| 72 | R07 / **客户数据准备不足**：历史咨询不足 150 条，或没人标注，离线评测失去意义 / 中至高 / 高 / 节前三件事里单列；合成数据只用来跑通工具，不用于验收；样本不足时与张宝文协商调整样本量阈值【张宝文确认】并延长上线后抽查；开工日前未到位则 W1 至 W3 顺延 / 摩兽业务、摩兽销售；张宝文跟进 / 04-eval/la… | `07-project/risk-register.md:16` | 张宝文 |
| 73 | R12 / **需求蔓延**：CRM、经销商评分、私信接入等二期事项挤进 MVP / 高 / 中 / 报价单两档范围写死；范围外事项进二期清单；变更按约定另计，金额【张宝文确认】 / 张宝文 / 00-client/报价单.md、07-project/phase-2-outline.md | `07-project/risk-register.md:21` | 张宝文 |
| 74 | R21 / **Botmaker 数据条款**：官网写明 Co-pilot（坐席回复建议）用坐席与客户的对话训练 ChatGPT 模型；AI Agent 的对话是否用于训练、下游模型供应商是否训练，公开页面都没写，也没有公开的 DPA 与子处理方清单（SOURCES S-B17）；WhatsApp 条款禁止用业务数据训练 AI 模型（S-… | `07-project/risk-register.md:30` | 张宝文 |
| 75 | 假设：开工日 2026-10-12（国庆假期后第一个完整周的周一）为假设【张宝文确认】；国庆假期按 2026-10-01 至 2026-10-07 计，以国务院公布为准；调优期按完整版 4 周画，精简版为 2 周（到 2026-11-22）。 | `07-project/timeline.md:4` | 张宝文 |
| 76 | 正式开工（W1） / 假设【张宝文确认】 | `07-project/timeline.md:16` | 张宝文 |
| 77 | 张宝文对客户的总价在 15,000–30,000 CNY 区间内，他的 FDE 时间与利润空间由他自己定。下表只是算术参考。【张宝文确认】 | `99-internal/pricing-internal.md:17` | 张宝文 |
| 78 | 对客户的月度维护价 / 【张宝文确认】，客户版口径见 00-client/维护服务说明.md | `99-internal/pricing-internal.md:35` | 张宝文 |
| 79 | 付款时限 / 每个节点达成后 7 个自然日内付到；客户拖款不影响张宝文按节点付我 / 【张宝文确认】 | `99-internal/pricing-internal.md:45` | 张宝文 |
| 80 | 含税与开票 / 上述数字为不含税到手价；开票主体与税点由谁承担要先说清 / 【张宝文确认】 | `99-internal/pricing-internal.md:46` | 张宝文 |
| 81 | 变更计费 / 范围外需求先书面确认再做，按 1,200 CNY / 人天 / 【张宝文确认】 | `99-internal/pricing-internal.md:47` | 张宝文 |
| 82 | Meta 审核延误 / 日历时间顺延，不算我方违约；调优期从实际上线日起算 / 【张宝文确认】 | `99-internal/pricing-internal.md:48` | 张宝文 |
| 83 | 二期优先 / 第二阶段（他预估约 50,000 CNY，未定）同等条件下优先由我承接 / 【张宝文确认】 | `99-internal/pricing-internal.md:49` | 张宝文 |
| 84 | 案例署名 / 脱敏后可作为我的案例展示；客户名是否可提另行确认 / 【张宝文确认】 | `99-internal/pricing-internal.md:50` | 张宝文 |
| 85 | 全部【张宝文确认】项汇总在 open-questions.md。最靠前的：两档对客价格；验收阈值是否写进合同；维护月费；付款节奏与开票；是否承诺上线日期（建议只承诺"认证通过后 4 周"）。 | `99-internal/zhang-baowen-brief.md:60` | 张宝文 |

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
| 7 | Botmaker 账号与付款方式 / 平台开在摩兽名下，摩兽为所有者 / 用公司邮箱注册；平台以美元计价、信用卡支付，需要一张可付美元的公司信用卡【待客户确认】。接入号码时可能还要在 Meta 侧为 WhatsApp 消息费登记同一张卡：Meta 规定没有登记付款方式的账户，每个号码每月的免费消息额度用完后，回复客户的消息将无法送达；是否… | `00-client/客户需提供清单.md:91` | 客户（经张宝文 / Kim 对接） |
| 8 | 两种方式任选其一，选择建议见《方案书》第 6 节；最终选择【待客户确认】。 | `00-client/客户需提供清单.md:106` | 客户（经张宝文 / Kim 对接） |
| 9 | 标记说明：【待核实】＝平台政策或价格仍在向官方核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝商务数字与承诺由张宝文最终确定。 | `00-client/报价单.md:5` | 客户（经张宝文 / Kim 对接） |
| 10 | 具体语种【待客户确认】。不在验收范围内的语种，AI 仍然可以应答，只是不做专门的测试与调优。 | `00-client/报价单.md:42` | 客户（经张宝文 / Kim 对接） |
| 11 | 日均咨询量 / 低 10 个、中 30 个、高 120 个 / 【待客户确认】 | `00-client/报价单.md:77` | 客户（经张宝文 / Kim 对接） |
| 12 | B 端咨询占比 / 10% 至 20% / 【待客户确认】 | `00-client/报价单.md:78` | 客户（经张宝文 / Kim 对接） |
| 13 | 客户国家分布 / 德国 25%、意大利 15%、法国 10%、西班牙 10%、美国 10%、其他 30% / 【待客户确认】 | `00-client/报价单.md:79` | 客户（经张宝文 / Kim 对接） |
| 14 | 从 Click-to-WhatsApp 广告或 Facebook 主页按钮进入的对话占比（这部分 72 小时内免费） / 低 0%、中 20%、高 30% / 【待客户确认】 | `00-client/报价单.md:80` | 客户（经张宝文 / Kim 对接） |
| 15 | 各国单条费率 / 德国、法国、意大利、西班牙、美国按 Meta 官方费率卡；"其他"市场的国家构成未知，暂用官方费率的平均值代替 / 费率已核实；"其他"市场构成【待客户确认】 | `00-client/报价单.md:82` | 客户（经张宝文 / Kim 对接） |
| 16 | 选择精简版还是完整版；具体语种 / 【待客户确认】 | `00-client/报价单.md:139` | 客户（经张宝文 / Kim 对接） |
| 17 | 日均咨询量、国家分布、广告投放占比 / 【待客户确认】 | `00-client/报价单.md:140` | 客户（经张宝文 / Kim 对接） |
| 18 | 现状（根据 Kim 2026-09-18 的描述整理，细节【待客户确认】） | `00-client/方案书.md:52` | 客户（经张宝文 / Kim 对接） |
| 19 | 下面三段对话中的英文，是计划上线的实际话术。花括号内为占位内容，上线前替换；工作时间与答复时限为默认值【待客户确认】。涉及车型参数、价格、质保的内容一律来自摩兽提供的知识库，示例中不编造。 | `00-client/方案书.md:105` | 客户（经张宝文 / Kim 对接） |
| 20 | 通知销售 / 线索卡片发到销售群（飞书或企业微信，【待客户确认】），目标 1 分钟内送达 / 销售第一时间知道 | `00-client/方案书.md:195` | 客户（经张宝文 / Kim 对接） |
| 21 | 建议：MVP 用方式 a 起步；如果现有号码已经是主要对外入口，则选方式 b。也可以先 a 后 b：先用新号把链路跑通，再把老号并入。最终选择【待客户确认】，建议在中秋碰面时确定。 | `00-client/方案书.md:232` | 客户（经张宝文 / Kim 对接） |
| 22 | 隐私 / 开场消息附隐私政策链接【待客户确认】；只收集业务必需的信息；客户要求删除时按流程删除；发到销售群的卡片默认隐藏完整号码。欧盟客户占比较高，建议摩兽法务复核隐私告知与数据存放安排【待客户确认】 | `00-client/方案书.md:263` | 客户（经张宝文 / Kim 对接） |
| 23 | 隐私合规 / 欧盟客户的个人数据有专门要求 / 隐私告知、只收必要信息、删除请求流程；建议法务复核【待客户确认】 | `00-client/方案书.md:439` | 客户（经张宝文 / Kim 对接） |
| 24 | 标记说明：【待核实】＝平台细节仍在核实；【待客户确认】＝需要摩兽提供或拍板；【张宝文确认】＝商务数字与承诺由张宝文最终确定。 | `00-client/维护服务说明.md:4` | 客户（经张宝文 / Kim 对接） |
| 25 | 假设：Botmaker 后台的具体菜单名称以培训时看到的实际界面为准【待核实】；各指标的目标值为建议值【待客户确认】；审核人为建议分工【待客户确认】。 | `00-client/运维手册.md:5` | 客户（经张宝文 / Kim 对接） |
| 26 | 内容类型 / 建议审核人【待客户确认】 | `00-client/运维手册.md:50` | 客户（经张宝文 / Kim 对接） |
| 27 | 转人工比例 / 线索库 / 建议不高于 30%【待客户确认】 / 偏高说明知识库不够，补 FAQ | `00-client/运维手册.md:132` | 客户（经张宝文 / Kim 对接） |
| 28 | 销售首次响应时间 / Botmaker 数据看板【待核实】 / 工作时间内 B 端线索 2 小时内【待客户确认】 / 反馈给销售负责人 | `00-client/运维手册.md:133` | 客户（经张宝文 / Kim 对接） |
| 29 | 假设：响应时限、周末值班安排、线索分工为建议值【待客户确认】；Botmaker 后台的按钮名称以培训时看到的实际界面为准【待核实】；结束分类的名称为暂定【待核实】【待客户确认】。 | `00-client/销售接手SOP.md:5` | 客户（经张宝文 / Kim 对接） |
| 30 | 谁来接：按销售负责人定的国家或类型分工【待客户确认】。接的人在群里回一句"我接"，避免两个人同时回复。 | `00-client/销售接手SOP.md:43` | 客户（经张宝文 / Kim 对接） |
| 31 | 以下均为建议【待客户确认】： | `00-client/销售接手SOP.md:65` | 客户（经张宝文 / Kim 对接） |
| 32 | 夜间进线时，AI 已经告诉客户"同事将在一个工作日内回复"，并说明了工作时间（默认周一至周五 09:00 至 18:00，北京时间【待客户确认】）。销售要做的就是兑现这句话。 | `00-client/销售接手SOP.md:75` | 客户（经张宝文 / Kim 对接） |
| 33 | 同一位客户同一件事，模板最多发 2 次，两次至少间隔 3 天；两次都没有回复，就把线索状态改为培育或无意向，不再追发【待客户确认】。 | `00-client/销售接手SOP.md:96` | 客户（经张宝文 / Kim 对接） |
| 34 | 结束会话时，在 Botmaker 里选择一个结束分类，系统会据此更新线索库里的状态。名称为暂定【待核实】【待客户确认】。 | `00-client/销售接手SOP.md:102` | 客户（经张宝文 / Kim 对接） |
| 35 | 状态：已采纳方向（2026-09-21）；具体选 a 还是 b 取决于客户现有号码状况【待客户确认】。 | `01-design/adr/0002-number-strategy.md:4` | 客户（经张宝文 / Kim 对接） |
| 36 | 客户现有号码的类型、国家码、持机人，是否已在 WhatsApp Business App 上使用 / 【待客户确认】 | `01-design/adr/0002-number-strategy.md:57` | 客户（经张宝文 / Kim 对接） |
| 37 | 新号用哪个国家的号码、由哪个主体办理 / 【待客户确认】 | `01-design/adr/0002-number-strategy.md:58` | 客户（经张宝文 / Kim 对接） |
| 38 | 客户团队日常用什么表格工具还不知道【待客户确认】。 | `01-design/adr/0004-lead-storage.md:11` | 客户（经张宝文 / Kim 对接） |
| 39 | 备份**：每日把数据库文件与 CSV 复制到客户指定的存储位置【待客户确认】；保留期见 03-whatsapp/compliance.md。 | `01-design/adr/0004-lead-storage.md:19` | 客户（经张宝文 / Kim 对接） |
| 40 | 直接写飞书多维表格 / 销售看着方便；权限现成 / 依赖客户是否用飞书；接口限流与字段变更会反过来约束服务；欧盟客户数据进入境内工具需法务评估【待客户确认】 | `01-design/adr/0004-lead-storage.md:25` | 客户（经张宝文 / Kim 对接） |
| 41 | 客户用哪种表格或协作工具；是否需要同步适配器 / 【待客户确认】 | `01-design/adr/0004-lead-storage.md:41` | 客户（经张宝文 / Kim 对接） |
| 42 | 备份放在哪里、保留多久 / 【待客户确认】 | `01-design/adr/0004-lead-storage.md:42` | 客户（经张宝文 / Kim 对接） |
| 43 | 欧盟客户数据同步到境内工具的合规评估 / 【待客户确认】需法务复核 | `01-design/adr/0004-lead-storage.md:43` | 客户（经张宝文 / Kim 对接） |
| 44 | 状态：已采纳适配器方案（2026-09-21）；具体接哪个工具【待客户确认】。 | `01-design/adr/0005-notification-channel.md:4` | 客户（经张宝文 / Kim 对接） |
| 45 | 销售团队用哪种协作工具、通知发到哪个群 / 【待客户确认】 | `01-design/adr/0005-notification-channel.md:42` | 客户（经张宝文 / Kim 对接） |
| 46 | 是否需要按语种或区域分群通知 / 【待客户确认】 | `01-design/adr/0005-notification-channel.md:43` | 客户（经张宝文 / Kim 对接） |
| 47 | 含欧盟用户信息的通知进入境内协作工具的合规评估 / 【待客户确认】需法务复核 | `01-design/adr/0005-notification-channel.md:45` | 客户（经张宝文 / Kim 对接） |
| 48 | 咨询以英语为主，另有西、德、法、葡等语种（具体语种【待客户确认】），小语种上的分类质量是主要不确定项。 | `01-design/adr/0006-model-selection.md:9` | 客户（经张宝文 / Kim 对接） |
| 49 | 客户主体在中国大陆，另有欧洲服务中心（SOURCES 第 4 节）；由哪个主体签约、付款，决定了哪些模型开得出来【待客户确认】。 | `01-design/adr/0006-model-selection.md:10` | 客户（经张宝文 / Kim 对接） |
| 50 | 主体可开通性 / 高：随 Botmaker 账号开通，无需另签 / 取决于签约主体：境内主体直接签约与付款可能受限，境外主体可行性更高【待客户确认】 / 高：人民币结算、可开票 | `01-design/adr/0006-model-selection.md:27` | 客户（经张宝文 / Kim 对接） |
| 51 | 数据条款 / 服务条款写 Botmaker 对客户数据的使用限于提供服务，但隐私政策另有"改进服务、研究"用途；Co-pilot 原文写明用于训练 ChatGPT 模型（不启用）；AI Agent 的对话与下游模型供应商（至少两家）是否用于训练、有无 DPA 与子处理方清单，公开页面都没有，须书面问 Botmaker【待核实】（SOURC… | `01-design/adr/0006-model-selection.md:30` | 客户（经张宝文 / Kim 对接） |
| 52 | 由哪个主体签约与付款 / 【待客户确认】 | `01-design/adr/0006-model-selection.md:57` | 客户（经张宝文 / Kim 对接） |
| 53 | 欧盟用户数据进入境内模型服务的合规评估 / 【待客户确认】需法务复核 | `01-design/adr/0006-model-selection.md:60` | 客户（经张宝文 / Kim 对接） |
| 54 | 销售群通知 / 60 秒内把 B 端线索摘要推给销售；号码默认打码 / 客户现有协作工具【待客户确认】 / 选型见 adr/0005-notification-channel.md | `01-design/architecture.md:128` | 客户（经张宝文 / Kim 对接） |
| 55 | 销售群用哪种协作工具 / 【待客户确认】 | `01-design/architecture.md:179` | 客户（经张宝文 / Kim 对接） |
| 56 | 假设：英文为母版；西、德、法、葡为占位，具体语种【待客户确认】；{privacy_url}、{working_hours}、{sla_b2b}、{sla_general} 为占位符，默认值见第 5 节，均【待客户确认】；话术里不出现任何参数、价格、质保条款。 | `01-design/conversation-flow.md:4` | 客户（经张宝文 / Kim 对接） |
| 57 | 媒体、供应商、求职等与销售无关但与摩兽有关的来访：依据知识库给出对应的公开联系方式（内容【待客户确认】），segment 保持 unknown，随后结束。 | `01-design/conversation-flow.md:134` | 客户（经张宝文 / Kim 对接） |
| 58 | 问题已解决且客户无后续：进 S8_CONSENT（该步骤是否启用【待客户确认】），否则直接结束。 | `01-design/conversation-flow.md:151` | 客户（经张宝文 / Kim 对接） |
| 59 | 触发 / C 端问题已解决；是否启用【待客户确认】 | `01-design/conversation-flow.md:184` | 客户（经张宝文 / Kim 对接） |
| 60 | S1 开场问候与三个按钮 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:219` | 客户（经张宝文 / Kim 对接） |
| 61 | S2 一次问齐 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:220` | 客户（经张宝文 / Kim 对接） |
| 62 | S2 交接话术 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:221` | 客户（经张宝文 / Kim 对接） |
| 63 | S3 C 端接待与三个按钮 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:222` | 客户（经张宝文 / Kim 对接） |
| 64 | S4 其他 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:223` | 客户（经张宝文 / Kim 对接） |
| 65 | S6 一般转人工 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:224` | 客户（经张宝文 / Kim 对接） |
| 66 | S7 非工作时间 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:225` | 客户（经张宝文 / Kim 对接） |
| 67 | S8 营销同意与两个按钮 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:226` | 客户（经张宝文 / Kim 对接） |
| 68 | 话题收口 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:227` | 客户（经张宝文 / Kim 对接） |
| 69 | 价格与质保守卫 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:228` | 客户（经张宝文 / Kim 对接） |
| 70 | 没听懂两次 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 / 待翻译【待客户确认】 | `01-design/conversation-flow.md:229` | 客户（经张宝文 / Kim 对接） |
| 71 | {privacy_url} / 客户官网隐私政策链接 / 【待客户确认】 | `01-design/conversation-flow.md:237` | 客户（经张宝文 / Kim 对接） |
| 72 | {working_hours} / Monday to Friday, 09:00-18:00 China time (UTC+8) / 【待客户确认】 | `01-design/conversation-flow.md:238` | 客户（经张宝文 / Kim 对接） |
| 73 | {sla_b2b} / one business day / 【待客户确认】 | `01-design/conversation-flow.md:239` | 客户（经张宝文 / Kim 对接） |
| 74 | {sla_general} / one business day / 【待客户确认】 | `01-design/conversation-flow.md:240` | 客户（经张宝文 / Kim 对接） |
| 75 | ai_summary / string / AI 抽取 / 给销售看的一两句话摘要（默认简体中文【待客户确认】） / 是 | `01-design/lead-schema.md:40` | 客户（经张宝文 / Kim 对接） |
| 76 | 产品代码目录：MC10、UKKO、M05、MINO、M03、PESGO（来自官网公开车型名，SOURCES 第 4 节）。现售清单【待客户确认】。 | `01-design/lead-schema.md:91` | 客户（经张宝文 / Kim 对接） |
| 77 | 假设：工作时间、响应时限、结束分类名称均为默认值，【待客户确认】。 | `01-design/routing-rules.md:5` | 客户（经张宝文 / Kim 对接） |
| 78 | 回复语言：客户语言在支持清单内（SUPPORTED_LANGUAGES：en、es、de、fr、pt、it，最终清单【待客户确认】）则跟随；不在清单内用英文作答，并在需要时转人工 | `01-design/routing-rules.md:45` | 客户（经张宝文 / Kim 对接） |
| 79 | 队列 / MVP 设一个销售队列；按语种或区域分队列放到调优期再定【待客户确认】 | `01-design/routing-rules.md:121` | 客户（经张宝文 / Kim 对接） |
| 80 | 结束分类与线索状态的映射（分类名称【待核实】【待客户确认】）： | `01-design/routing-rules.md:126` | 客户（经张宝文 / Kim 对接） |
| 81 | 默认工作时间：周一至周五 09:00 至 18:00，北京时间（UTC+8）【待客户确认】。 | `01-design/routing-rules.md:138` | 客户（经张宝文 / Kim 对接） |
| 82 | 响应时限（全部【待客户确认】）： | `01-design/routing-rules.md:160` | 客户（经张宝文 / Kim 对接） |
| 83 | 同一客户同一咨询，模板最多发 2 次，间隔不少于 3 天；两次都没回就把线索状态记为 nurture 或 closed_lost，不再追发【待客户确认】。（与 02-botmaker/templates/README.md 同一口径。） | `01-design/routing-rules.md:187` | 客户（经张宝文 / Kim 对接） |
| 84 | 假设：{whatsapp_number} 为最终接入的公司号码【待客户确认】；预填文案母版为 Hi Tromox!。 | `01-design/source-tracking.md:5` | 客户（经张宝文 / Kim 对接） |
| 85 | 可选扩展【待客户确认】：面向单一市场的账号可以用当地语言的预填文案（如德语账号用 Hallo Tromox! [IG-2609D]），短码解析不受影响，语言判定还能更早生效。 | `01-design/source-tracking.md:79` | 客户（经张宝文 / Kim 对接） |
| 86 | IG-2609 / Instagram / 主页链接 / 全球 / 常驻 / 2026-09-21 / 【待客户确认】 / 示例行 | `01-design/source-tracking.md:87` | 客户（经张宝文 / Kim 对接） |
| 87 | AD-2609A / Click-to-WhatsApp / 广告组 A / 【待客户确认】 / 【待客户确认】 /  /  / 示例行 | `01-design/source-tracking.md:88` | 客户（经张宝文 / Kim 对接） |
| 88 | 产品 / prod_ / product_interest 中的产品代码小写；目录见 shared/tromox_lead/products.py【待客户确认】 / prod_mc10 /  / 上 | `01-design/tag-taxonomy.md:20` | 客户（经张宝文 / Kim 对接） |
| 89 | 优先级 / prio_ / 规则：B 端且类型为 distributor / importer / fleet 为 high，其余 B 端为 normal；C 端仅在投诉、质保争议、法律、安全类升级时为 high【待客户确认】 / prio_high /  / 上 | `01-design/tag-taxonomy.md:25` | 客户（经张宝文 / Kim 对接） |
| 90 | 假设：支持语种、工作时间、回复时限、隐私政策链接均为默认值【待客户确认】；AI Agent 可用的动作（转人工、跳转流程）与变量写入方式以试用账号实测为准【待核实】（SOURCES S-B9）。 | `02-botmaker/ai-agent-system-prompt.md:5` | 客户（经张宝文 / Kim 对接） |
| 91 | 粘贴前替换占位符：{privacy_url}、{working_hours}、{sla_b2b}、{sla_general}、{safety_line}，取值均【待客户确认】；默认值见 2.8 下方的说明。 | `02-botmaker/ai-agent-system-prompt.md:11` | 客户（经张宝文 / Kim 对接） |
| 92 | 本段待确认：支持语种清单【待客户确认】；精简版只对英语加 1 个主要语种做测试与调优，其余语种 AI 仍会应答但不在验收范围。 | `02-botmaker/ai-agent-system-prompt.md:55` | 客户（经张宝文 / Kim 对接） |
| 93 | {privacy_url} / 客户隐私政策链接 / 【待客户确认】 | `02-botmaker/ai-agent-system-prompt.md:142` | 客户（经张宝文 / Kim 对接） |
| 94 | {safety_line} / If anyone is in danger, please contact your local emergency services first. / 【待客户确认】，建议法务过目 | `02-botmaker/ai-agent-system-prompt.md:143` | 客户（经张宝文 / Kim 对接） |
| 95 | 非英语的机器人回复仅示意"语言跟随客户"，译文上线前须由母语者审核【待客户确认】。 | `02-botmaker/ai-agent-system-prompt.md:277` | 客户（经张宝文 / Kim 对接） |
| 96 | AI / {知识库答案：西班牙的试驾与购买渠道，以西班牙语作答}【待客户确认】 | `02-botmaker/ai-agent-system-prompt.md:355` | 客户（经张宝文 / Kim 对接） |
| 97 | 占位符写法：{…}，填完后删除花括号与【待客户确认】标记。 | `02-botmaker/knowledge-base-template.md:13` | 客户（经张宝文 / Kim 对接） |
| 98 | 字段说明：**ID**（分类前缀 + 序号）、**问题（EN）**、**答案**、**AI 直答**、**负责人**（起草）、**审核人**、**最后更新**。负责人与审核人的具体人选【待客户确认】。 | `02-botmaker/knowledge-base-template.md:18` | 客户（经张宝文 / Kim 对接） |
| 99 | KB-PRD-001 / Which models does Tromox currently offer? / {现售车型清单与一句话定位；车型家族名见 SOURCES 第 4 节，现售清单以客户为准}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:24` | 客户（经张宝文 / Kim 对接） |
| 100 | KB-PRD-002 / What are the main differences between the models? / {各车型面向的人群与用途，不写具体参数或写经确认的公开参数}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:25` | 客户（经张宝文 / Kim 对接） |
| 101 | KB-PRD-003 / How fast can it go and how far on a single charge? / {按车型给出对外口径；无统一口径则引导到官网车型页}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:26` | 客户（经张宝文 / Kim 对接） |
| 102 | KB-PRD-004 / How long does the battery take to charge, and what is its lifespan? / {对外口径}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:27` | 客户（经张宝文 / Kim 对接） |
| 103 | KB-PRD-005 / Do I need a licence to ride it? Can I carry a passenger? / {按国家分条；无把握的国家写"请咨询当地经销商"}【待客户确认】 / 需转人工 / 运营 / 法务或区域负责人 | `02-botmaker/knowledge-base-template.md:28` | 客户（经张宝文 / Kim 对接） |
| 104 | KB-PRD-006 / Is there an app? What can it do? / {对外口径}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:29` | 客户（经张宝文 / Kim 对接） |
| 105 | KB-PRD-007 / Where can I find manuals and specifications? / {官网链接}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:30` | 客户（经张宝文 / Kim 对接） |
| 106 | KB-PRD-008 / What is an e-motorcycle and how does it compare with a petrol one? / {通用科普口径}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:31` | 客户（经张宝文 / Kim 对接） |
| 107 | KB-BUY-001 / Is Tromox available in my country? / {已覆盖国家清单；未覆盖国家的统一说法}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:37` | 客户（经张宝文 / Kim 对接） |
| 108 | KB-BUY-002 / Where can I buy a Tromox? / {按国家分条：经销商查询页或当地总代联系方式}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:38` | 客户（经张宝文 / Kim 对接） |
| 109 | KB-BUY-003 / Can I buy online? / {对外口径}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:39` | 客户（经张宝文 / Kim 对接） |
| 110 | KB-BUY-004 / How much does it cost? / {是否有可对外说的零售指导价；没有则写"价格因国家而异，请联系当地经销商"}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:40` | 客户（经张宝文 / Kim 对接） |
| 111 | KB-BUY-005 / How do I become a Tromox dealer or distributor? / {申请流程的对外说法；AI 会先收集公司、国家、业务类型、意向车型与数量，再转销售} 【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:41` | 客户（经张宝文 / Kim 对接） |
| 112 | KB-BUY-006 / What are the requirements to become a reseller in my country? / {可对外说的基本要求；官网 FAQ 提到希望申请方已有至少 1 年的既有架构，是否沿用由销售确认}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:42` | 客户（经张宝文 / Kim 对接） |
| 113 | KB-BUY-008 / Do you offer fleet, rental or corporate purchase programmes? / {是否有此类合作及对外说法}【待客户确认】 / 需转人工 / 销售 / 销售负责人 | `02-botmaker/knowledge-base-template.md:44` | 客户（经张宝文 / Kim 对接） |
| 114 | KB-BUY-009 / How long does delivery take? / {对外口径；无统一口径则转人工}【待客户确认】 / 需转人工 / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:45` | 客户（经张宝文 / Kim 对接） |
| 115 | KB-AFS-001 / How do I contact Tromox customer support? / {售后联系渠道与受理时间；官网公开的售后邮箱见 SOURCES 第 4 节，是否沿用由客户确认}【待客户确认】 / yes / 运营 / 售后负责人 | `02-botmaker/knowledge-base-template.md:51` | 客户（经张宝文 / Kim 对接） |
| 116 | KB-AFS-002 / What does the warranty cover and for how long? / {可对外说的质保口径，按国家分条；未经审核前保持"需转人工"}【待客户确认】 / 需转人工 / 售后 / 售后负责人与法务 | `02-botmaker/knowledge-base-template.md:52` | 客户（经张宝文 / Kim 对接） |
| 117 | KB-AFS-003 / How do I make a warranty claim? / {报修流程：找谁、要准备什么材料}【待客户确认】 / yes / 售后 / 售后负责人 | `02-botmaker/knowledge-base-template.md:53` | 客户（经张宝文 / Kim 对接） |
| 118 | KB-AFS-005 / How do I maintain my vehicle? / {日常保养要点}【待客户确认】 / yes / 售后 / 售后负责人 | `02-botmaker/knowledge-base-template.md:55` | 客户（经张宝文 / Kim 对接） |
| 119 | KB-AFS-006 / How should I charge and store the battery? / {充电与存放的对外口径}【待客户确认】 / yes / 售后 / 售后负责人 | `02-botmaker/knowledge-base-template.md:56` | 客户（经张宝文 / Kim 对接） |
| 120 | KB-PRT-001 / Where can I buy spare parts? / {按国家分条：经销商或指定渠道}【待客户确认】 / yes / 运营 / 售后负责人 | `02-botmaker/knowledge-base-template.md:64` | 客户（经张宝文 / Kim 对接） |
| 121 | KB-PRT-002 / Can I buy a second or replacement battery? / {对外口径}【待客户确认】 / yes / 运营 / 售后负责人 | `02-botmaker/knowledge-base-template.md:65` | 客户（经张宝文 / Kim 对接） |
| 122 | KB-PRT-003 / Which accessories are available? / {配件清单或官网链接}【待客户确认】 / yes / 运营 / 产品负责人 | `02-botmaker/knowledge-base-template.md:66` | 客户（经张宝文 / Kim 对接） |
| 123 | KB-TRD-001 / Where can I test ride a Tromox? / {按国家分条：可试驾的经销商或预约方式}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:73` | 客户（经张宝文 / Kim 对接） |
| 124 | KB-TRD-002 / Is there a dealer or showroom near me? / {经销商查询页链接；各国经销商名单由客户提供}【待客户确认】 / yes / 运营 / 销售负责人 | `02-botmaker/knowledge-base-template.md:74` | 客户（经张宝文 / Kim 对接） |
| 125 | KB-TRD-003 / Will Tromox be at an upcoming show or event? / {近期展会与活动；无则删除本条}【待客户确认】 / yes / 运营 / 市场负责人 | `02-botmaker/knowledge-base-template.md:75` | 客户（经张宝文 / Kim 对接） |
| 126 | KB-COM-001 / Who is Tromox? Where is the company based? / {公司简介的对外口径}【待客户确认】 / yes / 运营 / 市场负责人 | `02-botmaker/knowledge-base-template.md:81` | 客户（经张宝文 / Kim 对接） |
| 127 | KB-COM-002 / Is Tromox a European brand? / {对外口径}【待客户确认】 / yes / 运营 / 市场负责人 | `02-botmaker/knowledge-base-template.md:82` | 客户（经张宝文 / Kim 对接） |
| 128 | KB-COM-003 / How can I contact Tromox for media, sponsorship or influencer cooperation? / {对外联系渠道；官网公开的媒体邮箱见 SOURCES 第 4 节，是否沿用由客户确认}【待客户确认】 / yes / 运营 / 市场负责人 | `02-botmaker/knowledge-base-template.md:83` | 客户（经张宝文 / Kim 对接） |
| 129 | KB-COM-004 / I am a supplier and want to offer my products or services. / {统一回复口径或指定邮箱}【待客户确认】 / yes / 运营 / 采购或行政 | `02-botmaker/knowledge-base-template.md:84` | 客户（经张宝文 / Kim 对接） |
| 130 | KB-COM-005 / Are you hiring? / {招聘信息入口}【待客户确认】 / yes / 运营 / 人事 | `02-botmaker/knowledge-base-template.md:85` | 客户（经张宝文 / Kim 对接） |
| 131 | KB-COM-006 / How do you use my personal data? How can I have it deleted? / {隐私政策链接与一句话说明}；删除或查询请求一律转人工处理，流程见 03-whatsapp/compliance.md【待客户确认】 / yes（仅限链接与一句话说明） / 运营 / 法务 | `02-botmaker/knowledge-base-template.md:86` | 客户（经张宝文 / Kim 对接） |
| 132 | 现售车型清单与对外卖点 / KB-PRD-001 至 KB-PRD-004 / 【待客户确认】 | `02-botmaker/knowledge-base-template.md:110` | 客户（经张宝文 / Kim 对接） |
| 133 | 各国经销商名单或经销商查询页 / KB-BUY-001、KB-BUY-002、KB-TRD-001、KB-TRD-002、KB-PRT-001 / 【待客户确认】 | `02-botmaker/knowledge-base-template.md:111` | 客户（经张宝文 / Kim 对接） |
| 134 | 可对外说的价格与质保口径 / KB-BUY-004、KB-AFS-002 / 【待客户确认】 | `02-botmaker/knowledge-base-template.md:112` | 客户（经张宝文 / Kim 对接） |
| 135 | 售后受理渠道与时间 / KB-AFS-001、KB-AFS-003 / 【待客户确认】 | `02-botmaker/knowledge-base-template.md:113` | 客户（经张宝文 / Kim 对接） |
| 136 | 隐私政策链接 / KB-COM-006 与开场话术 / 【待客户确认】 | `02-botmaker/knowledge-base-template.md:114` | 客户（经张宝文 / Kim 对接） |
| 137 | 品牌语气要求与禁用词 / 全部条目的措辞 / 【待客户确认】 | `02-botmaker/knowledge-base-template.md:115` | 客户（经张宝文 / Kim 对接） |
| 138 | 权限与交接 / 客户为所有者，各角色权限到位 / 0.5 小时 / 人员名单【待客户确认】 | `02-botmaker/setup-guide.md:29` | 客户（经张宝文 / Kim 对接） |
| 139 | 由客户用企业邮箱注册 Botmaker 账号（开账号免费，附最多 300 个初始对话额度，SOURCES S-B3）。注册邮箱用公共邮箱（如 whatsapp-admin@客户域名）而不是个人邮箱，避免人员变动后账号失联。【待客户确认】 | `02-botmaker/setup-guide.md:35` | 客户（经张宝文 / Kim 对接） |
| 140 | S1_GREETING / 一条带 3 个回复按钮的消息 / 按钮标题不超过 20 个字符，最多 3 个：Dealer/Distributor、Rider or Customer、Other；话术含 AI 身份告知与隐私政策链接 {privacy_url}【待客户确认】；**进入本状态先把变量 escalation_flag 置为 fal… | `02-botmaker/setup-guide.md:125` | 客户（经张宝文 / Kim 对接） |
| 141 | S7_AFTER_HOURS / 工作时间判断：在 Botmaker 后台的营业时间功能中【待核实】配置 {working_hours}【待客户确认】 / 非工作时间转人工时改发夜间话术，AI 继续可答 FAQ | `02-botmaker/setup-guide.md:131` | 客户（经张宝文 / Kim 对接） |
| 142 | S8_CONSENT / 可选步骤【待客户确认】：一条带 2 个按钮的消息 Yes, keep me posted / No, thanks / 写 consent_marketing；只在 C 端对话自然结束时问一次 | `02-botmaker/setup-guide.md:132` | 客户（经张宝文 / Kim 对接） |
| 143 | 发交接话术（工作时间内发 S2 或通用交接话术，非工作时间发夜间话术），其中 {sla_b2b}、{sla_general}、{working_hours} 均【待客户确认】。 | `02-botmaker/setup-guide.md:141` | 客户（经张宝文 / Kim 对接） |
| 144 | 知识库正文以英文为主库；AI 用客户的语言作答。涉及质保、退换、法律的条目，若要用当地语言的固定措辞，单独提供经审核的译文【待客户确认】。 | `02-botmaker/setup-guide.md:173` | 客户（经张宝文 / Kim 对接） |
| 145 | sales_b2b / segment=B2B 的全部转人工 / 海外销售【待客户确认】 / 响应时限见 00-client/销售接手SOP.md | `02-botmaker/setup-guide.md:186` | 客户（经张宝文 / Kim 对接） |
| 146 | support_b2c / C 端售后、质保、投诉、安全类 / 售后或运营【待客户确认】 | `02-botmaker/setup-guide.md:187` | 客户（经张宝文 / Kim 对接） |
| 147 | 销售结束会话时必须选一个结束分类，集成服务据此回写线索状态（事件回调里带 typification，SOURCES S-B6）。分类名【待核实】【待客户确认】： | `02-botmaker/setup-guide.md:209` | 客户（经张宝文 / Kim 对接） |
| 148 | 管理员（备份） / 客户运营负责人（Kim 或其指定的人）【待客户确认】 / 同上 / 避免单点 | `02-botmaker/setup-guide.md:316` | 客户（经张宝文 / Kim 对接） |
| 149 | 坐席 / 海外销售、售后【待客户确认】 / 在所属队列接会话、回消息、结束会话选分类 / Standard 套餐含 10 个坐席（SOURCES S-B3） | `02-botmaker/setup-guide.md:318` | 客户（经张宝文 / Kim 对接） |
| 150 | 假设：三条模板都按 utility（事务通知）类别提交；Meta 可能把它们改判为 marketing（营销）类，费率与发送条件随之变化【待核实】；ES / DE / FR / PT 译文为占位，语种清单与译文均【待客户确认】，须由母语者审核后再提交。 | `02-botmaker/templates/README.md:4` | 客户（经张宝文 / Kim 对接） |
| 151 | 响应时限规则见 00-client/销售接手SOP.md：工作时间内 2 小时首次回复；非工作时间进线的，下一个工作日 10:00（北京时间）前回复；周末无人值班时，周一用模板再触达。时限数值均【待客户确认】。 | `02-botmaker/templates/README.md:21` | 客户（经张宝文 / Kim 对接） |
| 152 | 每个语种单独提交 / 同名模板下按语种各建一份；语言代码（如西语、葡语的地区变体）按目标市场选【待客户确认】 | `02-botmaker/templates/README.md:30` | 客户（经张宝文 / Kim 对接） |
| 153 | 同一客户同一咨询，模板最多发 2 次，间隔不少于 3 天；两次都没回就把线索状态记为 nurture 或 closed_lost，不再追发【待客户确认】。 | `02-botmaker/templates/README.md:54` | 客户（经张宝文 / Kim 对接） |
| 154 | 假设：类别 utility；是否被 Meta 改判为 marketing【待核实】；译文与语种【待客户确认】。 | `02-botmaker/templates/tromox_info_request_v1.md:4` | 客户（经张宝文 / Kim 对接） |
| 155 | es / {ES 译文待定} / 【待客户确认】 | `02-botmaker/templates/tromox_info_request_v1.md:27` | 客户（经张宝文 / Kim 对接） |
| 156 | de / {DE 译文待定} / 【待客户确认】 | `02-botmaker/templates/tromox_info_request_v1.md:28` | 客户（经张宝文 / Kim 对接） |
| 157 | fr / {FR 译文待定} / 【待客户确认】 | `02-botmaker/templates/tromox_info_request_v1.md:29` | 客户（经张宝文 / Kim 对接） |
| 158 | pt / {PT 译文待定} / 【待客户确认】 | `02-botmaker/templates/tromox_info_request_v1.md:30` | 客户（经张宝文 / Kim 对接） |
| 159 | 同一咨询最多发 2 次，间隔不少于 3 天【待客户确认】。 | `02-botmaker/templates/tromox_info_request_v1.md:53` | 客户（经张宝文 / Kim 对接） |
| 160 | 假设：类别 utility；是否被 Meta 改判为 marketing【待核实】；译文与语种【待客户确认】；仅完整版包含本模板。 | `02-botmaker/templates/tromox_support_update_v1.md:4` | 客户（经张宝文 / Kim 对接） |
| 161 | 同一请求最多发 2 次，间隔不少于 3 天【待客户确认】。 | `02-botmaker/templates/tromox_support_update_v1.md:51` | 客户（经张宝文 / Kim 对接） |
| 162 | 测试号码 / 备用号码 1 个，走新号接入；另备 1 部装有 WhatsApp Business App（版本不低于 2.24.17）的手机与 1 个测试号，仅用于 T-1。商家认证未通过时一个商务组合最多注册 2 个号码（SOURCES S-M8），测试号接在客户的商务组合下也占名额：这两个测试号正好占满，上线号码要等认证通过（或升到 … | `02-botmaker/trial-test-plan.md:27` | 客户（经张宝文 / Kim 对接） |
| 163 | T-6 / CTWA referral 透传 / 客户有广告账户且同意时，投 1 条最小预算的 Click-to-WhatsApp 测试广告【待客户确认】；否则书面询问 Botmaker 支持。检查回调 messages[] 里是否出现 whatsappReferral 及其子键 sourceId、sourceURL、headline、b… | `02-botmaker/trial-test-plan.md:43` | 客户（经张宝文 / Kim 对接） |
| 164 | 语种分布：EN 8、DE 3、ES 3、FR 3、PT 2、IT 1。最终语种清单【待客户确认】后，把不在范围内的语种样例换成范围内的。 | `02-botmaker/trial-test-plan.md:82` | 客户（经张宝文 / Kim 对接） |
| 165 | T-6 如需投测试广告，费用由客户广告账户承担，投放前征得客户同意【待客户确认】。 | `02-botmaker/trial-test-plan.md:155` | 客户（经张宝文 / Kim 对接） |
| 166 | 假设：本文件是工程侧的合规设计说明，**不是法律意见**；欧盟隐私要求只写到"基本做法"的深度；客户以哪个主体作为数据责任方尚未确定【待客户确认】。平台条款引用见 SOURCES S-M5；账号与发送量规则已按 Meta 原文核实，见 SOURCES S-M8、S-M10；Botmaker 的 AI 数据条款见 SOURCES S-B17… | `03-whatsapp/compliance.md:4` | 客户（经张宝文 / Kim 对接） |
| 167 | 与提供方之间有数据处理协议 / 客户作为业务方"聘用 AI 提供方作为第三方服务商"，需要相应的数据处理条款 / 【待客户确认】由哪一方签 | `03-whatsapp/compliance.md:40` | 客户（经张宝文 / Kim 对接） |
| 168 | 营销类消息必须有明确的事先同意**：MVP 不发营销消息。流程里的同意步骤（S8，可选【待客户确认】）只是把同意记录进线索字段 consent_marketing，为第二阶段的主动再触达做准备；没有记录同意的客户，第二阶段也不得群发。 | `03-whatsapp/compliance.md:52` | 客户（经张宝文 / Kim 对接） |
| 169 | 数据控制者 / 摩兽的某个主体【待客户确认】 / 决定处理目的与方式；若以欧洲主体面向欧盟客户，责任关系更直接 | `03-whatsapp/compliance.md:65` | 客户（经张宝文 / Kim 对接） |
| 170 | 隐私告知 / 开场话术内放隐私政策链接 {privacy_url}；隐私政策需补充：通过 WhatsApp 处理咨询、使用 AI 助手、处理目的、保存期限、权利行使方式、联系人 / 【待客户确认】隐私政策由客户法务更新 | `03-whatsapp/compliance.md:73` | 客户（经张宝文 / Kim 对接） |
| 171 | 处理依据 / 回应咨询：基于客户请求的前期沟通或正当利益；营销：单独同意（第 2 节） / 【待客户确认】法务定性 | `03-whatsapp/compliance.md:75` | 客户（经张宝文 / Kim 对接） |
| 172 | 访问与删除请求 / 见 3.3 / 已设计，时限【待客户确认】 | `03-whatsapp/compliance.md:77` | 客户（经张宝文 / Kim 对接） |
| 173 | 跨境传输 / 见 3.4 / 【待客户确认】法务评估 | `03-whatsapp/compliance.md:78` | 客户（经张宝文 / Kim 对接） |
| 174 | 运营在 1 个工作日内登记到请求台账；法定答复期限通常为一个月【待核实】，内部目标 10 个工作日内完成【待客户确认】。 | `03-whatsapp/compliance.md:83` | 客户（经张宝文 / Kim 对接） |
| 175 | 集成服务与线索库 / 线索字段、原始回调事件 / 境外小型 VPS；面向欧盟客户时优先选欧盟区域【待客户确认】 / 05-integration/deployment.md | `03-whatsapp/compliance.md:95` | 客户（经张宝文 / Kim 对接） |
| 176 | 销售群通知（飞书或企业微信） / 线索摘要；号码默认只显示后四位 / 中国境内 / **这是一次向中国的跨境传输**：靠打码与最小化降低风险，是否还需标准合同条款等传输机制由法务评估【待客户确认】 | `03-whatsapp/compliance.md:96` | 客户（经张宝文 / Kim 对接） |
| 177 | 境内主体处理境外个人信息时，国内个人信息保护方面的要求同样需要法务一并评估【待客户确认】。 | `03-whatsapp/compliance.md:99` | 客户（经张宝文 / Kim 对接） |
| 178 | 数据保留（建议值，均【待客户确认】） | `03-whatsapp/compliance.md:101` | 客户（经张宝文 / Kim 对接） |
| 179 | 提示法务复核的清单【待客户确认】 | `03-whatsapp/compliance.md:124` | 客户（经张宝文 / Kim 对接） |
| 180 | daily_inquiries,10,30,120,个/天,【待客户确认】,日均新咨询数；月对话数 = 日均 x 30 | `03-whatsapp/cost-model-inputs.csv:2` | 客户（经张宝文 / Kim 对接） |
| 181 | b2b_share,0.10,0.15,0.20,比例,【待客户确认】,B 端咨询占比 | `03-whatsapp/cost-model-inputs.csv:3` | 客户（经张宝文 / Kim 对接） |
| 182 | ctwa_share,0.00,0.20,0.30,比例,【待客户确认】,经 Click-to-WhatsApp 广告或 Facebook 主页按钮进入的对话占比（72 小时免费） | `03-whatsapp/cost-model-inputs.csv:9` | 客户（经张宝文 / Kim 对接） |
| 183 | OTHER,其他市场,0.30,,【待客户确认】,ALL,国家构成未知：取全部官方费率市场的均值作代理（含西欧高价市场，偏保守） | `03-whatsapp/cost-model-rates.csv:7` | 客户（经张宝文 / Kim 对接） |
| 184 | 其他市场 / 30% / 0.0219（代理值） / 【待客户确认】 | `03-whatsapp/cost-model-results.md:16` | 客户（经张宝文 / Kim 对接） |
| 185 | 加权平均费率：0.0302 USD/条（Meta 基础价，未含 BSP 加价）。代理值 = 全部有官方费率的市场的算术平均（SOURCES S-M4），只用于国家构成未知的其他市场，仅作量级估算；拿到真实国家分布后按实际国家填费率。【待客户确认】 | `03-whatsapp/cost-model-results.md:18` | 客户（经张宝文 / Kim 对接） |
| 186 | cost-model-inputs.csv / 低/中/高三档的全部输入，含状态列（假设 / 【待核实】 / 【待客户确认】 / 已复核） / 是 | `03-whatsapp/cost-model.md:14` | 客户（经张宝文 / Kim 对接） |
| 187 | 费率**：各市场单价取自 Meta 官方费率卡（SOURCES S-M4，10/1 起服务消息单价等于 utility 单价）。只有国家构成未知的"其他市场"仍用代理值：全部有官方费率市场的算术平均，含德、荷等高价市场，偏保守。拿到真实国家分布后按实际国家填 cost-model-rates.csv（区域组单价见 S-M4，如西欧其他 0… | `03-whatsapp/cost-model.md:51` | 客户（经张宝文 / Kim 对接） |
| 188 | "拿到真实国家分布后按实际国家填费率。【待客户确认】", | `03-whatsapp/cost_model.py:236` | 客户（经张宝文 / Kim 对接） |
| 189 | 假设：客户已有运营 Facebook / Instagram 的商务账户【待客户确认】；未认证时的收发范围、号码数上限、显示名审核机制、认证审核时长、发送量分级与质量评级已于 2026-09-22 按 Meta 原文逐条核实（SOURCES S-M8、S-M10）；认证材料清单、提交入口、显示名命名规范等细节未逐条核对原文，仍标【待核实】… | `03-whatsapp/meta-onboarding-checklist.md:4` | 客户（经张宝文 / Kim 对接） |
| 190 | 是否已有商务账户 / 沿用现有的（运营 Facebook 主页与 Instagram 的那个），不新建重复账户；重复账户是认证被拒的常见原因 / 客户 / 【待客户确认】 | `03-whatsapp/meta-onboarding-checklist.md:23` | 客户（经张宝文 / Kim 对接） |
| 191 | 管理员 / 至少 2 名客户员工为管理员，用本人实名 Facebook 账号，开启两步验证；不使用共用或新注册的空白账号 / 客户 / 【待客户确认】 | `03-whatsapp/meta-onboarding-checklist.md:24` | 客户（经张宝文 / Kim 对接） |
| 192 | 先定用哪个主体【待客户确认】 | `03-whatsapp/meta-onboarding-checklist.md:33` | 客户（经张宝文 / Kim 对接） |
| 193 | 国家码的选择【待客户确认】 / 权衡三点：目标市场客户对号码的观感；公司能否长期持有并稳定收验证码；境内号码接入的可行性【待核实】 | `03-whatsapp/meta-onboarding-checklist.md:79` | 客户（经张宝文 / Kim 对接） |
| 194 | 必须与企业或品牌有明确关系，并与官网、社媒上的对外名称一致；建议直接用 Tromox【待客户确认】。 | `03-whatsapp/meta-onboarding-checklist.md:99` | 客户（经张宝文 / Kim 对接） |
| 195 | 保留期限 / 验收结束后按客户制度删除或归档【待客户确认】 | `04-eval/labeling-guide.md:35` | 客户（经张宝文 / Kim 对接） |
| 196 | 历史记录里有欧盟等地区居民的个人信息，导出与使用前请按 03-whatsapp/compliance.md 的要求确认合规依据【待客户确认】。 | `04-eval/labeling-guide.md:37` | 客户（经张宝文 / Kim 对接） |
| 197 | product_interest / 客户点名的车型，用产品代码、分号分隔：MC10;UKKO；代码目录 MC10、UKKO、M05、MINO、M03、PESGO【待客户确认】；没点名留空 / 运营 | `04-eval/labeling-guide.md:52` | 客户（经张宝文 / Kim 对接） |
| 198 | 请销售负责人在中秋碰面前后填好；is_valid_lead 一列按此判断，第二阶段的经销商评分也以此为起点。表中"摩兽的标准"一列全部【待客户确认】。 | `04-eval/labeling-guide.md:132` | 客户（经张宝文 / Kim 对接） |
| 199 | 主体 / 哪些类型算有效：门店、分销商、进口商、车队/租赁、线上转售、企业团购？哪些不算？ / 【待客户确认】 | `04-eval/labeling-guide.md:136` | 客户（经张宝文 / Kim 对接） |
| 200 | 市场 / 重点国家与区域；已有独家代理、暂不开放的国家 / 【待客户确认】 | `04-eval/labeling-guide.md:137` | 客户（经张宝文 / Kim 对接） |
| 201 | 经营基础 / 是否要求已有实体门店或团队、经营年限（官网对外写的是希望申请方已有至少 1 年的既有架构） / 【待客户确认】 | `04-eval/labeling-guide.md:138` | 客户（经张宝文 / Kim 对接） |
| 202 | 现有业务 / 是否要求有两轮或电动车经验；在售竞品是否影响判断 / 【待客户确认】 | `04-eval/labeling-guide.md:139` | 客户（经张宝文 / Kim 对接） |
| 203 | 采购规模 / 首单与年采购量的最低预期；低于多少按个人或团购处理 / 【待客户确认】 | `04-eval/labeling-guide.md:140` | 客户（经张宝文 / Kim 对接） |
| 204 | 资质能力 / 进口、认证、售后维修能力是否为必要条件 / 【待客户确认】 | `04-eval/labeling-guide.md:141` | 客户（经张宝文 / Kim 对接） |
| 205 | 联系人 / 需要对方提供哪些信息才值得销售跟进：公司名、职位、官网、邮箱等 / 【待客户确认】 | `04-eval/labeling-guide.md:142` | 客户（经张宝文 / Kim 对接） |
| 206 | 直接排除 / 明确不跟进的情形：个人代购、只要样车、要求寄售等 / 【待客户确认】 | `04-eval/labeling-guide.md:143` | 客户（经张宝文 / Kim 对接） |
| 207 | 优先级 / 什么样的线索要当天处理 / 【待客户确认】 | `04-eval/labeling-guide.md:144` | 客户（经张宝文 / Kim 对接） |
| 208 | 销售在 Botmaker 结束会话时选择结束分类，conversation-close 事件把它带回来，服务据此回写 status。分类名称需要在 Botmaker 后台的结束分类功能中预先建好【待核实】，名称与含义由客户销售确认【待客户确认】。 | `05-integration/botmaker-api-notes.md:87` | 客户（经张宝文 / Kim 对接） |
| 209 | 假设：日均咨询在成本模型的低到高档之间（单机足够）；服务器账号、域名解析都开在客户名下；服务器放在中国大陆以外，保证 Botmaker 能稳定回调；具体云厂商与机房【待客户确认】。 | `05-integration/deployment.md:4` | 客户（经张宝文 / Kim 对接） |
| 210 | 线索库里有个人数据：号码、姓名、公司、对话摘要。客户多在欧洲时，机房优先选欧洲经济区内，并与云厂商签数据处理协议；选其他地区前请客户法务确认。【待客户确认】 | `05-integration/deployment.md:109` | 客户（经张宝文 / Kim 对接） |
| 211 | 云厂商、机房地区、由谁开账号 / 【待客户确认】 / 客户、张宝文 | `05-integration/deployment.md:139` | 客户（经张宝文 / Kim 对接） |
| 212 | 子域名与 DNS 解析由谁操作 / 【待客户确认】 / 客户 | `05-integration/deployment.md:140` | 客户（经张宝文 / Kim 对接） |
| 213 | 通知渠道用飞书还是企业微信 / 【待客户确认】 / 客户销售 | `05-integration/deployment.md:144` | 客户（经张宝文 / Kim 对接） |
| 214 | 海外租户（Lark）的开放平台域名不同，服务的 base_url 参数目前只在代码里可改，没有环境变量；客户若用 Lark 而不是飞书，要加一个配置项。【待客户确认】 | `05-integration/feishu-bitable-setup.md:80` | 客户（经张宝文 / Kim 对接） |
| 215 | defines the close categories in Botmaker 【待核实】【待客户确认】 (see botmaker-api-notes.md). | `05-integration/webhook-service/app/normalize.py:53` | 客户（经张宝文 / Kim 对接） |
| 216 | "_note": "【待核实】结构依据 Botmaker 帮助中心的 webhook 示例（SOURCES S-B6）整理，尚未用真实回调样本核对；拿到真实样本后替换本文件并同步 app/models.py。号码、姓名、公司均为虚构。 场景：销售在 Botmaker 结束会话并选择结束分类（typification），用于回写线索状态。分… | `05-integration/webhook-service/fixtures/event_conversation_close.json:2` | 客户（经张宝文 / Kim 对接） |
| 217 | 假设：在测试号或灰度入口上执行；测试人用自己的手机号，语种列为完整版的安排；精简版只保留 2 个语种，此处以英语加德语为例，第二语种【待客户确认】；示例里的公司与人名均为虚构；用例不涉及任何参数、价格、质保条款的具体内容。 | `06-acceptance/uat-test-cases.md:4` | 客户（经张宝文 / Kim 对接） |
| 218 | U19 / 营销同意步骤 / DE / C 端问题解决后出现同意询问；会话一按 "Yes, keep me posted"，会话二按 "No, thanks" / 会话一 consent_marketing true；会话二 false；未询问的其他线索为空 / 记录后结束会话 / 无卡片 / 三种取值都正确；该步骤是否启用【待客户确认】… | `06-acceptance/uat-test-cases.md:36` | 客户（经张宝文 / Kim 对接） |
| 219 | 德语 DE / U02、U06、U19、U20 / 保留（以德语为例，第二语种【待客户确认】） | `06-acceptance/uat-test-cases.md:65` | 客户（经张宝文 / Kim 对接） |
| 220 | 假设：碰面约 2 小时；对方到场的有 Kim（海外社媒运营）、至少一位销售负责人，最好有一位能拍板账号与付款的领导【待客户确认】。 | `07-project/meeting-prep.md:4` | 客户（经张宝文 / Kim 对接） |
| 221 | 假设：摩兽业务/FDE 一方以 Kim 为对接人；摩兽销售由销售主管代表【待客户确认】；工作项与周次对应 timeline.md。 | `07-project/raci.md:5` | 客户（经张宝文 / Kim 对接） |
| 222 | R10 / **隐私合规**：客户中有欧盟用户；线索与通知会进入境内协作工具 / 中 / 高 / 开场即告知 AI 身份与隐私政策链接；只存业务必需字段；通知里号码打码；删除请求有流程；数据保留期限与跨境安排提交客户法务复核【待客户确认】 / 摩兽业务（法务对接）；集成工程师（技术措施） / 03-whatsapp/compliance.… | `07-project/risk-register.md:19` | 客户（经张宝文 / Kim 对接） |
| 223 | 代写 FAQ 内容与专业翻译（Bot 话术的多语种版本由 AI 初译、客户审校）。【待客户确认】 | `99-internal/pricing-internal.md:55` | 客户（经张宝文 / Kim 对接） |
| 224 | 车型名称（家族） / MC10（含 TrailX、StreetX）、UKKO（含 Ukko S+、UkkoPro）、M05、MINO（含 Mino B）、M03、Pesgo（含 Plus、C）。现售清单以客户提供为准【待客户确认】。 / （链接见出处） ； （链接见出处） | `SOURCES.md:76` | 客户（经张宝文 / Kim 对接） |
| 225 | 市场与网络 / 官网 FAQ 提到中国、意大利、欧洲、日本、韩国、澳大利亚、北美；另有美国站、南非站、菲律宾经销商站；欧洲站有 "Dealer Partnership Program" 与 "EU Warehouse Support"；总部杭州，欧洲服务中心在比利时鲁汶。各国经销商名单【待客户确认】。 / 同上；搜索结果中的 tromox… | `SOURCES.md:77` | 客户（经张宝文 / Kim 对接） |
| 226 | 经销申请 / 官网设经销商/分销商申请表单；FAQ 写明希望申请方"已有至少 1 年的既有架构"、有二级网络更佳。有效线索标准以销售填写的为准【待客户确认】。 / （链接见出处） | `SOURCES.md:78` | 客户（经张宝文 / Kim 对接） |
| 227 | ISO 639-1 codes the MVP bot is expected to handle. Final list is 【待客户确认】. | `shared/tromox_lead/enums.py:92` | 客户（经张宝文 / Kim 对接） |
| 228 | FieldSpec("ai_summary", "string", SRC_AI, "给销售看的一两句话摘要（默认简体中文【待客户确认】）", ai_extracted=True), | `shared/tromox_lead/fields.py:46` | 客户（经张宝文 / Kim 对接） |
| 229 | line-up must be confirmed by the client 【待客户确认】. | `shared/tromox_lead/products.py:5` | 客户（经张宝文 / Kim 对接） |
