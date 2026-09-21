# 来源追踪

> 用途：wa.me 短码方案、各渠道链接生成表、Click-to-WhatsApp 广告 referral 的记录方式、报表口径与失效情形。读者：集成工程师、客户运营（负责生成与登记链接）。
> 机器实现：`shared/tromox_lead/shortcode.py`；字段定义见 `lead-schema.md`（`source_channel`、`source_code`、`referral`）。
> 假设：`{whatsapp_number}` 为最终接入的公司号码【待客户确认】；预填文案母版为 `Hi Tromox!`。

## 1. 为什么第一版就做

MVP 要验证的是"社媒流量能不能变成有效线索"。不知道线索从哪个渠道、哪条帖子来，就无法回答哪类内容值得继续投。短码方案不依赖任何平台能力，成本是每条链接多几个字符。

## 2. 短码格式

`[<前缀>-<YYMM><后缀>]`，例：`[IG-2609]`、`[TT-2610B]`。

| 部分 | 规则 | 例 |
|---|---|---|
| 前缀 | 渠道，2 至 3 个大写字母，取值见下表 | `IG` |
| `YYMM` | 链接创建的年月，4 位数字 | `2609` = 2026 年 9 月 |
| 后缀 | 可选，1 至 3 位字母或数字，用来区分同月的不同帖子、素材或市场 | `A`、`DE1` |
| 方括号 | 生成时带上，便于肉眼辨认；解析时可有可无 | |

| 前缀 | `source_channel` | 用在哪 |
|---|---|---|
| `IG` | `instagram` | Instagram 主页链接、帖子、Reels、Story 贴纸 |
| `FB` | `facebook` | Facebook 帖子与主页链接 |
| `TT` | `tiktok` | TikTok 主页链接 |
| `YT` | `youtube` | YouTube 视频描述与频道页 |
| `WEB` | `website` | 官网悬浮按钮、联系页 |
| `AD` | `ctwa_ad` | Click-to-WhatsApp 广告的预填消息 |
| `QR` | `offline_qr` | 展会、门店、包装上的二维码 |
| `OT` | `other` | 邮件签名、合作方等其他入口 |

## 3. 解析行为

与 `parse_source_code` 的实现逐条对应：

| 行为 | 例 | 结果 |
|---|---|---|
| 标准写法 | `Hi Tromox! [IG-2609]` | `IG-2609`，`instagram` |
| 不区分大小写，方括号可省 | `hola tt-2610b quiero info` | `TT-2610B`，`tiktok` |
| 带后缀 | `[ig-2609a]` | `IG-2609A`，`instagram` |
| 短码前后紧贴字母或数字则不匹配，避免误中普通单词 | `BIG-2609 deal` | 无短码，`unknown` |
| 数字位数不对不匹配 | `IG-26091234` | 无短码，`unknown` |
| 缺连字符不匹配 | `IG 2609` | 无短码，`unknown` |
| 未知前缀不匹配 | `[XX-2609]` | 无短码，`unknown` |
| 没有短码 | `Hello` | 无短码，`unknown` |

其他约定：

1. 短码统一转大写后入库。
2. 送给语言检测与 AI 的文本会先去掉短码（`strip_source_code`），避免干扰。
3. **首次来源优先**：一个号码第一次带来的短码记为该线索的来源，之后再带别的短码不覆盖。（集成服务按此实现；重复来访的渠道分布另看原始事件。）
4. 登记表里查不到的新短码，渠道仍可由前缀得出；每周抽查时补登记。

## 4. 链接生成

格式：`https://wa.me/{whatsapp_number}?text=<URL 编码后的预填文案>`。

1. `{whatsapp_number}` 用国际格式的纯数字：带国家码，不带加号、空格、括号、连字符、开头的 0。
2. 预填文案必须做 URL 编码：空格写成 `%20`，感叹号写成 `%21`，左右方括号写成 `%5B`、`%5D`。
3. 生成方法：`build_prefill("IG-2609")` 得到 `Hi Tromox! [IG-2609]`，再用任意 URL 编码工具处理；或直接套用下表。
4. 发布前用手机点一次，确认 WhatsApp 输入框里出现完整的预填文案。

| 渠道与位置 | 短码示例 | 预填文案 | 链接 |
|---|---|---|---|
| Instagram 主页链接 | `IG-2609` | `Hi Tromox! [IG-2609]` | `https://wa.me/{whatsapp_number}?text=Hi%20Tromox%21%20%5BIG-2609%5D` |
| Instagram 单条帖子或 Story | `IG-2609A` | `Hi Tromox! [IG-2609A]` | `https://wa.me/{whatsapp_number}?text=Hi%20Tromox%21%20%5BIG-2609A%5D` |
| Facebook 帖子 | `FB-2609` | `Hi Tromox! [FB-2609]` | `https://wa.me/{whatsapp_number}?text=Hi%20Tromox%21%20%5BFB-2609%5D` |
| TikTok 主页链接 | `TT-2609` | `Hi Tromox! [TT-2609]` | `https://wa.me/{whatsapp_number}?text=Hi%20Tromox%21%20%5BTT-2609%5D` |
| YouTube 视频描述 | `YT-2609` | `Hi Tromox! [YT-2609]` | `https://wa.me/{whatsapp_number}?text=Hi%20Tromox%21%20%5BYT-2609%5D` |
| 官网按钮 | `WEB-2609` | `Hi Tromox! [WEB-2609]` | `https://wa.me/{whatsapp_number}?text=Hi%20Tromox%21%20%5BWEB-2609%5D` |
| Click-to-WhatsApp 广告 | `AD-2609A` | `Hi Tromox! [AD-2609A]` | 不走 wa.me；在广告设置的预填消息里填这段文案 |
| 线下二维码 | `QR-2609` | `Hi Tromox! [QR-2609]` | `https://wa.me/{whatsapp_number}?text=Hi%20Tromox%21%20%5BQR-2609%5D`，再生成二维码 |
| 其他入口 | `OT-2609` | `Hi Tromox! [OT-2609]` | `https://wa.me/{whatsapp_number}?text=Hi%20Tromox%21%20%5BOT-2609%5D` |

说明：

- Facebook 主页自带的 WhatsApp 按钮不支持预填文案，来源只能靠 referral 数据（第 6 节）或记为 `unknown`。经该按钮进入的会话与 Click-to-WhatsApp 广告一样享有 72 小时免费入口（SOURCES S-M1）。
- 可选扩展【待客户确认】：面向单一市场的账号可以用当地语言的预填文案（如德语账号用 `Hallo Tromox! [IG-2609D]`），短码解析不受影响，语言判定还能更早生效。

## 5. 短码登记表

由客户运营维护，建议放在线索库同一个表格工具里。每新建一条链接登记一行。

| 短码 | 渠道 | 位置或帖子 | 目标市场 | 活动或素材 | 创建日期 | 负责人 | 备注 |
|---|---|---|---|---|---|---|---|
| `IG-2609` | Instagram | 主页链接 | 全球 | 常驻 | 2026-09-21 | 【待客户确认】 | 示例行 |
| `AD-2609A` | Click-to-WhatsApp | 广告组 A | 【待客户确认】 | 【待客户确认】 | | | 示例行 |

规则：一条链接一个短码；同一帖子换文案不换短码；下线的短码不复用。

## 6. Click-to-WhatsApp 广告 referral

Meta 在广告带来的首条消息上附带 referral 数据（来源类型、广告 id、来源 URL、标题、正文、点击 id）。线索结构里已留好 `referral` 对象，字段为 `source_type`、`source_id`、`source_url`、`headline`、`body`、`ctwa_clid`。Botmaker 回调字段表里的对应对象只有 `sourceId`、`sourceURL`、`headline`、`body` 四个子键，没有来源类型与点击 id；`ctwa_clid` 在 Botmaker 帮助中心与 API 描述文件中都未出现（SOURCES S-B12）。所以经 Botmaker 接入时，`source_type` 与 `ctwa_clid` 预计留空，以真实样本为准【待核实】。

| 事项 | 现状 |
|---|---|
| Botmaker 是否把 referral 明细放进 webhook 回调 | 【待核实】帮助中心回调字段表列有 `messages[].whatsappReferral`（子键 `sourceId`、`sourceURL`、`headline`、`body`），但同文 JSON 示例里没有这个对象，真实回调未见（SOURCES S-B6、S-B12）；广告 referral 写进哪个会话变量也未见明文（变量清单只列了 Messenger 的 referral 变量）。试用账号第一周用真实样本核对（`02-botmaker/trial-test-plan.md`） |
| 集成服务现状 | 只识别名为 `referral` 的对象（顶层或消息内），照字段表写法到达的 `whatsappReferral` 读不到。本轮不改代码：拿到真实样本、核对对象名与层级后，再决定是否解析、怎么映射 |
| Botmaker 自带的广告来源能力 | 有 "Click to WhatsApp Dashboards"，会识别来源为广告 referral 的会话（SOURCES S-B12），可在后台看广告维度的会话数 |
| 透传成立且服务读得到时（对象名就是 `referral`，或已按样本补上 `whatsappReferral` 的解析） | 集成服务把 referral 写入线索，`source_channel` 记 `ctwa_ad`；同时有短码时两者都保留 |
| 透传不成立时 | 靠广告预填消息里的 `AD-` 短码区分素材；广告维度的统计看 Botmaker 后台 |

## 7. 报表口径

统计周期默认按周；时间取 `first_message_ts`，按北京时间切周。

| 指标 | 定义 | 维度 |
|---|---|---|
| 线索数 | 周期内首次来访的去重号码数（一个号码一条线索） | `source_channel`、`source_code`、国家 |
| B 端占比 | `segment` = `B2B` 的线索数 ÷ 线索数 | 同上 |
| 已交接数 | `escalation_reason` = `b2b_qualified` 且已通知销售的线索数 | 同上 |
| 有效线索率 | 销售接手后结束分类不是 `not_a_lead` 的线索数 ÷ 已交接且已有结束分类的线索数 | 同上 |
| 未知来源占比 | `source_channel` = `unknown` 的线索数 ÷ 线索数 | 整体 |

读法：

1. 有效线索率按渠道、按短码比，才能回答"哪类内容带来的是真经销商"。
2. 未知来源占比是追踪方案自身的健康指标；持续高于三成，说明有入口没挂短码，或客户习惯删掉预填文案，需要回头检查链接。
3. "有效"的标准以销售填写的有效线索标准为准（`04-eval/labeling-guide.md`）。

## 8. 失效情形

| 情形 | 结果 | 应对 |
|---|---|---|
| 客户删掉或改写预填文案 | `source_code` 为空，`source_channel` = `unknown` | 接受；用未知来源占比监控 |
| 客户保存号码后直接发消息 | 同上 | 同上 |
| 链接被转发，第三人点击 | 记到原短码名下 | 接受；属于该内容的传播效果 |
| 同一人先后从多个渠道来 | 只记首次来源 | 设计如此，见第 3 节 |
| 链接未做 URL 编码，预填文案被截断 | 短码不完整，解析失败 | 发布前手机实测 |
| 新建链接没登记 | 渠道仍可由前缀得出，登记表缺行 | 每周抽查时补登记 |
| Facebook 主页按钮进入 | 无预填文案 | 依赖 referral；不透传则为 `unknown` |
