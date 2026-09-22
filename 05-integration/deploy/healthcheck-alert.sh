#!/usr/bin/env bash
# 健康检查 + 告警：/health 返回 200 且 status 为 ok → 进程活着；否则 stderr 报 down，
# 给了告警地址就 POST 一条 {"text": "..."}（通用 webhook 格式）过去，退出 1。
# 环境变量 TROMOX_METRICS_TOKEN（= BOTMAKER_WEBHOOK_TOKEN）非空时再查 /metrics（health_url 去掉 /health 换成 /metrics）：
# 原始回调堆着没处理（raw_events_unprocessed > 0）、最近 24 小时有通知全失败（notifications.failed_24h > 0）
# 或有镜像行用满重试预算卡住（mirror_outbox_exhausted > 0，要人看 last_error 再 app.replay --reset-mirrors）
# → stderr 报 degraded，同样告警、退出 1；/metrics 本身非 200（Token 配错、服务没起全）也算 degraded。
# mirror_outbox_pending / mirror_outbox_failed_24h 不报警：积压由每 5 分钟的 app.replay 消化，不是人工项。
# 变量未设时行为与只查 /health 完全一样。全部正常时安静退出 0。
# 用法：TROMOX_METRICS_TOKEN=… healthcheck-alert.sh <health_url> [alert_webhook_url]
# 放进 cron 每 5 分钟跑一次（cron.example）。为什么要几分钟内发现：deployment.md 第 5 节。
set -euo pipefail

url=${1:?用法：healthcheck-alert.sh <health_url> [alert_webhook_url]}
alert=${2:-}
metrics_token=${TROMOX_METRICS_TOKEN:-}

alarm() {  # $1 = 一句话；stderr 报出、能发就 POST 到告警地址、退出 1
  local msg=$1 payload
  echo "$msg" >&2
  if [ -n "$alert" ]; then
    payload=$(printf '{"text": "%s (%s)"}' "$msg" "$(date '+%Y-%m-%d %H:%M:%S %Z')")
    if ! curl -fsS --max-time 10 -X POST -H 'content-type: application/json' --data "$payload" "$alert" >/dev/null 2>&1; then
      echo "healthcheck-alert.sh: 告警也没发出去：$alert" >&2
    fi
  fi
  exit 1
}

# 1. 进程活着吗（瞬时抖动：超时、5xx 重试两次再判定）
healthy=0
if body=$(curl -fsS --max-time 10 --retry 2 --retry-delay 3 "$url" 2>/dev/null); then
  if printf '%s' "$body" | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"'; then
    healthy=1
  fi
fi
[ "$healthy" -eq 1 ] || alarm "tromox webhook down: $url"

# 2. 没配 Token 就到此为止（老行为）
[ -n "$metrics_token" ] || exit 0

# 3. 活着但干活了吗：/metrics（同一把 Token）
metrics_url="${url%/health}/metrics"
if ! metrics=$(curl -sS --max-time 10 --retry 2 --retry-delay 3 -H "auth-bm-token: $metrics_token" "$metrics_url" \
                 -w '\n%{http_code}' 2>/dev/null); then
  alarm "tromox webhook degraded: GET $metrics_url unreachable"
fi
code=${metrics##*$'\n'}
metrics=${metrics%$'\n'*}
[ "$code" = "200" ] || alarm "tromox webhook degraded: GET $metrics_url returned HTTP $code"

# 读三个数：坏 JSON 也算 degraded（脚本只依赖 python3，服务器上一定有）
if ! verdict=$(printf '%s' "$metrics" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    u = int(d.get("raw_events_unprocessed", 0) or 0)
    f = int((d.get("notifications") or {}).get("failed_24h", 0) or 0)
    x = int(d.get("mirror_outbox_exhausted", 0) or 0)  # 键不存在（老版本服务）当 0
except Exception as exc:  # noqa: BLE001
    print(f"bad json: {exc}"); sys.exit(2)
print(f"unprocessed={u} failed_24h={f} mirror_exhausted={x}")
sys.exit(1 if (u > 0 or f > 0 or x > 0) else 0)
' 2>&1); then
  alarm "tromox webhook degraded: $verdict"
fi
exit 0
