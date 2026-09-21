# FAQ 知识库模板

> 用途：AI 只按知识库回答，这份模板就是知识库的源文件：客户按条填答案、走完审核再导入 Botmaker；填好的版本存回本仓库（反锁定）。读者：客户运营（填写与维护）、客户业务负责人（审核）、集成工程师（导入）。
> 假设：问题清单是起步用的建议项，部分问题取自摩兽官网公开 FAQ 的标题（SOURCES 第 4 节），**答案一律留空由客户提供**；本模板不含任何参数、价格、质保条款。主库用英文写，AI 会用客户的语言作答。

## 1. 填写规则

1. 一条只答一个问题，答案控制在 80 个英文单词以内，能直接发给客户；WhatsApp 里每条消息都计费，答案要"一条说清"。
2. 只写**对外可以说**的内容。经销价、折扣、返点、独家条款、内部交期一律不写。
3. 涉及国家差异的内容（渠道、驾照与上牌要求、质保期限）按国家分条写，条目 ID 后加国家码，如 `KB-BUY-002-DE`。没写到的国家，AI 会说明不确定并转人工。
4. "可否由 AI 直接回答"只有两个取值：`yes`（导入知识库）或 `需转人工`（**不导入**，AI 遇到就转人工）。拿不准就填 `需转人工`。
5. 质保、退换货、法律、安全类条目，必须由业务负责人逐字审核后才能标 `yes`；AI 不会在知识库原文之外多说一个字，所以原文要写完整。
6. 占位符写法：`{…}`，填完后删除花括号与【待客户确认】标记。
7. 需要固定当地语言措辞的条目（如质保声明），在"备注"里附经审核的译文；其余由 AI 翻译。

## 2. 条目表

字段说明：**ID**（分类前缀 + 序号）、**问题（EN）**、**答案**、**AI 直答**、**负责人**（起草）、**审核人**、**最后更新**。负责人与审核人的具体人选【待客户确认】。

### 2.1 产品（KB-PRD）

| ID | 问题（EN） | 答案 | AI 直答 | 负责人 | 审核人 | 最后更新 |
|---|---|---|---|---|---|---|
| KB-PRD-001 | Which models does Tromox currently offer? | {现售车型清单与一句话定位；车型家族名见 SOURCES 第 4 节，现售清单以客户为准}【待客户确认】 | yes | 运营 | 产品负责人 | |
| KB-PRD-002 | What are the main differences between the models? | {各车型面向的人群与用途，不写具体参数或写经确认的公开参数}【待客户确认】 | yes | 运营 | 产品负责人 | |
| KB-PRD-003 | How fast can it go and how far on a single charge? | {按车型给出对外口径；无统一口径则引导到官网车型页}【待客户确认】 | yes | 运营 | 产品负责人 | |
| KB-PRD-004 | How long does the battery take to charge, and what is its lifespan? | {对外口径}【待客户确认】 | yes | 运营 | 产品负责人 | |
| KB-PRD-005 | Do I need a licence to ride it? Can I carry a passenger? | {按国家分条；无把握的国家写"请咨询当地经销商"}【待客户确认】 | 需转人工 | 运营 | 法务或区域负责人 | |
| KB-PRD-006 | Is there an app? What can it do? | {对外口径}【待客户确认】 | yes | 运营 | 产品负责人 | |
| KB-PRD-007 | Where can I find manuals and specifications? | {官网链接}【待客户确认】 | yes | 运营 | 产品负责人 | |
| KB-PRD-008 | What is an e-motorcycle and how does it compare with a petrol one? | {通用科普口径}【待客户确认】 | yes | 运营 | 产品负责人 | |

### 2.2 购买与经销（KB-BUY）

| ID | 问题（EN） | 答案 | AI 直答 | 负责人 | 审核人 | 最后更新 |
|---|---|---|---|---|---|---|
| KB-BUY-001 | Is Tromox available in my country? | {已覆盖国家清单；未覆盖国家的统一说法}【待客户确认】 | yes | 运营 | 销售负责人 | |
| KB-BUY-002 | Where can I buy a Tromox? | {按国家分条：经销商查询页或当地总代联系方式}【待客户确认】 | yes | 运营 | 销售负责人 | |
| KB-BUY-003 | Can I buy online? | {对外口径}【待客户确认】 | yes | 运营 | 销售负责人 | |
| KB-BUY-004 | How much does it cost? | {是否有可对外说的零售指导价；没有则写"价格因国家而异，请联系当地经销商"}【待客户确认】 | yes | 运营 | 销售负责人 | |
| KB-BUY-005 | How do I become a Tromox dealer or distributor? | {申请流程的对外说法；AI 会先收集公司、国家、业务类型、意向车型与数量，再转销售} 【待客户确认】 | yes | 运营 | 销售负责人 | |
| KB-BUY-006 | What are the requirements to become a reseller in my country? | {可对外说的基本要求；官网 FAQ 提到希望申请方已有至少 1 年的既有架构，是否沿用由销售确认}【待客户确认】 | yes | 运营 | 销售负责人 | |
| KB-BUY-007 | What are your dealer prices, MOQ, payment terms or exclusivity conditions? | 不写答案：一律转销售 | 需转人工 | 销售 | 销售负责人 | |
| KB-BUY-008 | Do you offer fleet, rental or corporate purchase programmes? | {是否有此类合作及对外说法}【待客户确认】 | 需转人工 | 销售 | 销售负责人 | |
| KB-BUY-009 | How long does delivery take? | {对外口径；无统一口径则转人工}【待客户确认】 | 需转人工 | 运营 | 销售负责人 | |

### 2.3 售后与质保（KB-AFS）

| ID | 问题（EN） | 答案 | AI 直答 | 负责人 | 审核人 | 最后更新 |
|---|---|---|---|---|---|---|
| KB-AFS-001 | How do I contact Tromox customer support? | {售后联系渠道与受理时间；官网公开的售后邮箱见 SOURCES 第 4 节，是否沿用由客户确认}【待客户确认】 | yes | 运营 | 售后负责人 | |
| KB-AFS-002 | What does the warranty cover and for how long? | {可对外说的质保口径，按国家分条；未经审核前保持"需转人工"}【待客户确认】 | 需转人工 | 售后 | 售后负责人与法务 | |
| KB-AFS-003 | How do I make a warranty claim? | {报修流程：找谁、要准备什么材料}【待客户确认】 | yes | 售后 | 售后负责人 | |
| KB-AFS-004 | My vehicle or battery has a problem. What should I do? | 不写排查步骤以外的承诺；涉及冒烟、起火、事故、受伤的一律转人工 | 需转人工 | 售后 | 售后负责人 | |
| KB-AFS-005 | How do I maintain my vehicle? | {日常保养要点}【待客户确认】 | yes | 售后 | 售后负责人 | |
| KB-AFS-006 | How should I charge and store the battery? | {充电与存放的对外口径}【待客户确认】 | yes | 售后 | 售后负责人 | |
| KB-AFS-007 | I want a refund or I want to return my vehicle. | 不写答案：一律转人工 | 需转人工 | 售后 | 售后负责人 | |
| KB-AFS-008 | My local dealer does not respond. What can I do? | 不写答案：记为投诉并转人工 | 需转人工 | 售后 | 售后负责人 | |

### 2.4 配件（KB-PRT）

| ID | 问题（EN） | 答案 | AI 直答 | 负责人 | 审核人 | 最后更新 |
|---|---|---|---|---|---|---|
| KB-PRT-001 | Where can I buy spare parts? | {按国家分条：经销商或指定渠道}【待客户确认】 | yes | 运营 | 售后负责人 | |
| KB-PRT-002 | Can I buy a second or replacement battery? | {对外口径}【待客户确认】 | yes | 运营 | 售后负责人 | |
| KB-PRT-003 | Which accessories are available? | {配件清单或官网链接}【待客户确认】 | yes | 运营 | 产品负责人 | |
| KB-PRT-004 | Are parts from other brands or models compatible? | 不写答案：涉及安全，转人工 | 需转人工 | 售后 | 售后负责人 | |

### 2.5 试驾与门店（KB-TRD）

| ID | 问题（EN） | 答案 | AI 直答 | 负责人 | 审核人 | 最后更新 |
|---|---|---|---|---|---|---|
| KB-TRD-001 | Where can I test ride a Tromox? | {按国家分条：可试驾的经销商或预约方式}【待客户确认】 | yes | 运营 | 销售负责人 | |
| KB-TRD-002 | Is there a dealer or showroom near me? | {经销商查询页链接；各国经销商名单由客户提供}【待客户确认】 | yes | 运营 | 销售负责人 | |
| KB-TRD-003 | Will Tromox be at an upcoming show or event? | {近期展会与活动；无则删除本条}【待客户确认】 | yes | 运营 | 市场负责人 | |

### 2.6 公司与联系方式（KB-COM）

| ID | 问题（EN） | 答案 | AI 直答 | 负责人 | 审核人 | 最后更新 |
|---|---|---|---|---|---|---|
| KB-COM-001 | Who is Tromox? Where is the company based? | {公司简介的对外口径}【待客户确认】 | yes | 运营 | 市场负责人 | |
| KB-COM-002 | Is Tromox a European brand? | {对外口径}【待客户确认】 | yes | 运营 | 市场负责人 | |
| KB-COM-003 | How can I contact Tromox for media, sponsorship or influencer cooperation? | {对外联系渠道；官网公开的媒体邮箱见 SOURCES 第 4 节，是否沿用由客户确认}【待客户确认】 | yes | 运营 | 市场负责人 | |
| KB-COM-004 | I am a supplier and want to offer my products or services. | {统一回复口径或指定邮箱}【待客户确认】 | yes | 运营 | 采购或行政 | |
| KB-COM-005 | Are you hiring? | {招聘信息入口}【待客户确认】 | yes | 运营 | 人事 | |
| KB-COM-006 | How do you use my personal data? How can I have it deleted? | {隐私政策链接与一句话说明}；删除或查询请求一律转人工处理，流程见 `03-whatsapp/compliance.md`【待客户确认】 | yes（仅限链接与一句话说明） | 运营 | 法务 | |

## 3. 审核与发布流程

| 步骤 | 做什么 | 谁 | 产出 |
|---|---|---|---|
| 1 起草 | 在本模板里新增或修改条目，填"负责人"与日期 | 运营 | 待审条目 |
| 2 审核 | 逐字确认可以对外说；质保、退换、法律、安全、价格类必须由对应负责人审核 | 业务负责人 | 审核人签名与日期 |
| 3 导入 | 把标 `yes` 的条目导入 Botmaker 知识库；标 `需转人工` 的不导入 | 运营（培训后）或集成工程师 | 平台内生效 |
| 4 抽测 | 每个新增或修改的条目用 3 种问法各问一次，至少 1 次用非英语 | 运营 | 抽测记录 |
| 5 归档 | 在第 4 节登记；把最新全文存回仓库 | 运营 | 更新记录 |

时限建议：普通条目 2 个工作日内走完；纠错类（AI 说错了）当天处理。每周抽查对话时发现知识库没覆盖的高频问题，进入下一轮起草，流程见 `00-client/运维手册.md`。

## 4. 更新记录

| 日期 | 条目 ID | 变更内容 | 起草人 | 审核人 | 是否已导入 | 抽测结果 |
|---|---|---|---|---|---|---|
| 2026-09-21 | 全部 | 建立模板，答案待客户填写 | 集成工程师 | | 否 | |

## 5. 还需要客户提供的素材

| 素材 | 用在哪些条目 | 状态 |
|---|---|---|
| 现售车型清单与对外卖点 | KB-PRD-001 至 KB-PRD-004 | 【待客户确认】 |
| 各国经销商名单或经销商查询页 | KB-BUY-001、KB-BUY-002、KB-TRD-001、KB-TRD-002、KB-PRT-001 | 【待客户确认】 |
| 可对外说的价格与质保口径 | KB-BUY-004、KB-AFS-002 | 【待客户确认】 |
| 售后受理渠道与时间 | KB-AFS-001、KB-AFS-003 | 【待客户确认】 |
| 隐私政策链接 | KB-COM-006 与开场话术 | 【待客户确认】 |
| 品牌语气要求与禁用词 | 全部条目的措辞 | 【待客户确认】 |
