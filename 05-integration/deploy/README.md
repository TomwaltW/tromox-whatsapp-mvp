# 回调服务部署套件

> 用途：把 `../deployment.md` 里的部署命令做成仓库里的文件——docker compose、Caddy 配置、备份 / 恢复 / 更新 / 健康告警脚本，让"一台 VPS + Docker + Caddy"照着文件起来，并能在本机用 Docker 跑一遍 smoke test。读者：集成工程师、接手运维的人。
> 选型与"为什么"（单机、不上 Kubernetes、备份策略、更新窗口）都在 `../deployment.md`，本文只讲怎么操作。

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `docker-compose.yml` | 服务 `webhook`（从仓库根目录构建镜像、只绑 127.0.0.1、日志轮转、健康检查）与服务 `caddy`（profile `proxy`，不加参数不起） |
| `Caddyfile.example` | 反向代理三行配置，复制为 `Caddyfile` 后改域名 |
| `backup.sh` | `backup.sh <data_dir> <backup_dir> [keep_days=30]`：`sqlite3 .backup` 在线一致性备份，删过期备份，打印备份文件路径 |
| `restore.sh` | `restore.sh <backup_file> <data_dir>`：覆盖 `leads.db`、删 `-wal` / `-shm`、留底现有库；不停起容器，只提示下一步 |
| `update.sh` | `update.sh [compose_dir]`：`git pull --ff-only` → 重建镜像 → 重建容器 → 等 `/health` 200（最多 60 秒） |
| `healthcheck-alert.sh` | `healthcheck-alert.sh <health_url> [alert_webhook_url]`：健康则安静退出 0；否则 stderr 报 `tromox webhook down`，POST `{"text": "..."}` 到告警地址，退出 1 |
| `cron.example` | 三条定时任务：每 5 分钟 `app.replay`、每日备份、每 5 分钟健康检查 |
| `.gitignore` | 本目录的 `.env`、`Caddyfile`、`data/` 不进仓库 |

compose 文件里四个可插值变量（写在本目录 `.env` 或 shell 环境里）：

| 变量 | 默认 | 说明 |
|---|---|---|
| `TROMOX_ENV_FILE` | `.env` | 传给容器的环境变量文件；同一个文件也给下面三项插值 |
| `TROMOX_BIND` | `127.0.0.1` | 宿主机绑定地址；公网流量一律经反向代理进入，不要改成 0.0.0.0 |
| `TROMOX_HTTP_PORT` | `8000` | 宿主机端口 |
| `TROMOX_DATA_DIR` | `./data` | 宿主机数据目录（SQLite + CSV）；服务器上建议放仓库之外 |

## 2. 首次部署（服务器）

前提：`../deployment.md` 4.1 的基础加固已做；Docker Engine 与 Compose 插件已装（`docker compose version` 能返回）；部署用户在 `docker` 组。下面以仓库克隆在 `/opt/tromox/app`、数据在 `/opt/tromox/data` 为例，命令都在本目录执行：

```bash
cd /opt/tromox/app/05-integration/deploy
```

1. **环境变量文件**：`cp ../webhook-service/.env.example .env && chmod 600 .env`。必填 `BOTMAKER_WEBHOOK_TOKEN`（`openssl rand -hex 32` 生成）、`NOTIFIERS` 及对应群机器人地址；`DATABASE_PATH` / `CSV_EXPORT_PATH` 两行删掉（容器内路径由镜像设定）；末尾加一行 `TROMOX_DATA_DIR=/opt/tromox/data`。
2. **数据目录**：`sudo mkdir -p /opt/tromox/data && sudo chown 10001 /opt/tromox/data`（容器以 uid 10001 运行）。
3. **起服务**：`docker compose up -d --build webhook`，然后 `docker compose ps` 看到 `healthy`。
4. **Caddyfile**：先把子域名的 A 记录指到服务器，再 `cp Caddyfile.example Caddyfile`，把 `wa-hook.<客户域名>` 换成真实子域名。
5. **起反向代理**：`docker compose --profile proxy up -d`。证书自动签发，几十秒后 `https://wa-hook.<客户域名>/health` 可访问。
6. **验证**：按 `../deployment.md` 4.6 的三条 curl 走一遍（`/health` 200、无密钥 401、样例回调 `lead_upserted`），然后到 Botmaker 侧接上（4.7）。

以后所有 `docker compose` 命令都在本目录执行；带 `--profile proxy` 才会连 Caddy 一起操作（如 `docker compose --profile proxy ps`）。

## 3. 日常运维

- **定时任务**：`crontab -e`（deploy 用户），把 `cron.example` 贴进去，改路径、域名与告警地址。三条任务分别是：每 5 分钟重放未处理事件（`app.replay`）、每日 03:15 备份并清理 30 天前的备份、每 5 分钟健康检查并告警。
- **看日志**：`docker compose logs -f webhook`（json-file，单文件 10 MB、保留 5 个）。
- **进容器跑运维命令**：`docker compose exec -T webhook python -m app.replay --export`（重放并重写 CSV）。
- **备份**：`./backup.sh /opt/tromox/data /opt/tromox/backup 30`，产出 `/opt/tromox/backup/leads-YYYY-MM-DD.db`。每天把最新备份同步到机器之外（`../deployment.md` 第 6 节）。
- **恢复**：`docker compose stop webhook` → `./restore.sh /opt/tromox/backup/leads-YYYY-MM-DD.db /opt/tromox/data` → 按脚本打印的提示 `docker compose up -d webhook`、重放并重写 CSV。上线前演练一次。
- **更新**：`./update.sh`（等价于 `git pull --ff-only`、`docker compose build webhook`、`docker compose up -d webhook`、等 `/health`）。放在咨询低谷做；跑完看一眼 `docker compose logs --tail 50 webhook`。旧镜像会积累，隔一阵 `docker image prune -f`。
- **告警去哪**：`healthcheck-alert.sh` 的第二个参数是任意接收 `{"text": "..."}` JSON POST 的地址（通用 webhook）；飞书 / 企业微信群机器人要的字段不同，接它们时在中间放一个转换端点，或改脚本里 `payload` 那一行。

## 4. 本机 smoke test

不占 80/443，不碰仓库里的任何目录，用完整个删掉：

```bash
cd 05-integration/deploy
T=$(mktemp -d); mkdir "$T/data"
printf 'BOTMAKER_WEBHOOK_TOKEN=local-token\nNOTIFIERS=\nLOG_LEVEL=INFO\n' > "$T/.env"
export TROMOX_ENV_FILE="$T/.env" TROMOX_HTTP_PORT=18080 TROMOX_DATA_DIR="$T/data"

docker compose -p tromox-smoke up -d --build webhook
curl -s http://127.0.0.1:18080/health                       # 期望 200，webhook_token_configured 为 true
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:18080/webhooks/botmaker \
  -H "content-type: application/json" --data '{}'           # 期望 401
curl -s -X POST http://127.0.0.1:18080/webhooks/botmaker \
  -H "auth-bm-token: local-token" -H "content-type: application/json" \
  --data @../webhook-service/fixtures/message_with_variables_b2b.json   # 期望 lead_upserted
docker compose -p tromox-smoke restart webhook && sleep 3 && curl -s http://127.0.0.1:18080/health
ls "$T/data"                                                # leads.db、leads.csv
./healthcheck-alert.sh http://127.0.0.1:18080/health; echo "exit=$?"   # 0、不出声

docker compose -p tromox-smoke down -v && rm -rf "$T"
```

脚本单测不需要 Docker：`backup.sh` / `restore.sh` 对任意 SQLite 文件都能跑，`healthcheck-alert.sh` 对一个返回 503 的地址应退出 1 并在 stderr 打印 `tromox webhook down`。

## 5. 与 deployment.md 的对应

| deployment.md | 本目录 |
|---|---|
| 4.2 安装 Docker、4.4 数据目录与启动 | `docker-compose.yml`、第 2 节第 2–3 步 |
| 4.3 环境变量文件 | 第 2 节第 1 步 |
| 4.5 反向代理与 TLS | `Caddyfile.example`、第 2 节第 4–5 步 |
| 5 定时任务 | `cron.example`、`healthcheck-alert.sh` |
| 6 备份与恢复 | `backup.sh`、`restore.sh` |
| 7 更新 | `update.sh` |
