# UAT 端到端用例

> 用途：上线验收用的 20 个端到端场景，对应 `acceptance-criteria.md` 的 B1 至 B6。读者：集成工程师（执行）、客户运营与销售（见证并签字）、张宝文。
> 假设：在测试号或灰度入口上执行；测试人用自己的手机号，语种列为完整版的安排；精简版只保留 2 个语种，此处以英语加德语为例，第二语种【待客户确认】；示例里的公司与人名均为虚构；用例不涉及任何参数、价格、质保条款的具体内容。

## 1. 执行说明

1. 每个用例从一个干净的会话开始（换测试号，或先结束上一个会话）。
2. "期望分类"核对线索库里的字段；"期望动作"核对 Bot 的回复与 Botmaker 后台状态；"期望通知"核对销售群。
3. 话术逐字比对 `01-design/conversation-flow.md`；非英语场景比对已确认的译文。
4. 通知时延用手机秒表，从发出最后一条触发消息算到卡片出现在群里。
5. 全部 20 个通过才算 B1 通过；任何一个失败，修复后该用例与受影响用例重测。

## 2. 用例表

| # | 场景 | 语种 | 输入 | 期望分类 | 期望动作 | 期望通知 | 通过标准 |
|---|---|---|---|---|---|---|---|
| U01 | B 端经销商顺利路径 | EN | 经 Instagram 链接发送 `Hi Tromox! [IG-2609]`；按 "Dealer/Distributor"；一条消息给出：公司 Moto Nord GmbH、德国、经销商两家门店、对 MC10 与 UKKO 感兴趣、每季度约 20 台、联系人 Anna Keller、店主 | `segment` B2B；`b2b_type` dealer；`country_stated` DE；`product_interest` MC10、UKKO；`volume` 有值；`escalation_reason` b2b_qualified；`source_code` IG-2609；`source_channel` instagram | 开场问候带三个按钮；一次问齐话术；字段收齐后发 S2 交接话术一次；该会话停用 AI；建工单并进销售队列 | 销售群收到 1 张卡片：国家、类型、公司、产品、数量、中文摘要、窗口截止时间、回 Botmaker 的链接；号码只显示后四位 | 字段全部正确；Bot 共发 3 条消息；卡片 60 秒内到达 |
| U02 | B 端分销商，不按按钮直接打字，并索要价目表 | DE | `Hallo, wir sind ein Großhändler in Österreich und möchten Tromox exklusiv vertreiben. Bitte senden Sie uns Ihre Händlerpreisliste.` | `segment` B2B；`b2b_type` distributor；`country_stated` AT；`language` de；`escalation_reason` price_negotiation | 用德语回复价格与质保守卫话术；不给出任何价格；转人工 | 1 张卡片，原因显示价格谈判，优先级 high | 回复中没有价格数字；原因按优先级取 price_negotiation 而不是 b2b_qualified |
| U03 | B 端信息不全，追问不超过 2 次 | ES | 按 "Dealer/Distributor"；回复 `Tengo una tienda de motos`；之后按 Bot 的追问依次补充公司名与国家 | 追问前 `escalation_flag` false；补齐后 `segment` B2B、`b2b_type` dealer、`escalation_reason` b2b_qualified | Bot 只追问缺失的必填项，追问不超过 2 次；补齐后发交接话术 | 补齐后 1 张卡片；补齐前无卡片 | 追问次数不超过 2；没有重复问已回答的内容 |
| U04 | 按钮与文字矛盾 | EN | 按 "Rider or Customer"；随后发送 `Actually I own three motorcycle shops in Australia and want to import a container of your bikes.` | `segment` 改判 B2B；`b2b_type` importer；`country_stated` AU；`ai_confidence` 低于按钮直选时的取值 | 转入 B 端信息收集或直接转人工 | 线索最终到达销售群，1 张卡片 | 没有被当作 C 端处理；销售收到该线索 |
| U05 | C 端购买咨询 | EN | 按 "Rider or Customer"；按 "Buy / Find a dealer"；发送 `Where can I buy a MINO in Italy?` | `segment` B2C；`b2c_intent` buy；`product_interest` MINO；`country_stated` IT；`escalation_flag` false | 依据知识库一条消息作答；知识库无该国经销商信息时按守卫流程转人工 | 知识库能答时无卡片 | 回答内容全部出自知识库；Bot 消息不超过 5 条 |
| U06 | C 端试驾，只说城市 | DE | `Kann ich die MC10 in Hamburg Probe fahren?` | `segment` B2C；`b2c_intent` test_ride；`product_interest` MC10；`city_region` Hamburg；`country_stated` 为空；国家取号码国家码；`language` de | 用德语依据知识库作答 | 无卡片 | `country_stated` 没有被从城市推断出来；回复语言为德语 |
| U07 | C 端售后支持 | ES | `Mi Ukko no carga, ¿qué hago?` | `segment` B2C；`b2c_intent` support；`product_interest` UKKO；`language` es | 用西语依据知识库给出排查指引；知识库没有则转人工 | 知识库能答时无卡片 | 不编造知识库以外的技术指引 |
| U08 | 安全类投诉立即升级 | ES | `La batería de mi moto echa humo, necesito ayuda urgente` | `escalation_flag` true；`escalation_reason` complaint_warranty_legal_safety；标签含 prio_high | 立即转人工；不尝试自行排查；非工作时间用 S7 话术且不邀请继续提问 | 1 张卡片，优先级 high | 卡片 60 秒内到达；Bot 不尝试远程排查，也不作任何赔付或质保承诺 |
| U09 | 明确要求真人 | EN | `Can I talk to a real person please?` | `escalation_reason` human_requested | 发一般转人工话术一次；该会话停用 AI | 1 张卡片 | 话术与母版逐字一致；之后 AI 不再插话 |
| U10 | 价格谈判守卫 | EN | `What is your best dealer price for 10 units? Any discount?` | `escalation_reason` price_negotiation | 发价格与质保守卫话术；不报价；转人工 | 1 张卡片 | 回复中没有任何价格或折扣数字 |
| U11 | 质保承诺守卫 | FR | `Quelle est la garantie de la batterie ? Pouvez-vous me garantir un remplacement gratuit ?` | `segment` B2C；`b2c_intent` warranty；知识库无明确条款时 `escalation_flag` true | 只复述知识库里明确允许对外的表述；要求承诺的部分发守卫话术并转人工 | 转人工时 1 张卡片 | 回复中没有知识库以外的质保条款或承诺 |
| U12 | 话题收口 | EN | `Write me a poem about Bitcoin` | `segment` unknown；`escalation_flag` false | 发话题收口话术；不作答无关内容 | 无卡片 | 话术与母版逐字一致；没有生成诗歌 |
| U13 | 连续两次没听懂 | PT | 连续发送两条无意义内容，如 `asdf qwer` 与 `zzzz 1234` | `escalation_reason` not_understood_twice | 第二次后发"没听懂两次"话术并转人工 | 1 张卡片 | 第一次未转人工，第二次转人工 |
| U14 | 低置信度送人工 | EN | 不按按钮，发送 `I might want some bikes for my business, not sure yet` | `segment` B2B；`ai_confidence` 低于 0.6；`escalation_reason` low_confidence | 转人工，由销售判断 | 1 张卡片，原因显示 AI 拿不准 | 没有被直接判为 C 端后丢弃 |
| U15 | 短码解析的变体 | EN | 会话一：首条消息 `hi tromox tt-2610b`（小写、无方括号）；会话二：删掉预填文案只发 `Hello` | 会话一：`source_code` TT-2610B、`source_channel` tiktok；会话二：`source_code` 为空、`source_channel` unknown | 两个会话都正常进入开场问候 | 无要求 | 线索库两条记录的来源字段与期望一致 |
| U16 | 非工作时间转人工 | EN | 在北京时间工作时间之外发送 `I need to speak to someone about my order` | `escalation_reason` human_requested | 发 S7 非工作时间话术，含工作时间与跟进时限；AI 仍可继续答 FAQ | 卡片立即发出，不等到上班 | 话术含 `{working_hours}` 的实际取值；销售在下一个工作日北京时间 10:00 前回复 |
| U17 | 重复回调不产生重复线索 | 系统 | 把 U01 的同一条 webhook 回调原样重放两次 | 线索库仍只有 1 条该号码的线索 | 集成服务两次都返回成功 | 不产生新卡片 | 线索数为 1；通知数为 1 |
| U18 | 窗口关闭后走模板 | EN | 取一条已交接的 B 端测试线索，超过 24 小时不回复；销售再尝试联系 | 线索 `status` 保持 handed_off，回复后变 contacted | 自由回复不可用；销售发送模板 `tromox_sales_followup_v1`；测试客户回复后窗口重开，销售转回自由回复 | 无要求 | 模板已通过 Meta 审核并成功送达；客户回复后可自由回复 |
| U19 | 营销同意步骤 | DE | C 端问题解决后出现同意询问；会话一按 "Yes, keep me posted"，会话二按 "No, thanks" | 会话一 `consent_marketing` true；会话二 false；未询问的其他线索为空 | 记录后结束会话 | 无卡片 | 三种取值都正确；该步骤是否启用【待客户确认】，不启用则本用例改为验证字段恒为空 |
| U20 | 通知时延与卡片内容 | DE | 按 "Dealer/Distributor"；发送 `Wir sind ein Lieferdienst in Berlin, Deutschland, und brauchen etwa 30 Roller für unsere Flotte. Firma: FlottExpress, Ansprechpartner Jonas Weber, Einkaufsleiter.` | `segment` B2B；`b2b_type` fleet；`country_stated` DE；`city_region` Berlin；`company` FlottExpress；`contact_name` Jonas Weber；`escalation_reason` b2b_qualified；标签含 prio_high | 用德语发交接话术 | 1 张卡片，字段齐全，摘要为简体中文，号码打码 | 从发出该消息到卡片出现不超过 60 秒，测 3 次取最大值 |

## 3. 覆盖核对

| 要求 | 覆盖用例 |
|---|---|
| 升级原因 `b2b_qualified` | U01、U03、U20 |
| 升级原因 `price_negotiation` | U02、U10 |
| 升级原因 `complaint_warranty_legal_safety` | U08、U11 |
| 升级原因 `human_requested` | U09、U16 |
| 升级原因 `not_understood_twice` | U13 |
| 升级原因 `low_confidence` | U14 |
| 话题收口 | U12 |
| 价格与质保守卫 | U02、U10、U11 |
| 短码解析 | U01、U15 |
| 非工作时间 | U08、U16 |
| 重复回调（幂等） | U17 |
| 24 小时窗口与模板 | U18 |
| 营销同意 | U19 |
| 通知时延不超过 60 秒 | U01、U08、U20 |
| 国家不由 AI 猜 | U06 |
| 按钮与文字矛盾 | U04 |

## 4. 语种安排

| 语种 | 完整版用例 | 精简版 |
|---|---|---|
| 英语 EN | U01、U04、U05、U09、U10、U12、U14、U15、U16、U18 | 保留 |
| 德语 DE | U02、U06、U19、U20 | 保留（以德语为例，第二语种【待客户确认】） |
| 西语 ES | U03、U07、U08 | 改用英语或第二语种执行，场景逻辑不变 |
| 法语 FR | U11 | 同上 |
| 葡语 PT | U13 | 同上 |
| 系统 | U17 | 保留 |

完整版覆盖 5 个语种，满足不少于 3 个语种的要求；精简版 20 个场景全部保留，只是语种收缩为 2 个。

## 5. 执行记录

现场记录表由 `scripts/gen_uat_sheet.py` 生成（命令见脚本头部），填完后归档到 `dist/` 之外的项目文件夹。

| # | 执行日期 | 执行人 | 结果（通过 / 失败） | 问题与修复 | 见证人 |
|---|---|---|---|---|---|
| U01 至 U20 | 计划 2026-10-30 起 | | | | |
