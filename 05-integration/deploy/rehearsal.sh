#!/usr/bin/env bash
# 上线演练：把 ../deployment.md 第 9 节「上线前检查」里能自动做的项，对一个正在跑的部署跑一遍，
# 最后在标准输出打一张 Markdown 结果表（行号与第 9 节的 1-9 对齐）。有 FAIL 退出 1，否则 0。
# 过程日志走标准错误，标准输出只有表，方便直接贴进验收记录。
# 只依赖 curl 与 python3（解析 JSON），不依赖仓库的 .venv；第 5、8 项要动容器时才需要 docker。
# 不打印 Token，说明里的号码会被遮掉。
# 可以反复跑：第 3 项之前把样例复制到临时文件，每条 messages[]._id_ 改成 <原值>-rh<本次运行标识>
# （没有 _id_ 的事件类样例在顶层加 "_rehearsal_run"），第 3、4、5 项都发这份，退出时删掉。
# 不改写的话同一份样例第二次跑必判 duplicate：app.forget 按设计不清 processed_events。
# compose 部署是用 -p / COMPOSE_PROJECT_NAME 起的，演练前要 export 同一个 COMPOSE_PROJECT_NAME，
# 否则 docker compose 找不到那组容器；第 5 项会先 ps -q 拿容器、restart 前后核对 StartedAt，对不上记 FAIL。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_FIXTURE="${SCRIPT_DIR}/../webhook-service/fixtures/message_with_variables_b2b.json"
CURL_TIMEOUT=30
RESTART_WAIT=60

usage() {
  cat >&2 <<'EOF'
用法: rehearsal.sh <base_url> <token> [--compose-dir DIR] [--fixture PATH] [--no-cleanup]

  <base_url>        部署地址，不带路径，如 https://wa-hook.example.com 或 http://127.0.0.1:8000
  <token>           BOTMAKER_WEBHOOK_TOKEN 的值（只进请求头，不会被打印）
  --compose-dir DIR 部署所在目录（含 docker-compose.yml）；给了才做第 5 项重启与第 8 项删除
  --fixture PATH    第 3、4、5 项用的样例回调；默认 ../webhook-service/fixtures/message_with_variables_b2b.json
                    （每次运行都复制一份、把 messages[]._id_ 改写成本次独有的值再发，原文件不动）
  --no-cleanup      第 8 项只打印该跑的删除命令，不真删

演练可以反复跑：样例 id 每次自动改写，不会因为上一次演练或 4.6 的验证判成 duplicate。
部署是用 docker compose -p <名字> 或 COMPOSE_PROJECT_NAME 起的：先 export COMPOSE_PROJECT_NAME=<同一个名字> 再跑，
项目名对不上时第 5 项记 FAIL（找不到在跑的 webhook 容器），不会去 restart。
第 6（备份恢复）、7（权限）、9（Botmaker 侧）是人工项，脚本一律记 SKIP。
EOF
}

# ---------- 小工具 ----------

step() { printf '[%s/9] %s\n' "$1" "$2" >&2; }

# 遮掉 7 位以上连续数字（号码），去掉竖线与换行，截断——任何来自响应体的文本都要过这一道。
mask() {
  printf '%s' "$1" | python3 -c '
import re, sys
text = " ".join(sys.stdin.read().replace("|", " ").split())
print(re.sub(r"[0-9]{7,}", "<号码已隐藏>", text)[:160])
'
}

# json_field <json 文本> <字段名>：取顶层字段；列表用逗号连接；布尔转 true/false；取不到给空串。
json_field() {
  printf '%s' "$1" | python3 -c '
import json, sys
try:
    obj = json.loads(sys.stdin.read())
except Exception:
    print(""); raise SystemExit(0)
if not isinstance(obj, dict):
    print(""); raise SystemExit(0)
cur = obj.get(sys.argv[1])
if isinstance(cur, bool):
    print("true" if cur else "false")
elif isinstance(cur, list):
    print(", ".join(str(x) for x in cur))
elif cur is None:
    print("")
else:
    print(cur)
' "$2"
}

# do_curl <curl 参数...>：结果放进 http_code / http_body。
http_code=""
http_body=""
do_curl() {
  local raw rc
  set +e
  raw="$(curl -sS -m "${CURL_TIMEOUT}" -w $'\n%{http_code}' "$@" 2>&1)"
  rc=$?
  set -e
  if [ "${rc}" -ne 0 ]; then
    http_code="000"
    http_body="curl 失败(rc=${rc}): ${raw}"
    return 0
  fi
  http_code="${raw##*$'\n'}"
  http_body="${raw%$'\n'*}"
}

NAME=("" "/health" "无密钥请求" "样例回调" "重复回调" "重启容器" "备份与恢复演练" "权限" "测试数据" "Botmaker 侧 webhook")
RESULT=("" "" "" "" "" "" "" "" "" "")
NOTE=("" "" "" "" "" "" "" "" "" "")

set_row() { RESULT[$1]="$2"; NOTE[$1]="$(printf '%s' "$3" | tr '\n' ' ' | tr -d '|')"; }

# 本次运行的样例副本（第 3 项之前生成）；退出时删掉
RUN_FIXTURE=""
cleanup() { [ -z "${RUN_FIXTURE}" ] || rm -f "${RUN_FIXTURE}"; }
trap cleanup EXIT
RUN_TAG="$(date +%Y%m%d%H%M%S)-$$"

# make_run_fixture <原样例> <输出路径> <标识>：每条 messages[]._id_ 改成 <原值>-rh<标识>；
# 一条 _id_ 都没有（事件类样例）就在顶层加 "_rehearsal_run": <标识>，让内容哈希变掉。打印改写了几条 id。
make_run_fixture() {
  python3 -c '
import json, sys
src, dst, tag = sys.argv[1:4]
with open(src, encoding="utf-8") as fh:
    data = json.load(fh)
n = 0
if isinstance(data, dict):
    messages = data.get("messages")
    for m in messages if isinstance(messages, list) else []:
        if isinstance(m, dict) and m.get("_id_"):
            m["_id_"] = str(m["_id_"]) + "-rh" + tag
            n += 1
    if n == 0:
        data["_rehearsal_run"] = tag
with open(dst, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False)
print(n)
' "$1" "$2" "$3"
}

# ---------- 参数 ----------

BASE_URL=""
TOKEN=""
COMPOSE_DIR=""
FIXTURE=""
NO_CLEANUP=0
POSITIONAL=()

while [ $# -gt 0 ]; do
  case "$1" in
    --compose-dir)
      [ $# -ge 2 ] || { printf '%s\n' "--compose-dir 缺少参数" >&2; usage; exit 2; }
      COMPOSE_DIR="$2"; shift 2 ;;
    --fixture)
      [ $# -ge 2 ] || { printf '%s\n' "--fixture 缺少参数" >&2; usage; exit 2; }
      FIXTURE="$2"; shift 2 ;;
    --no-cleanup) NO_CLEANUP=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) printf '%s\n' "未知选项: $1" >&2; usage; exit 2 ;;
    *) POSITIONAL+=("$1"); shift ;;
  esac
done

if [ "${#POSITIONAL[@]}" -ne 2 ]; then
  printf '%s\n' "需要两个位置参数：<base_url> <token>" >&2
  usage
  exit 2
fi
BASE_URL="${POSITIONAL[0]}"
TOKEN="${POSITIONAL[1]}"
BASE_URL="${BASE_URL%/}"
[ -n "${FIXTURE}" ] || FIXTURE="${DEFAULT_FIXTURE}"

command -v curl >/dev/null 2>&1 || { printf '%s\n' "找不到 curl" >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { printf '%s\n' "找不到 python3" >&2; exit 2; }

printf '演练目标: %s\n' "${BASE_URL}" >&2
printf '样例回调: %s\n' "${FIXTURE}" >&2
printf '本次运行标识: %s\n' "${RUN_TAG}" >&2
[ -z "${COMPOSE_DIR}" ] || printf 'compose 项目名: %s\n' "${COMPOSE_PROJECT_NAME:-（未设 COMPOSE_PROJECT_NAME，按 compose 目录名）}" >&2

# ---------- 1 /health ----------

step 1 "GET ${BASE_URL}/health"
do_curl "${BASE_URL}/health"
h_code="${http_code}"
h_body="${http_body}"
h_token="$(json_field "${h_body}" webhook_token_configured)"
h_db="$(json_field "${h_body}" database)"
h_notifiers="$(json_field "${h_body}" notifiers)"
[ -n "${h_notifiers}" ] || h_notifiers="(空，没配通知渠道)"
if [ "${h_code}" = "200" ] && [ "${h_token}" = "true" ] && [ "${h_db}" = "ok" ]; then
  set_row 1 PASS "200；webhook_token_configured 为 true，database 为 ok；notifiers: ${h_notifiers}"
else
  set_row 1 FAIL "HTTP ${h_code}；webhook_token_configured=${h_token}，database=${h_db}；响应: $(mask "${h_body}")"
fi

# ---------- 2 无密钥 401 ----------

step 2 "POST ${BASE_URL}/webhooks/botmaker（不带密钥）"
do_curl -X POST -H 'content-type: application/json' --data '{}' "${BASE_URL}/webhooks/botmaker"
if [ "${http_code}" = "401" ]; then
  set_row 2 PASS "不带 auth-bm-token 的空 body 请求返回 401"
else
  set_row 2 FAIL "期望 401，实际 HTTP ${http_code}；响应: $(mask "${http_body}")"
fi

# ---------- 3 样例回调 / 4 重复回调 ----------

LEAD_ID=""
rewritten=""
fixture_err=""
if [ -f "${FIXTURE}" ]; then
  if ! RUN_FIXTURE="$(mktemp "${TMPDIR:-/tmp}/tromox-rehearsal.XXXXXX")"; then
    RUN_FIXTURE=""
    fixture_err="mktemp 建不了临时文件"
  elif ! rewritten="$(make_run_fixture "${FIXTURE}" "${RUN_FIXTURE}" "${RUN_TAG}" 2>&1)"; then
    fixture_err="$(mask "${rewritten}")"
    rewritten=""
  fi
fi

if [ ! -f "${FIXTURE}" ]; then
  set_row 3 FAIL "样例回调文件不存在: ${FIXTURE}"
  set_row 4 SKIP "第 3 项没跑成，重复回调无从验证"
elif [ -z "${rewritten}" ]; then
  set_row 3 FAIL "样例回调改写失败（不是合法 JSON？）: ${fixture_err}"
  set_row 4 SKIP "第 3 项没跑成，重复回调无从验证"
else
  if [ "${rewritten}" = "0" ]; then
    printf '样例里没有 messages[]._id_：顶层加了 "_rehearsal_run": "%s"\n' "${RUN_TAG}" >&2
  else
    printf '样例里 %s 条 messages[]._id_ 改写为 <原值>-rh%s（原文件不动）\n' "${rewritten}" "${RUN_TAG}" >&2
  fi
  step 3 "POST 样例回调（带密钥）"
  do_curl -X POST -H "auth-bm-token: ${TOKEN}" -H 'content-type: application/json' \
    --data-binary @"${RUN_FIXTURE}" "${BASE_URL}/webhooks/botmaker"
  c3_code="${http_code}"
  c3_status="$(json_field "${http_body}" status)"
  LEAD_ID="$(json_field "${http_body}" lead_id)"
  if [ "${c3_code}" = "200" ] && [ "${c3_status}" = "lead_upserted" ]; then
    set_row 3 PASS "200，status 为 lead_upserted，lead_id=${LEAD_ID}；卡片是否 60 秒内到群里请人工看"
  elif [ "${c3_code}" = "200" ] && [ "${c3_status}" = "duplicate" ]; then
    set_row 3 FAIL "200 但 status 为 duplicate：样例的 messages[]._id_ 已在 processed_events 里，app.forget 按设计不清它（删线索不会让同一条回调重新入库）。演练脚本本来每次都会把 id 改写成 <原值>-rh<本次运行标识>，出现这条说明 --fixture 给的文件里的 id 被别的方式重复用了（比如拿了某次演练改写后的副本当样例），换一份 id 没进过库的样例再跑"
  else
    set_row 3 FAIL "期望 200 且 status 为 lead_upserted，实际 HTTP ${c3_code} status=${c3_status}；响应: $(mask "${http_body}")"
  fi

  step 4 "POST 同一条样例回调（查重复）"
  do_curl -X POST -H "auth-bm-token: ${TOKEN}" -H 'content-type: application/json' \
    --data-binary @"${RUN_FIXTURE}" "${BASE_URL}/webhooks/botmaker"
  c4_status="$(json_field "${http_body}" status)"
  if [ "${http_code}" = "200" ] && [ "${c4_status}" = "duplicate" ]; then
    set_row 4 PASS "200，status 为 duplicate；群里不应出现第二张卡片"
  else
    set_row 4 FAIL "期望 200 且 status 为 duplicate，实际 HTTP ${http_code} status=${c4_status}；响应: $(mask "${http_body}")"
  fi
fi

# ---------- 5 重启容器 ----------

COMPOSE_FILE=""
if [ -n "${COMPOSE_DIR}" ]; then
  COMPOSE_FILE="${COMPOSE_DIR}/docker-compose.yml"
fi

if [ -z "${COMPOSE_DIR}" ]; then
  set_row 5 SKIP "没给 --compose-dir：本机 / 无 compose 的部署不自动重启，请人工重启后确认 /health 与数据还在"
elif [ ! -f "${COMPOSE_FILE}" ]; then
  set_row 5 FAIL "找不到 ${COMPOSE_FILE}"
elif ! command -v docker >/dev/null 2>&1; then
  set_row 5 FAIL "给了 --compose-dir 但本机没有 docker"
else
  step 5 "docker compose ps -q webhook 找容器 → restart webhook → 核对 StartedAt 变了 → 等 /health"
  # 项目名对不上时 restart 对一个不存在的服务照样退出 0、/health 由正在跑的那个容器回 200——所以先找容器
  cid="$(docker compose -f "${COMPOSE_FILE}" ps -q webhook | head -n 1 | tr -d '[:space:]')" || cid=""
  started_before=""
  started_after=""
  [ -z "${cid}" ] || started_before="$(docker inspect -f '{{.State.StartedAt}}' "${cid}")" || started_before=""
  if [ -z "${cid}" ]; then
    set_row 5 FAIL "compose 目录下没有在跑的 webhook 容器（docker compose ps -q webhook 为空），没做 restart：项目名对不上？用 -p / COMPOSE_PROJECT_NAME 起的部署，演练前要 export COMPOSE_PROJECT_NAME=<同一个名字>；也可能容器本来就没起来"
  elif [ -z "${started_before}" ]; then
    set_row 5 FAIL "docker inspect 取不到容器 ${cid:0:12} 的 StartedAt，没做 restart"
  elif ! docker compose -f "${COMPOSE_FILE}" restart webhook >&2; then
    set_row 5 FAIL "docker compose restart webhook 失败，看上面的输出"
  elif ! started_after="$(docker inspect -f '{{.State.StartedAt}}' "${cid}")" || [ -z "${started_after}" ]; then
    set_row 5 FAIL "restart 之后 docker inspect 取不到容器 ${cid:0:12}：容器没了？看 docker compose ps"
  elif [ "${started_after}" = "${started_before}" ]; then
    set_row 5 FAIL "restart 返回了成功但容器没有真的重启（容器 ${cid:0:12} 的 StartedAt 前后都是 ${started_before}）"
  else
    up=0
    waited=0
    while [ "${waited}" -lt "${RESTART_WAIT}" ]; do
      do_curl "${BASE_URL}/health"
      if [ "${http_code}" = "200" ]; then up=1; break; fi
      sleep 2
      waited=$((waited + 2))
    done
    if [ "${up}" -eq 1 ] && [ "${RESULT[4]}" = "PASS" ]; then
      # 「数据仍在」不能只看 /health：再发一次第 3 项那条样例（本次改写过 id 的副本），仍判重就说明库没被重建。
      do_curl -X POST -H "auth-bm-token: ${TOKEN}" -H 'content-type: application/json' \
        --data-binary @"${RUN_FIXTURE}" "${BASE_URL}/webhooks/botmaker"
      c5_status="$(json_field "${http_body}" status)"
      if [ "${http_code}" = "200" ] && [ "${c5_status}" = "duplicate" ]; then
        set_row 5 PASS "容器确实重启了（StartedAt 已变）；重启后 ${waited} 秒内 /health 返回 200；再发一次样例仍返回 duplicate，说明数据还在"
      else
        set_row 5 FAIL "重启后 /health 恢复了，但再发样例返回 HTTP ${http_code} status=${c5_status}，数据可能没落到宿主机目录"
      fi
    elif [ "${up}" -eq 1 ]; then
      set_row 5 PASS "容器确实重启了（StartedAt 已变）；重启后 ${waited} 秒内 /health 返回 200；第 4 项没通过，数据是否仍在请人工确认"
    else
      set_row 5 FAIL "重启后 ${RESTART_WAIT} 秒内 /health 没回 200（最后一次 HTTP ${http_code}）"
    fi
  fi
fi

# ---------- 6 / 7 / 9 人工项 ----------

set_row 6 SKIP "人工项：按 deploy/README.md 第 3 节用前一日备份走一遍 restore.sh。脚本本身的往返、清理、拒坏文件由 tests/test_backup_restore.py 固定；这里要人工做的是在服务器上用前一日备份真恢复一次"
set_row 7 SKIP "人工项：看 .env 是否 600、服务器是否禁了密码登录、我方子账号能否回收"
set_row 9 SKIP "人工项：到 Botmaker 后台确认 webhook 指向正式地址，且联调后错误日志没有新增记录"

# ---------- 8 测试数据删除 ----------

FORGET_ID="${LEAD_ID:-<第 3 项拿到的 lead_id>}"
LOCAL_FORGET="在 05-integration/webhook-service 下执行 .venv/bin/python -m app.forget --lead-id ${FORGET_ID} --yes"
COMPOSE_FORGET="docker compose exec -T webhook python -m app.forget --lead-id ${FORGET_ID} --yes"

if [ -n "${COMPOSE_DIR}" ] && [ "${NO_CLEANUP}" -eq 0 ] && [ -n "${LEAD_ID}" ] && [ -f "${COMPOSE_FILE}" ] && command -v docker >/dev/null 2>&1; then
  step 8 "删除本次演练写进去的测试线索"
  if docker compose -f "${COMPOSE_FILE}" exec -T webhook python -m app.forget --lead-id "${LEAD_ID}" --yes >&2; then
    set_row 8 PASS "已删除 lead_id=${LEAD_ID}（账本 / 通知 / 原始回调 / CSV 一起删，CSV 已重写）"
  else
    set_row 8 FAIL "app.forget 删除 lead_id=${LEAD_ID} 失败，看上面的输出；报 service webhook is not running 多半是项目名对不上（-p / COMPOSE_PROJECT_NAME 与部署时不同，export 同一个名字再跑）；手动补一次: ${COMPOSE_FORGET}"
  fi
elif [ -z "${LEAD_ID}" ]; then
  set_row 8 SKIP "第 3 项没拿到 lead_id，没有要删的测试线索；真跑出线索后用 app.forget --lead-id <id> --yes 删"
elif [ "${NO_CLEANUP}" -eq 1 ]; then
  set_row 8 SKIP "--no-cleanup：测试线索留着没删，验完自己删 —— ${LOCAL_FORGET}；compose 部署: ${COMPOSE_FORGET}"
else
  set_row 8 SKIP "本机 / 无 compose：脚本不自动删，请${LOCAL_FORGET}；compose 部署: ${COMPOSE_FORGET}"
fi

# ---------- 结果表 ----------

pass_n=0
fail_n=0
skip_n=0
for i in 1 2 3 4 5 6 7 8 9; do
  case "${RESULT[${i}]}" in
    PASS) pass_n=$((pass_n + 1)) ;;
    FAIL) fail_n=$((fail_n + 1)) ;;
    *) skip_n=$((skip_n + 1)) ;;
  esac
done

printf '\n'
printf '### 上线前检查演练结果（%s）\n\n' "${BASE_URL}"
printf '| # | 检查项 | 结果 | 说明 |\n'
printf '|---|---|---|---|\n'
for i in 1 2 3 4 5 6 7 8 9; do
  printf '| %d | %s | %s | %s |\n' "${i}" "${NAME[${i}]}" "${RESULT[${i}]}" "${NOTE[${i}]}"
done
printf '\n合计: PASS %d / FAIL %d / SKIP %d。行号对应 ../deployment.md 第 9 节的 1-9 项。\n' "${pass_n}" "${fail_n}" "${skip_n}"

if [ "${fail_n}" -gt 0 ]; then
  printf '有 %d 项 FAIL，不要上线。\n' "${fail_n}" >&2
  exit 1
fi
exit 0
