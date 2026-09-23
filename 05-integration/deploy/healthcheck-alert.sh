#!/usr/bin/env bash
# 健康检查 + 告警：/health 返回 200 且 status 为 ok → 进程活着；否则 stderr 报 down，
# 给了告警地址就 POST 一条告警过去，退出 1。
# 环境变量 TROMOX_METRICS_TOKEN（= BOTMAKER_WEBHOOK_TOKEN）非空时再查 /metrics（health_url 去掉 /health 换成 /metrics）：
# 原始回调堆着没处理（raw_events_unprocessed > 0）、最近 24 小时有通知全失败（notifications.failed_24h > 0）
# 或有镜像行用满重试预算卡住（mirror_outbox_exhausted > 0，要人看 last_error 再 app.replay --reset-mirrors）
# → stderr 报 degraded，同样告警、退出 1；/metrics 本身非 200（Token 配错、服务没起全）也算 degraded。
# mirror_outbox_pending / mirror_outbox_failed_24h 不报警：积压由每 5 分钟的 app.replay 消化，不是人工项。
# /metrics 的响应先落临时文件再解析（curl 重试时会截断重写文件；写 stdout 时 502 的正文会和随后 200 的 JSON 拼在一起）。
# 变量未设时行为与只查 /health 完全一样。全部正常时安静退出 0。
#
# 告警地址（第二个参数）三种都可以直接填，按主机名自动选请求体格式：
#   open.feishu.cn / open.larksuite.com → 飞书群机器人 {"msg_type":"text","content":{"text":…}}
#   qyapi.weixin.qq.com                 → 企业微信群机器人 {"msgtype":"text","text":{"content":…}}
#   其他                                → 通用 webhook {"text":…}
# 环境变量 TROMOX_ALERT_FORMAT=feishu|wecom|generic 强制指定格式（经转换端点转发、或测试时用），不设就按主机名判断。
# 环境变量 TROMOX_ALERT_SIGNING_SECRET：飞书机器人开了「签名校验」时填它的密钥，请求体顶层加 timestamp 与 sign
# （算法同 webhook-service/app/notify/feishu.py）；其他格式忽略。
# 请求体由 python3 的 json.dumps 生成（消息里有引号、反斜杠也是合法 JSON）。发出后看返回：HTTP 非 2xx、
# 飞书返回体 code（或 StatusCode）非 0、企业微信 errcode 非 0 → stderr 报「告警也没发出去」（只打主机名，
# 不打地址里的 key / token）；通用格式只看 HTTP 状态。有告警就退出 1，发没发出去都一样。
# 用法：TROMOX_METRICS_TOKEN=… healthcheck-alert.sh <health_url> [alert_webhook_url]
# 放进 cron 每 5 分钟跑一次（cron.example）。为什么要几分钟内发现：deployment.md 第 5 节。
set -euo pipefail

url=${1:?用法：healthcheck-alert.sh <health_url> [alert_webhook_url]}
alert=${2:-}
metrics_token=${TROMOX_METRICS_TOKEN:-}
metrics_tmp=""
trap '[ -z "$metrics_tmp" ] || rm -f "$metrics_tmp"' EXIT

# alert_meta：打印「<格式> <主机名>」。主机名只用来选格式和写进报错，地址里的 key / token 不出这个函数。
alert_meta() {
  ALERT_URL="$alert" python3 -c '
import os, sys
from urllib.parse import urlsplit
try:
    host = (urlsplit(os.environ["ALERT_URL"]).hostname or "").lower()
except ValueError:
    host = ""
forced = os.environ.get("TROMOX_ALERT_FORMAT", "").strip().lower()
if forced in ("feishu", "wecom", "generic"):
    fmt = forced
else:
    if forced:
        print(f"healthcheck-alert.sh: TROMOX_ALERT_FORMAT={forced} 不认识（只认 feishu / wecom / generic），按主机名判断", file=sys.stderr)
    fmt = ("feishu" if host in ("open.feishu.cn", "open.larksuite.com")
           else "wecom" if host == "qyapi.weixin.qq.com" else "generic")
print(fmt, host or "?")
'
}

# alert_body <格式>：告警正文从环境变量 ALERT_TEXT 读，请求体 JSON 打到 stdout。
alert_body() {
  python3 -c '
import base64, hashlib, hmac, json, os, sys, time
fmt, text = sys.argv[1], os.environ["ALERT_TEXT"]
if fmt == "feishu":
    body = {"msg_type": "text", "content": {"text": text}}
    secret = os.environ.get("TROMOX_ALERT_SIGNING_SECRET", "")
    if secret:
        timestamp = str(int(time.time()))
        key = f"{timestamp}\n{secret}".encode("utf-8")
        body["timestamp"] = timestamp
        body["sign"] = base64.b64encode(hmac.new(key, digestmod=hashlib.sha256).digest()).decode("utf-8")
elif fmt == "wecom":
    body = {"msgtype": "text", "text": {"content": text}}
else:
    body = {"text": text}
sys.stdout.write(json.dumps(body))
' "$1"
}

# alert_check <格式> <HTTP 码>：返回体从 stdin 读。送达退出 0；否则打印原因（HTTP 码与 code / errcode）、退出 1。
# 口径同 webhook-service/app/notify：HTTP 非 2xx 算失败；返回体不是 JSON 对象当作没有 code。
alert_check() {
  python3 -c '
import json, sys
fmt, http = sys.argv[1], sys.argv[2]
raw = sys.stdin.read()
if not (len(http) == 3 and http.startswith("2")):
    print(f"HTTP {http}" + ("（连不上或超时）" if http == "000" else "")); sys.exit(1)
if fmt == "generic":
    sys.exit(0)
try:
    data = json.loads(raw)
except ValueError:
    data = {}
if not isinstance(data, dict):
    data = {}
if fmt == "feishu":
    name, value, why = "code", data.get("code", data.get("StatusCode", 0)), data.get("msg", data.get("StatusMessage", ""))
else:
    name, value, why = "errcode", data.get("errcode", 0), data.get("errmsg", "")
if value in (0, "0", None):
    sys.exit(0)
why = " ".join(str(why or "").split())[:80]
print(f"HTTP {http}，{name}={value}" + (f"（{why}）" if why else "")); sys.exit(1)
' "$1" "$2"
}

alarm() {  # $1 = 一句话；stderr 报出、能发就 POST 到告警地址、退出 1
  local msg=$1 meta fmt host resp code reason
  echo "$msg" >&2
  if [ -n "$alert" ]; then
    meta=$(alert_meta) || meta="generic ?"
    fmt=${meta%% *}
    host=${meta#* }
    # 请求体走管道（@-），不落盘；返回体与 HTTP 码一起从 stdout 取回（告警只发一次，不重试，不会拼接）
    resp=$(ALERT_TEXT="$msg ($(date '+%Y-%m-%d %H:%M:%S %Z'))" alert_body "$fmt" \
             | curl -sS --max-time 10 -X POST -H 'content-type: application/json' --data-binary @- \
                    -w '\n%{http_code}' "$alert" 2>/dev/null) || true
    code=${resp##*$'\n'}
    case "$code" in [0-9][0-9][0-9]) resp=${resp%$'\n'*} ;; *) code=000; resp="" ;; esac
    if ! reason=$(printf '%s' "$resp" | alert_check "$fmt" "$code" 2>&1); then
      echo "healthcheck-alert.sh: 告警也没发出去：${host}（${fmt} 格式）返回 ${reason}" >&2
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

# 3. 活着但干活了吗：/metrics（同一把 Token）。不加 -f：401 / 502 要落到下面「returned HTTP」那条，而不是 unreachable
metrics_url="${url%/health}/metrics"
metrics_tmp=$(mktemp "${TMPDIR:-/tmp}/tromox-metrics.XXXXXX") \
  || alarm "tromox webhook degraded: mktemp failed, GET $metrics_url not checked"
if ! code=$(curl -sS --max-time 10 --retry 2 --retry-delay 3 -H "auth-bm-token: $metrics_token" \
                 -o "$metrics_tmp" -w '%{http_code}' "$metrics_url" 2>/dev/null); then
  alarm "tromox webhook degraded: GET $metrics_url unreachable"
fi
[ "$code" = "200" ] || alarm "tromox webhook degraded: GET $metrics_url returned HTTP $code"

# 读三个数：坏 JSON 也算 degraded（脚本只依赖 python3，服务器上一定有）
if ! verdict=$(python3 -c '
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        d = json.load(fh)
    u = int(d.get("raw_events_unprocessed", 0) or 0)
    f = int((d.get("notifications") or {}).get("failed_24h", 0) or 0)
    x = int(d.get("mirror_outbox_exhausted", 0) or 0)  # 键不存在（老版本服务）当 0
except Exception as exc:  # noqa: BLE001
    print(f"bad json: {exc}"); sys.exit(2)
print(f"unprocessed={u} failed_24h={f} mirror_exhausted={x}")
sys.exit(1 if (u > 0 or f > 0 or x > 0) else 0)
' "$metrics_tmp" 2>&1); then
  alarm "tromox webhook degraded: $verdict"
fi
exit 0
