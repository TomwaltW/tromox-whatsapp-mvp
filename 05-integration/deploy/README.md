# 回调服务部署套件

> 用途：把 `../deployment.md` 里的部署命令做成仓库里的文件——docker compose、Caddy 配置、备份 / 恢复 / 更新 / 健康告警脚本，让"一台 VPS + Docker + Caddy"照着文件起来，并能在本机用 Docker 跑一遍 smoke test。读者：集成工程师、接手运维的人。
> 选型与"为什么"（单机、不上 Kubernetes、备份策略、更新窗口）都在 `../deployment.md`，本文只讲怎么操作。

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `docker-compose.yml` | 服务 `webhook`（从仓库根目录构建镜像、只绑 127.0.0.1、日志轮转、健康检查、最小权限见第 4 节）与服务 `caddy`（profile `proxy`，不加参数不起） |
| `Caddyfile.example` | 反向代理配置：只放行三条路径、加安全头与请求体上限（第 4 节），复制为 `Caddyfile` 后改域名 |
| `backup.sh` | `backup.sh <data_dir> <backup_dir> [keep_days=30]`：`sqlite3 .backup` 在线一致性备份，删过期备份，打印备份文件路径 |
| `restore.sh` | `restore.sh <backup_file> <data_dir>`：覆盖 `leads.db`、删 `-wal` / `-shm`、留底现有库；不停起容器，只提示下一步 |
| `update.sh` | `update.sh [--no-rollback] [compose_dir]`：把当前镜像另存为 `tromox-webhook:rollback` → `git pull --ff-only` → 重建镜像 → 重建容器 → 等 `/health` 200（`TROMOX_UPDATE_WAIT_S` 秒，默认 60）。新版本不健康就**自动回滚**到上一版镜像；`--no-rollback` 只报告不回滚。退出码与回滚后怎么把代码钉回去见第 3 节「更新」 |
| `healthcheck-alert.sh` | `healthcheck-alert.sh <health_url> [alert_webhook_url]`：健康则安静退出 0；否则 stderr 报 `tromox webhook down`，POST `{"text": "..."}` 到告警地址，退出 1。设了环境变量 `TROMOX_METRICS_TOKEN` 再查 `/metrics`，回调堆积、通知失败或镜像卡住（用满重试预算）时报 `tromox webhook degraded`（第 3 节） |
| `rehearsal.sh` | `rehearsal.sh <base_url> <token> [--compose-dir DIR] [--fixture PATH] [--no-cleanup]`：上线演练，把 `../deployment.md` 第 9 节里能自动做的项跑一遍，标准输出打一张 Markdown 结果表，有 FAIL 退出 1（第 3 节） |
| `cron.example` | 三条定时任务：每 5 分钟 `app.replay`、每日备份、每 5 分钟健康检查 |
| `.gitignore` | 本目录的 `.env`、`Caddyfile`、`data/` 不进仓库 |

compose 文件里的可插值变量只从**本目录的 `.env`** 或 **shell 环境**取（`docker compose --env-file <文件>` 可以换一个文件，但 `update.sh` 与 cron 里的命令都不带它，服务器上就用本目录 `.env`）。最后一行 `TROMOX_UPDATE_WAIT_S` 是 `update.sh` 读的，不是 compose 变量：

| 变量 | 默认 | 说明 |
|---|---|---|
| `TROMOX_ENV_FILE` | `.env` | 传给容器的环境变量文件（`env_file`），**不参与插值**：它指到别处时，写在那个文件里的 `TROMOX_DATA_DIR` 等会被静默忽略。要么把这几项也 `export` 到 shell 里（第 5 节 smoke test 就是这么做的），要么每条命令都写 `docker compose --env-file <那个文件> ...` |
| `TROMOX_BIND` | `127.0.0.1` | 宿主机绑定地址；公网流量一律经反向代理进入，不要改成 0.0.0.0 |
| `TROMOX_HTTP_PORT` | `8000` | 宿主机端口 |
| `TROMOX_DATA_DIR` | `./data` | 宿主机数据目录（SQLite + CSV）；服务器上建议放仓库之外 |
| `TROMOX_FORWARDED_ALLOW_IPS` | 未设 → `*`；设成空（`TROMOX_FORWARDED_ALLOW_IPS=`）→ 谁都不信 | uvicorn 信任哪些来源发来的 `X-Forwarded-For`；什么时候要改见第 4 节 |
| `PIP_INDEX_URL` | PyPI 官方 | 只在构建镜像时用；国内网络构建慢就指向 PyPI 镜像的 `/simple`，境外服务器不需要 |
| `TROMOX_UPDATE_WAIT_S` | `60` | `update.sh` 每一轮等 `/health` 的秒数（每 2 秒查一次；回滚后再等一轮）。它不读 `.env`，要改就写在命令前：`TROMOX_UPDATE_WAIT_S=120 ./update.sh` |

## 2. 首次部署（服务器）

前提：`../deployment.md` 4.1 的基础加固已做；Docker Engine 与 Compose 插件已装（`docker compose version` 能返回）；部署用户在 `docker` 组。下面以仓库克隆在 `/opt/tromox/app`、数据在 `/opt/tromox/data` 为例，命令都在本目录执行：

```bash
cd /opt/tromox/app/05-integration/deploy
```

1. **环境变量文件**：`cp ../webhook-service/.env.example .env && chmod 600 .env`。必填 `BOTMAKER_WEBHOOK_TOKEN`（`openssl rand -hex 32` 生成）、`NOTIFIERS` 及对应群机器人地址；`DATABASE_PATH` / `CSV_EXPORT_PATH` 两行删掉（容器内路径由镜像设定）；末尾加一行 `TROMOX_DATA_DIR=/opt/tromox/data`。这份 `.env` 放在本目录，才同时给 compose 插值；别挪到别处再用 `TROMOX_ENV_FILE` 指过去（第 1 节）。
2. **数据目录**：`sudo mkdir -p /opt/tromox/data && sudo chown 10001 /opt/tromox/data`（容器以 uid 10001 运行）。
3. **起服务**：`docker compose up -d --build webhook`，然后 `docker compose ps` 看到 `healthy`。
4. **Caddyfile**：先把子域名的 A 记录指到服务器，再 `cp Caddyfile.example Caddyfile`，把 `wa-hook.<客户域名>` 换成真实子域名。
5. **起反向代理**：`docker compose --profile proxy up -d`。证书自动签发，几十秒后 `https://wa-hook.<客户域名>/health` 可访问。
6. **验证**：按 `../deployment.md` 4.6 的三条 curl 走一遍（`/health` 200、无密钥 401、样例回调 `lead_upserted`），然后到 Botmaker 侧接上（4.7）。

以后所有 `docker compose` 命令都在本目录执行；带 `--profile proxy` 才会连 Caddy 一起操作（如 `docker compose --profile proxy ps`）。

## 3. 日常运维

- **定时任务**：`crontab -e`（deploy 用户），把 `cron.example` 贴进去，改路径、域名与告警地址。三条任务分别是：每 5 分钟重放未处理事件（`app.replay`）、每日 03:15 备份并清理 30 天前的备份、每 5 分钟健康检查并告警。
- **看日志**：`docker compose logs -f webhook`（json-file，单文件 10 MB、保留 5 个）。
- **进容器跑运维命令**：`docker compose exec -T webhook python -m app.replay --export`（重放并重写 CSV）。一律在本目录用 `docker compose exec -T webhook ...`（cron 里先 `cd` 到本目录；`-T` 因为 cron 没有终端）：compose 起的容器叫 `tromox-webhook-1`（项目名-服务名-序号），按 `tromox-webhook` 这个名字 `docker exec` 会报 `No such container`——那是 `../webhook-service/README.md` 第 5 节单容器 `docker run --name` 的写法。删除请求（`app.forget`）的写法见 `../deployment.md` 第 8 节。
- **备份**：`./backup.sh /opt/tromox/data /opt/tromox/backup 30`，产出 `/opt/tromox/backup/leads-YYYY-MM-DD.db`。每天把最新备份同步到机器之外（`../deployment.md` 第 6 节）。
- **恢复**：`docker compose stop webhook` → `./restore.sh /opt/tromox/backup/leads-YYYY-MM-DD.db /opt/tromox/data` → 按脚本打印的提示 `docker compose up -d webhook`、重放并重写 CSV。上线前演练一次。
- **更新**：`./update.sh`（先把当前镜像另存为 `tromox-webhook:rollback`，再 `git pull --ff-only`、`docker compose build webhook`、`docker compose up -d webhook`、等 `/health`，默认 60 秒，`TROMOX_UPDATE_WAIT_S=120 ./update.sh` 可放宽）。放在咨询低谷做；跑完看一眼 `docker compose logs --tail 50 webhook`。按退出码处理：
  - `0`：更新成功。
  - `1`，stderr 是「更新失败，已回滚到上一版镜像」：新版本在时限内没通过 `/health`，脚本已把 `:rollback` 标回 `:latest`、`docker compose up -d --no-build webhook` 并确认旧版健康——**线上是好的**，但代码仍停在新提交。按 stderr 给的命令把代码钉回旧提交：`git -C /opt/tromox/app reset --hard <旧 sha>`（会丢掉工作区的改动，部署克隆里本来就不该有）；新版本为什么起不来看 stderr 里留底的那 50 行日志（容器已被替换，`docker compose logs` 里只剩回滚后的）。上游修好后再跑 `./update.sh`。
  - `1`，stderr 是「镜像构建失败」：线上容器没动，照样按给出的命令钉回旧提交。
  - `2`：回滚后仍不健康，或更新前没有 `tromox-webhook:latest`（首次部署，无镜像可回滚）——**线上此刻没有健康的版本**，立刻人工处理（`docker compose logs --tail 100 webhook`）。
  - 想保留坏容器排查就加 `--no-rollback`：不健康时只报告、不回滚，退出 `1`，线上停在坏版本上，手动回滚的命令 stderr 里有。

  旧镜像会积累，隔一阵 `docker image prune -f`（它只清没有标签的镜像，`:rollback` 留着）。
- **告警去哪**：`healthcheck-alert.sh` 的第二个参数是任意接收 `{"text": "..."}` JSON POST 的地址（通用 webhook）；飞书 / 企业微信群机器人要的字段不同，接它们时在中间放一个转换端点，或改脚本里 `payload` 那一行。
- **不只看进程活着**：`/health` 只查数据库能不能 ping，Token 配错、通知全失败、原始回调堆着没处理它照样 200。给 `healthcheck-alert.sh` 设环境变量 `TROMOX_METRICS_TOKEN`（值 = `.env` 里的 `BOTMAKER_WEBHOOK_TOKEN`），它在 `/health` 正常之后再带 `auth-bm-token` 头 `GET <health_url 去掉 /health>/metrics`（所以第一个参数必须以 `/health` 结尾），`raw_events_unprocessed > 0`、`notifications.failed_24h > 0` 或 `mirror_outbox_exhausted > 0`（镜像行用满重试预算卡住）就 stderr 报 `tromox webhook degraded: unprocessed=<n> failed_24h=<n> mirror_exhausted=<n>`、POST 告警、退出 1；`/metrics` 本身非 200 也算 degraded。`mirror_outbox_pending` 与 `mirror_outbox_failed_24h` 不报警：飞书故障期间积压是正常的，由每 5 分钟的 `app.replay` 消化，不是人工项。变量不设，行为与只查 `/health` 完全一样。指标口径见 `../webhook-service/README.md` 第 1 节"指标"一行。上面这些行为由 `tests/test_healthcheck_alert.py` 固定。手工跑与 cron 写法：

  ```bash
  TROMOX_METRICS_TOKEN=<BOTMAKER_WEBHOOK_TOKEN 的值> ./healthcheck-alert.sh https://wa-hook.<客户域名>/health <运维群 webhook 地址>; echo "exit=$?"
  ```

  ```
  # crontab：把 cron.example 里的健康检查那行换成这条（Token 别写进 cron.example 这类会进仓库的文件）
  */5 * * * * TROMOX_METRICS_TOKEN=<BOTMAKER_WEBHOOK_TOKEN 的值> /opt/tromox/app/05-integration/deploy/healthcheck-alert.sh https://wa-hook.<客户域名>/health <运维群 webhook 地址> 2>&1 | logger -t tromox
  ```

  收到 degraded 后怎么办：`unprocessed` 大于 0 说明重放没跟上或某条一直处理失败，`docker compose exec -T webhook python -m app.replay` 跑一遍再看日志里的 `error`；`failed_24h` 大于 0 说明群机器人地址或网络出了问题，看 `docker compose logs --tail 200 webhook | grep 'notification failed'`；`mirror_exhausted` 大于 0 说明有镜像行用满 10 次重试预算、不再自动重试，`docker compose logs --tail 200 webhook | grep 'mirror failed'` 看 `last_error`（或直接看 `/metrics`）判断是配置错了还是接口变了，**排除原因之后**再 `docker compose exec -T webhook python -m app.replay --reset-mirrors` 重置重试预算——这条不进 cron，原因没排除就重置只是再烧一轮预算。

- **上线演练**：`../deployment.md` 第 9 节那张「上线前检查」是九项人工表，其中 1–5 与 8 用 `rehearsal.sh` 自动跑。它只要 `curl` 与 `python3`（不吃仓库的 `.venv`），对着一个**正在跑**的部署发真请求：

  ```bash
  ./rehearsal.sh https://wa-hook.<客户域名> <BOTMAKER_WEBHOOK_TOKEN 的值> --compose-dir .; echo "exit=$?"
  ```

  逐项做的事：1 查 `/health`（200、`webhook_token_configured` 为 true、`database` 为 ok，并把 `notifiers` 列进说明）；2 不带密钥 POST 空 body，要 401；3 带密钥 POST 一条样例回调（默认 `../webhook-service/fixtures/message_with_variables_b2b.json`，`--fixture` 可换），要 200 且 `lead_upserted`，记下 `lead_id`；4 把同一条再发一次，要 200 且 `duplicate`；5 `docker compose restart webhook` 后等 `/health` 200（最多 60 秒），再把样例发一次、仍判 `duplicate` 才算数据还在；8 进容器 `python -m app.forget --lead-id <上一步的 id> --yes` 删掉演练线索。

  **输出怎么读**：过程日志走标准错误，标准输出只有一张 `| # | 检查项 | 结果 | 说明 |` 的表，行号就是第 9 节的 1–9，可以直接贴进验收记录。`PASS` / `FAIL` / `SKIP` 三种结果，只要有一个 `FAIL` 就退出 1，别上线；全是 `PASS` / `SKIP` 退出 0。脚本不打印 Token，说明里的长数字（号码）会被遮掉。

  **仍然是人工的**：第 3 项只验证了线索入库，**卡片是否 60 秒内到了销售群要自己看一眼**；第 6（备份恢复演练）、7（权限）、9（Botmaker 后台）脚本一律记 `SKIP`，照本节上面几条和 `../deployment.md` 第 6 节手动走。不给 `--compose-dir` 时（本机、或部署不是 compose 起的）第 5、8 项也记 `SKIP`，第 8 项会把该跑的删除命令连 `lead_id` 一起打出来，自己补一条；`--no-cleanup` 则是给了 compose 也不删，留着线索人工看卡片。

## 4. 安全基线

密钥校验（`auth-bm-token`）是主防线，下面几项是万一有人绕过前面时的减害措施，都写死在 `docker-compose.yml` 与 `Caddyfile.example` 里，照第 2 节起服务就已经生效，不用额外操作。

**容器最小权限**（`webhook` 服务）：

| 设置 | 作用 | 会不会碍事 |
|---|---|---|
| `read_only: true` | 根文件系统只读，被注入的代码写不进镜像里的任何路径 | 不会：要写的只有 `/srv/data` 卷（SQLite、CSV，CSV 的临时文件也落在同一目录）与下面的 `/tmp` |
| `tmpfs: ["/tmp"]` | `/tmp` 单独给一块内存盘 | 不会：服务与运维命令（`app.replay`、`app.forget`、`app.retention`）只写 `/srv/data`，`/tmp` 给 Python 默认临时目录兜底；重启即清 |
| `cap_drop: ["ALL"]` | 去掉全部 Linux capabilities | 不会：服务以 uid 10001 跑、只监听 8000，一个都不需要 |
| `security_opt: ["no-new-privileges:true"]` | 容器内进程拿不到更高权限 | 不会：镜像里没有 setuid 程序 |
| `pids_limit: 256` | 进程 / 线程上限 | 不会：正常负载远低于这个数；fork 炸弹拖不垮宿主机 |

`caddy` 服务同样 `cap_drop: ALL`，只补回 `NET_BIND_SERVICE`（绑 80 / 443 要它）与 `no-new-privileges`。Caddy 要写证书，所以它不设只读根文件系统。

改完 compose 想确认生效：`docker compose config` 看渲染结果，或 `docker inspect` 看容器。日常运维命令（`docker compose exec -T webhook python -m app.replay --export`、`app.forget`、`app.retention`）都在只读根文件系统下能跑，上线演练（第 3 节）跑的就是这套配置。演示卡片（`app.demo`）不在容器里跑：镜像只带 `app/`、没有 `fixtures/`，它在仓库检出里跑（`../webhook-service/README.md` 第 11 节）。

**Caddy 只放行三条路径**：`@app path /webhooks/botmaker /health /metrics`，其余一律 `respond 404`，扫描器探到的路径连上游都到不了。另外给放行的请求加了 `request_body { max_size 1MB }`（超限的体在代理这层就被拒，打不到服务）和四个安全头：`X-Content-Type-Options nosniff`、`X-Frame-Options DENY`、`Referrer-Policy no-referrer`、`Strict-Transport-Security max-age=31536000`，并删掉 `Server` 头不回显版本。以后新增对外路径，记得同时加进 `@app` 那一行，否则线上会收到 404。

**`TROMOX_FORWARDED_ALLOW_IPS`（什么时候要改）**：`ALLOWED_IPS` 拦的是"来源 IP"，而服务在反向代理后面看到的对端是 Caddy。所以镜像里 uvicorn 带 `--proxy-headers` 启动，compose 把 `FORWARDED_ALLOW_IPS` 设成 `${TROMOX_FORWARDED_ALLOW_IPS-*}` —— 只有来源在这个名单里时 `X-Forwarded-For` 才被采信，别人伪造这个头一律忽略。`-*` 前面故意不带冒号：未设取 `*`，设成空就是空串（谁的代理头都不信）；带冒号的写法在变量为空时也会取 `*`，「留空」就不生效了（`scripts/check_repo.py` 会拦）。

- 默认 `*` 的前提：8000 端口只绑 `127.0.0.1`（`TROMOX_BIND`），唯一入口是同一 compose 网络里的 Caddy，它的容器地址每次重建都变，写死没有意义。
- 把 8000 暴露到公网（`TROMOX_BIND=0.0.0.0`）、或在宿主机上直接跑 Caddy / Nginx：必须改。在本目录 `.env` 里加 `TROMOX_FORWARDED_ALLOW_IPS=<代理的固定 IP>`。宿主机跑代理时，容器看到的对端是 compose 网络 `tromox_default` 的网关（不是默认网桥的 `172.17.0.1`——服务不在那个网络上，照它配了 `ALLOWED_IPS` 的话每条回调都会 403），这样查：`docker network inspect tromox_default -f '{{(index .IPAM.Config 0).Gateway}}'`。`docker compose down` 再 `up` 会重建这个网络，子网可能重新分配，所以每次 `down` 之后都要复查一遍、对不上就改。不启用 `ALLOWED_IPS` 时也可以直接留空 `TROMOX_FORWARDED_ALLOW_IPS=`，谁的代理头都不信。
- **要改的是 `TROMOX_FORWARDED_ALLOW_IPS`**：compose 里的 `environment` 优先级高于 `env_file`，在 `.env` 里直接写 `FORWARDED_ALLOW_IPS=` 不会生效。
- 改完先 `docker compose config | grep FORWARDED_ALLOW_IPS` 看渲染值（留空时是 `""`），再 `docker compose up -d webhook` 重建容器；回归用例见 `../webhook-service/tests/test_proxy_headers.py`（可信采信 / 无头按对端判 / 伪造被忽略三种情形）。

## 5. 本机 smoke test

不占 80/443，不碰仓库里的任何目录，用完整个删掉。环境文件放在临时目录，所以 `TROMOX_*` 用 `export` 给插值（`TROMOX_ENV_FILE` 本身不参与插值，第 1 节）；项目名用 `-p tromox-smoke`，和服务器上的 `tromox` 分开：

```bash
cd 05-integration/deploy
T=$(mktemp -d); mkdir "$T/data"; chmod 777 "$T/data"         # 容器以 uid 10001 写；临时目录，省得 sudo chown
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
TROMOX_METRICS_TOKEN=local-token ./healthcheck-alert.sh http://127.0.0.1:18080/health; echo "exit=$?"   # 0、不出声（顺带查了 /metrics）

# 可选：顺带跑上线演练。rehearsal.sh 里的 docker compose 不带 -p，先用环境变量指到 smoke 这个项目；
# 上面已经发过 b2b 样例，演练换一条没发过的，否则第 3 项判 duplicate
export COMPOSE_PROJECT_NAME=tromox-smoke
./rehearsal.sh http://127.0.0.1:18080 local-token --compose-dir . --fixture ../webhook-service/fixtures/message_user_first.json; echo "exit=$?"

docker compose -p tromox-smoke down -v && rm -rf "$T"
unset TROMOX_ENV_FILE TROMOX_HTTP_PORT TROMOX_DATA_DIR COMPOSE_PROJECT_NAME   # 别让这几项留在 shell 里影响之后的 compose 命令
```

脚本单测不需要 Docker：`backup.sh` / `restore.sh` 的往返一致（写连接还开着时 WAL 里的行也在备份里）、过期备份清理、恢复后删 `-wal` / `-shm`、拒绝不是 SQLite 的备份文件，都由根目录 `tests/test_backup_restore.py` 固定（`scripts/check_all.sh` 会跑，不用手工 smoke）；`healthcheck-alert.sh` 的行为（`/health` 连不上报 `down`；设了 `TROMOX_METRICS_TOKEN` 时 `raw_events_unprocessed`、`notifications.failed_24h`、`mirror_outbox_exhausted` 任一非 0 报 `degraded`，键缺失当 0，告警地址收到 POST）由根目录 `tests/test_healthcheck_alert.py` 固定，同样随 `scripts/check_all.sh` 跑。

`update.sh` 的成功 / 回滚 / 回滚后仍不健康 / 首次部署无镜像 / `--no-rollback` 几条路径由根目录 `tests/test_update.py` 用假 `git` / 假 `docker` 固定，compose 代理头「未设 → `*`、设成空 → 空串」由 `tests/test_compose_config.py` 固定（有 Docker 时真跑 `docker compose config`，不起容器），都随 `scripts/check_all.sh` 跑，不用在 smoke test 里真的更新一次。

## 6. 与 deployment.md 的对应

| deployment.md | 本目录 |
|---|---|
| 4.2 安装 Docker、4.4 数据目录与启动 | `docker-compose.yml`、第 2 节第 2–3 步 |
| 4.3 环境变量文件 | 第 2 节第 1 步 |
| 4.5 反向代理与 TLS | `Caddyfile.example`、第 2 节第 4–5 步、第 4 节（含宿主机跑代理时按 `tromox_default` 查网关） |
| 5 定时任务 | `cron.example`、`healthcheck-alert.sh` |
| 6 备份与恢复 | `backup.sh`、`restore.sh` |
| 7 更新 | `update.sh`（自动回滚、`--no-rollback`）、第 3 节"更新" |
| 8 数据位置与隐私提示（删除请求） | 第 3 节"进容器跑运维命令"（`docker compose exec -T webhook`） |
| 9 上线前检查 | `rehearsal.sh`、第 3 节"上线演练" |
