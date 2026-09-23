# 飞书多维表格线索镜像：设置说明

> 用途：把回调服务的线索库镜像到一张飞书多维表格（Bitable），让销售在飞书里直接看线索。本文说明在飞书开放平台建自建应用、授权、建表、填四个环境变量、验证的每一步。读者：集成工程师，以及客户方负责飞书管理员权限的人。
> 前提：SQLite 仍是账本，多维表格只是镜像；镜像写失败只记日志，不影响线索入库与通知。接口形态按飞书开放平台的公开文档整理，尚未用真实租户跑通，第 7 节列了上线前要对一遍的点。

## 1. 它做什么

回调服务每次更新一条线索，就按 `lead_id` 在多维表格里找这条线索的行：找到就更新，没找到就新建。一条线索永远只占一行，字段名与线索库一致（`shared/tromox_lead` 的 `LEAD_FIELDS`）。销售在表里加视图、筛选、加自己的备注列都不受影响，服务只写它认识的那些列。

启用方式：`STORAGE_BACKENDS=sqlite,csv,feishu_bitable`，再把第 5 节的四个变量填齐。四个变量缺任何一个，服务启动即报错退出，不会悄悄丢线索。

## 2. 在飞书开放平台建自建应用

1. 用客户租户的管理员账号登录飞书开放平台（`https://open.feishu.cn`；海外租户是 Lark 开放平台 `https://open.larksuite.com`，见第 7 节），进入「开发者后台」，选「创建企业自建应用」。名字建议「Tromox 线索镜像」，图标随意。
2. 打开应用的「凭证与基础信息」页，记下 **App ID** 与 **App Secret**。App Secret 只显示一次，当场存进密码管理器；泄漏就在这一页重置。
3. 「权限管理」页，搜索并开通多维表格相关权限：**查看、评论、编辑和管理多维表格**（权限标识以 `bitable:app` 开头的那一条）。只开这一条即可，不要开通讯录、消息类权限。
4. 「版本管理与发布」页，创建一个版本并申请发布；管理员在「管理后台」审核通过后应用才可用。可用范围选「全员」或只选一个部门都行，因为服务用的是应用自己的身份（租户令牌），不代表任何用户。

## 3. 建多维表格并把应用加为协作者

1. 在飞书里新建一个多维表格（不要用「导入 Excel」建，导入的列类型往往是文本）。把默认数据表改名为「线索」。
2. 按第 4 节的表建列。**列名必须与字段名逐字一致**（小写加下划线），类型按表里写的选；单选、多选的选项可以不预先添加，飞书会在首次写入时自动补选项（若租户关闭了这项设置，就把第 4 节列出的枚举值先加上）。
3. 表格右上角「...」→「添加文档应用」（部分版本叫「更多 → 添加应用」），搜索第 2 节建的应用，授予 **可编辑**。没做这一步时，服务会收到「没有权限」类错误码，日志里会看到 `feishu_bitable: search code=...`。
4. 从浏览器地址栏取两个标识。多维表格的网址结构是 `https://<租户域名>.feishu.cn/base/<app_token>?table=<table_id>&view=<view_id>`：
   - `/base/` 后面那一段（以 `bascn` 或 `bas` 开头的字符串）就是 **app_token**；
   - `table=` 后面那一段（以 `tbl` 开头）就是 **table_id**。
   若网址是 `/wiki/` 开头（表格建在知识库里），需要在表格右上角「...」→「复制链接」拿 `/base/` 形式的地址，或把表格移出知识库；知识库节点的 token 不能直接当 app_token 用（见第 7 节）。

## 4. 每列的名字与类型

| 列名（逐字） | 飞书列类型 | 写入的值 |
|---|---|---|
| `lead_id` | 文本 | 线索主键，服务用它找行；**建议设为主字段**（表格第一列） |
| `phone`、`contact_name`、`profile_name`、`company`、`role`、`city_region`、`volume`、`existing_dealer_relationship`、`source_code`、`ai_summary`、`assigned_to`、`notes` | 文本 | 字符串原样 |
| `segment` | 单选 | `B2B`、`B2C`、`unknown` |
| `b2b_type` | 单选 | `dealer`、`distributor`、`fleet`、`importer`、`other` |
| `b2c_intent` | 单选 | `buy`、`support`、`parts`、`warranty`、`test_ride`、`other` |
| `status` | 单选 | `new`、`qualified`、`handed_off`、`contacted`、`closed_won`、`closed_lost`、`nurture`、`invalid` |
| `source_channel` | 单选 | `instagram`、`facebook`、`tiktok`、`youtube`、`website`、`ctwa_ad`、`offline_qr`、`other`、`unknown` |
| `escalation_reason` | 单选 | `human_requested`、`b2b_qualified`、`low_confidence`、`complaint_warranty_legal_safety`、`price_negotiation`、`not_understood_twice` |
| `language`、`country_by_phone`、`country_stated` | 单选 | ISO 代码（`de`、`DE` 这类两字母） |
| `product_interest`、`tags` | 多选 | 字符串列表（产品代码 / 标签名） |
| `ai_confidence` | 数字 | 0 到 1 的小数，格式选「保留两位小数」 |
| `escalation_flag`、`consent_marketing` | 复选框 | 布尔 |
| `first_message_ts`、`last_message_ts` | 日期 | 毫秒时间戳，飞书按表格所在时区显示；勾选「显示时间」 |
| `referral` | 文本 | JSON 字符串（广告 referral 原文） |

值为 null 的字段不写入：例如 C 端线索的 `b2b_type` 为空时，该格保持空白，不会被写成字符串 `null`。单选列收到一个不在选项里的值时，飞书会自动新增选项。

## 5. 四个环境变量

| 变量 | 取自 |
|---|---|
| `FEISHU_APP_ID` | 开放平台 → 应用 → 凭证与基础信息 → App ID（`cli_` 开头） |
| `FEISHU_APP_SECRET` | 同页 App Secret；密钥，只放 `.env` 或部署平台的密钥配置 |
| `FEISHU_BITABLE_APP_TOKEN` | 表格网址 `/base/` 后的那段 |
| `FEISHU_BITABLE_TABLE_ID` | 表格网址 `table=` 后的那段（`tbl` 开头） |

可选：`FEISHU_BASE_URL`，开放平台地址，要写完整来源（带 `https://`，不带路径）：默认 `https://open.feishu.cn`；海外 Lark 租户填 `https://open.larksuite.com`（见第 7 节）；留空即默认值。只写域名、不带 `https://` 时服务拒绝启动，启动日志会写明。

再把 `STORAGE_BACKENDS` 改成 `sqlite,csv,feishu_bitable`。服务的日志与错误信息不会输出 App Secret 与租户令牌。

## 6. 验证

1. 起服务（本地 `uvicorn app.main:create_app --factory`，或 Docker，见回调服务 README 第 3、5 节），看 `GET /health` 的 `storage` 列表里有 `feishu_bitable`。四个变量缺一个时服务不会起来，启动日志会写明缺哪个。
2. 发一条 fixture：

   ```bash
   curl -s -X POST http://127.0.0.1:8000/webhooks/botmaker \
     -H "auth-bm-token: $BOTMAKER_WEBHOOK_TOKEN" -H "Content-Type: application/json" \
     --data @05-integration/webhook-service/fixtures/message_with_variables_b2b.json
   ```

   期望：响应 `{"status": "lead_upserted", ...}`；表格里多出一行，`segment` 是 `B2B`，`product_interest` 是两个选项，`first_message_ts` 显示成日期。
3. 把同一个 fixture 再发一次（或改一个变量再发）：表里**仍是一行**，内容被更新，不会多出重复行。这就是按 `lead_id` 查找后更新的效果。
4. 故意把 `FEISHU_BITABLE_TABLE_ID` 改错再发一条：响应仍是 `lead_upserted`（账本照常，应答不等飞书），几秒后服务日志有一行 `mirror failed`，`sink` 为 `feishu_bitable`，`/metrics` 的 `mirror_outbox_pending` 加 1。改回来之后不用再发：这一行留在 `mirror_outbox` 里，每 5 分钟一次的 `python -m app.replay` 会把它补发（等不及就手动跑一次）；连失败 10 次的行会停在 `mirror_outbox_exhausted` 里，排查 `last_error` 之后用 `python -m app.replay --reset-mirrors` 重置再补发。

## 7. 上线前要用真实租户对一遍的点

- 接口路径、请求体与返回体按飞书开放平台公开文档整理（租户令牌、记录查询 `records/search`、记录创建、记录更新），未用真实租户跑通。尤其是查询接口的 filter 写法与「单选列自动补选项」的行为。【待核实】
- 日期列接受毫秒时间戳、复选框列接受布尔、多选列接受字符串数组，是按文档写的；若某列类型建错（例如把日期建成文本），写入会报错码，日志里能看到。【待核实】
- 海外租户（Lark）的开放平台地址不同：国内飞书用默认的 `https://open.feishu.cn` 即可，Lark 租户要把 `FEISHU_BASE_URL` 设成 `https://open.larksuite.com` 这个完整来源（带 https，只写域名服务会拒绝启动）；客户用的是飞书还是 Lark 要客户说明。【待客户确认】
- 频控：飞书对单个应用的写接口有每秒次数限制，MVP 的线索量远低于该限制；历史导入一次写几千行时要分批。【待核实】
- 建在知识库里的多维表格，其网址 token 是知识库节点的，不能直接当 app_token；需要把表格移出知识库或换用节点接口取 app_token。【待核实】
