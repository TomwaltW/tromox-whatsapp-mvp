# 集成服务部署

> 用途：把 `webhook-service` 部署成 Botmaker 可以回调的公网 HTTPS 服务的分步说明，含月成本、备份、更新与数据位置提示。读者：集成工程师。
> 假设：日均咨询在成本模型的低到高档之间（单机足够）；服务器账号、域名解析都开在客户名下；服务器放在中国大陆以外，保证 Botmaker 能稳定回调；具体云厂商与机房【待客户确认】。

## 1. 选型结论

**境外小型 VPS + Docker + 自动签发证书的反向代理。** 理由：

| 方案 | 优点 | 问题 | 结论 |
|---|---|---|---|
| 小型 VPS（1 vCPU / 1 GB 内存 / 20 GB 磁盘级别） | 有持久磁盘，SQLite 直接可用；固定出口、固定域名；排障直观；月费固定 | 需要自己做系统更新与备份（本文第 6、7 节） | **MVP 采用** |
| Serverless（云函数或容器按需实例） | 免运维、按量计费 | 本地磁盘是临时的，SQLite 不能用，要换托管数据库并改存储适配器；冷启动与并发实例让"同号码串行合并"变复杂 | 不采用；二期接 CRM、不再需要本地库时再评估 |

不上 Kubernetes，不拆微服务：一台机器、一个容器、一个 SQLite 文件。

## 2. 月成本

| 项 | 月费 | 说明 |
|---|---|---|
| VPS | 约 6 至 12 USD | 与 `03-whatsapp/cost-model-inputs.csv` 的 `hosting_usd_per_month`（低、中档 6 USD，高档 12 USD）一致；具体厂商报价【待核实】 |
| 域名 | 0 | 用客户现有域名的一个子域名（如 `wa-hook.<客户域名>`） |
| TLS 证书 | 0 | 反向代理自动签发与续期 |
| 备份存储 | 约 0 至 1 USD | SQLite 文件很小；放客户自己的对象存储或第二台机器 |
| Botmaker webhook 功能 | 单价未公开【待核实】 | 额外计费、默认关闭的功能，不开就收不到回调（SOURCES S-B5）；计在 Botmaker 账单里，不属于本机费用 |

第三方费用由客户直付，账单在客户名下。

## 3. 账号与权限

1. 云服务器账号、域名解析由**客户**开通并持有所有者权限；我方只拿一个可回收的子账号或一把 SSH 公钥。
2. 服务器上的 `.env`（含 webhook 密钥与群机器人地址）只有部署用户可读（权限 600），不进仓库、不进聊天记录。
3. 项目结束或更换服务方时：客户删除我方子账号与 SSH 公钥，轮换 `BOTMAKER_WEBHOOK_TOKEN` 与群机器人地址即可完成交接。

## 4. 部署步骤

以下以 Ubuntu LTS 为例，命令在服务器上执行。

### 4.1 基础加固

```bash
adduser --disabled-password deploy && usermod -aG sudo deploy      # 日常不用 root
# 把 SSH 公钥放进 /home/deploy/.ssh/authorized_keys，然后在 sshd_config 里关闭密码登录与 root 登录
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable
apt-get update && apt-get install -y unattended-upgrades sqlite3    # 自动安全更新；sqlite3 用于备份
```

4.2 到 4.5 的文件都在 `deploy/` 目录：`deploy/docker-compose.yml`（服务定义）、`deploy/Caddyfile.example`（反向代理）与几个运维脚本，逐步操作见 `deploy/README.md` 第 2 节；本节只保留每一步的用意。

### 4.2 安装 Docker 并取回代码

按 Docker 官方文档为该发行版安装 Docker Engine 与 Compose 插件（`docker compose version` 能返回），把 deploy 用户加进 `docker` 组。仓库克隆到 `/opt/tromox/app`，之后所有 `docker compose` 命令都在 `/opt/tromox/app/05-integration/deploy` 目录执行。镜像不再手动 `docker build`：compose 文件里写了构建上下文（仓库根目录）与 Dockerfile 路径，`docker compose up --build` 会构建。

### 4.3 环境变量文件

`deploy/.env`（由 `webhook-service/.env.example` 复制，权限 600，已被 `.gitignore` 排除）同时做两件事：作为 `env_file` 传给容器，也给 compose 文件里的 `TROMOX_*` 变量插值（数据目录、端口、绑定地址）。必填 `BOTMAKER_WEBHOOK_TOKEN`（`openssl rand -hex 32` 生成）、`NOTIFIERS` 及对应的群机器人地址；容器内路径已由镜像设定，`DATABASE_PATH` / `CSV_EXPORT_PATH` 两行删掉；加一行 `TROMOX_DATA_DIR=/opt/tromox/data`，把数据放在仓库之外。

### 4.4 数据目录与启动

服务器上用绑定挂载，备份与取 CSV 都方便；容器以 uid 10001 运行，目录要 `chown 10001` 交给它。`docker compose up -d --build webhook` 起服务。compose 文件里已经写死的几项及其理由：端口只绑 `127.0.0.1`，公网流量一律经反向代理进入；`restart: unless-stopped`，机器重启后自动拉起；日志驱动 json-file、单文件 10 MB、保留 5 个，就是日志轮转；健康检查与镜像里的一样查 `/health`。日志是 JSON 结构化的，不含完整号码与消息正文。

### 4.5 反向代理与 TLS

推荐 Caddy，配置三行，证书自动签发与续期。先把子域名的 A 记录指到服务器，再把 `deploy/Caddyfile.example` 复制为 `deploy/Caddyfile`、改域名，`docker compose --profile proxy up -d` 起代理。Caddy 跑在同一个 compose 网络里，所以上游写服务名 `webhook:8000`；不加 `--profile proxy` 时 Caddy 不会起，本机 smoke test 因此不占 80 / 443。改在宿主机上直接跑 Caddy（systemd）也可以，上游改成 `127.0.0.1:8000`；用 Nginx 则是 `proxy_pass http://127.0.0.1:8000;` 加 certbot 签发证书。

如果启用了 `ALLOWED_IPS`：容器看到的对端是 Caddy 容器（宿主机跑 Caddy 时则是 Docker 网桥网关）而不是真实来源，需要让 uvicorn 信任反向代理传来的 `X-Forwarded-For`。在 `.env` 里加 `FORWARDED_ALLOW_IPS`：Caddy 在 compose 里时其地址会随重建变化，写 `*` 即可（8000 端口只绑 127.0.0.1，只有 Caddy 与本机能到达）；宿主机跑 Caddy 时写网桥网关 IP（`docker network inspect bridge` 可查，常见为 `172.17.0.1`）。不启用 `ALLOWED_IPS` 时不需要这一步，密钥校验才是主防线。

### 4.6 验证

```bash
curl -s https://wa-hook.<客户域名>/health
# 期望：{"status":"ok", ... "webhook_token_configured":true, ...}

curl -s -o /dev/null -w "%{http_code}\n" -X POST https://wa-hook.<客户域名>/webhooks/botmaker \
  -H "content-type: application/json" --data '{}'
# 期望：401（没带密钥被拒）

curl -s -X POST https://wa-hook.<客户域名>/webhooks/botmaker \
  -H "auth-bm-token: <密钥>" -H "content-type: application/json" \
  --data @05-integration/webhook-service/fixtures/message_with_variables_b2b.json
# 期望：lead_upserted，销售群收到一张卡片；验证后删除这条测试线索（见第 8 节）
```

### 4.7 在 Botmaker 侧接上

webhook 是 Botmaker 的额外计费功能，默认不开，先在账户设置里开通；同一渠道只能挂 1 个（SOURCES S-B5）。然后在 Settings > Integrations > Botmaker API 的 Webhooks 区域填回调地址 `https://<子域名>/webhooks/botmaker` 与同一个 Token，勾选项见 `botmaker-api-notes.md` 第 4 节。用测试号发一条消息，确认服务日志（`docker compose logs -f webhook`）出现 `callback processed`。

## 5. 定时任务

三条任务写在 `deploy/cron.example`，贴进 deploy 用户的 `crontab -e` 后改路径、域名与告警地址：每 5 分钟 `app.replay`（重放未处理事件、重试失败通知）；每日 03:15 `deploy/backup.sh`（备份并清理 30 天前的备份）；每 5 分钟 `deploy/healthcheck-alert.sh`（查 `/health`，不健康就 POST 到运维群机器人并写系统日志）。

健康检查失败要能通知到人：`healthcheck-alert.sh` 的第二个参数就是运维群机器人（或任何接收 JSON POST）的地址，不填则只写本机系统日志。理由：Botmaker 的 webhook 在 10 分钟内失败超过 100 次会熔断，接下来 10 分钟停发，这段时间的消息丢失；单条失败是否重试也还不知道（SOURCES S-B5）。这些回调没有落盘，`app.replay` 补不回，只能按 `botmaker-api-notes.md` 第 7 节对账。所以服务停摆要在几分钟内发现，处理路径也保持"先落盘、尽快应答、通知放到响应之后"。`/health` 只查数据库：Token 未配置、Token 与 Botmaker 侧不一致或 `ALLOWED_IPS` 过期时它照样返回 200，回调却全被拒（503 / 401 / 403），同样收不到、同样没落盘；所以每次改配置或更新后，还要看一眼 Botmaker 后台 webhook 的错误与被拒计数（`botmaker-api-notes.md` 第 4 节）。

## 6. 备份与恢复

1. `deploy/backup.sh <数据目录> <备份目录> [保留天数]` 用 `sqlite3 ... ".backup"` 做在线一致性备份（库开了 WAL，不要直接拷贝正在写的文件），并删除过期备份；cron 每日调用。
2. 每天把最新备份同步到机器之外（客户的对象存储或第二台机器）；备份里有客户号码与姓名，存放位置的访问权限与主库一致。
3. 恢复：停容器（`docker compose stop webhook`），`deploy/restore.sh <备份文件> <数据目录>` 用备份覆盖 `leads.db` 并删除同目录下的 `leads.db-wal` 与 `leads.db-shm`（现有库会留底一份），然后按脚本打印的提示启动容器、执行一次 `app.replay --export` 重建 CSV。
4. 上线前做一次恢复演练，写进上线检查清单。

## 7. 更新

`deploy/update.sh`：`git pull --ff-only` → `docker compose build webhook` → `docker compose up -d webhook` → 等 `/health` 返回 200（最多 60 秒），任一步失败退出非 0。

切换有数秒不可用。Botmaker 对单条回调失败是否重试尚不清楚【待核实】；若不重试，这几秒里的回调会丢失，`app.replay` 也补不回（它只重放已落盘的事件）。数秒的切换一般碰不到熔断线（10 分钟内失败超过 100 次，SOURCES S-B5）。所以更新放在咨询低谷（北京时间上午，欧美的深夜）进行；更新后看一眼 `/health` 与最近日志。表结构用 `CREATE TABLE IF NOT EXISTS` 建立，线索以 JSON 存放，升级字段不需要迁移脚本。

## 8. 数据位置与隐私提示

1. 线索库里有个人数据：号码、姓名、公司、对话摘要。客户多在欧洲时，机房优先选欧洲经济区内，并与云厂商签数据处理协议；选其他地区前请客户法务确认。【待客户确认】
2. 库里不存完整聊天记录：回调原文在处理成功后即清空（`KEEP_RAW_PAYLOADS` 只在试用期为采集真实样本临时打开）。
3. 发到销售群的卡片默认只显示号码后四位，详情回 Botmaker 看；飞书、企业微信的服务器在中国，卡片内容等于出境数据，这也是默认打码的原因。
4. CSV 导出含个人数据：只放在服务器数据目录，按需下载，不挂公开链接。
5. 删除请求：用 `app.forget` 命令按号码一次删除账本（线索、通知记录、保留期内的原始回调）、CSV 与多维表格镜像，同时在 Botmaker 后台处理对应会话；流程见 `03-whatsapp/compliance.md`。备份里的副本按第 6 节的保留期自然过期，命令不处理备份。

```bash
# 先预演（只打印会删什么，不改任何东西），确认后加 --yes 执行；输出与日志里只有 lead_id，不出现号码
docker exec tromox-webhook python -m app.forget --phone +<E.164 号码> --dry-run
docker exec tromox-webhook python -m app.forget --phone +<E.164 号码> --yes
```

## 9. 上线前检查

下面 9 项里，1–5 与 8 可以用 `deploy/rehearsal.sh` 对着正在跑的部署自动跑一遍，打出一张同样行号的结果表，有 FAIL 就退出 1（第 3 项的"卡片 60 秒内到群里"仍要人工看一眼；6、7、9 是纯人工项）：

```bash
cd 05-integration/deploy
./rehearsal.sh https://wa-hook.<客户域名> <BOTMAKER_WEBHOOK_TOKEN 的值> --compose-dir .; echo "exit=$?"
```

不带 `--compose-dir` 时第 5、8 项记 SKIP（脚本不碰容器，只把该跑的删除命令打出来）。用法与输出怎么读在 `deploy/README.md` 第 3 节。

| # | 检查项 | 通过标准 |
|---|---|---|
| 1 | `/health` | 200，`webhook_token_configured` 为 true，`notifiers` 列出所选渠道 |
| 2 | 无密钥请求 | 401 |
| 3 | 样例回调 | 线索入库，销售群收到卡片，从收到回调到卡片送达不超过 60 秒 |
| 4 | 重复回调 | 返回 `duplicate`，群里没有第二张卡片 |
| 5 | 重启容器 | 数据仍在，`/health` 正常 |
| 6 | 备份与恢复演练 | 用前一日备份恢复成功 |
| 7 | 权限 | `.env` 为 600；服务器无密码登录；我方子账号可随时回收 |
| 8 | 测试数据 | 验证用的线索已删除，CSV 已重写 |
| 9 | Botmaker 侧 webhook | 已开通并指向正式地址；联调结束后，后台错误日志里没有新增的错误或被拒记录 |

## 10. 待确认

| 事项 | 标记 | 负责人 |
|---|---|---|
| 云厂商、机房地区、由谁开账号 | 【待客户确认】 | 客户、张宝文 |
| 子域名与 DNS 解析由谁操作 | 【待客户确认】 | 客户 |
| 所选厂商的实际月费是否落在 6 至 12 USD | 【待核实】 | 集成工程师 |
| Botmaker 单条回调失败的重试策略（决定更新窗口的宽严；熔断规则已知，SOURCES S-B5） | 【待核实】 | 集成工程师 |
| Botmaker webhook 功能的单价 | 【待核实】 | 集成工程师 |
| 通知渠道用飞书还是企业微信 | 【待客户确认】 | 客户销售 |
