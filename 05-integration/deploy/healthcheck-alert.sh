#!/usr/bin/env bash
# 健康检查 + 告警：/health 返回 200 且 status 为 ok → 退出 0、不出声；否则 stderr 报 down，
# 给了告警地址就 POST 一条 {"text": "..."}（通用 webhook 格式）过去，退出 1。
# 用法：healthcheck-alert.sh <health_url> [alert_webhook_url]
# 放进 cron 每 5 分钟跑一次（cron.example）。为什么要几分钟内发现：deployment.md 第 5 节。
set -euo pipefail

url=${1:?用法：healthcheck-alert.sh <health_url> [alert_webhook_url]}
alert=${2:-}

# 瞬时抖动（超时、5xx）重试两次再判定
if body=$(curl -fsS --max-time 10 --retry 2 --retry-delay 3 "$url" 2>/dev/null); then
  if printf '%s' "$body" | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"'; then
    exit 0
  fi
fi

msg="tromox webhook down: $url"
echo "$msg" >&2
if [ -n "$alert" ]; then
  payload=$(printf '{"text": "%s (%s)"}' "$msg" "$(date '+%Y-%m-%d %H:%M:%S %Z')")
  if ! curl -fsS --max-time 10 -X POST -H 'content-type: application/json' --data "$payload" "$alert" >/dev/null 2>&1; then
    echo "healthcheck-alert.sh: 告警也没发出去：$alert" >&2
  fi
fi
exit 1
