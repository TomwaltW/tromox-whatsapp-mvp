#!/usr/bin/env bash
# 更新回调服务：记下当前提交、把当前镜像另存为 tromox-webhook:rollback → git pull --ff-only → 重建镜像
# → 重建容器 → 等 /health 返回 200。新版本在时限内不健康时自动回滚到上一版镜像（deployment.md 第 7 节）。
# 用法：update.sh [--no-rollback] [compose_dir]
#   --no-rollback  失败时只报告、不回滚（坏容器留着排查）
#   compose_dir    docker-compose.yml 所在目录，默认本脚本所在目录
# 环境变量：TROMOX_UPDATE_WAIT_S  每一轮等 /health 的秒数，默认 60（每 2 秒查一次）
# 退出码：
#   0  更新成功
#   1  没更新成：构建失败（线上容器没动）；或新版本不健康、已自动回滚且回滚后健康；或 --no-rollback 下新版本不健康
#   2  线上此刻没有健康的版本，立刻人工处理：回滚后仍不健康，或更新前没有可回滚的镜像（首次部署）
# 回滚只回镜像，代码仍停在新提交；stderr 会给出把代码钉回旧提交的命令。切换有数秒不可用，放在咨询低谷做。
set -euo pipefail

usage() {
  sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

no_rollback=0
while [ $# -gt 0 ]; do
  case "$1" in
    --no-rollback) no_rollback=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    -*) echo "update.sh: 不认识的选项 $1" >&2; usage >&2; exit 1 ;;
    *) break ;;
  esac
done
if [ $# -gt 1 ]; then
  echo "update.sh: 参数太多：$*" >&2; usage >&2; exit 1
fi

wait_s=${TROMOX_UPDATE_WAIT_S:-60}
if ! [[ "$wait_s" =~ ^[0-9]+$ ]] || [ "$wait_s" -lt 1 ]; then
  echo "update.sh: TROMOX_UPDATE_WAIT_S 要是正整数（秒），现在是 '$wait_s'" >&2
  exit 1
fi
attempts=$(( (wait_s + 1) / 2 ))   # 每 2 秒查一次，至少查一次

compose_dir=${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}
cd "$compose_dir"
if [ ! -f docker-compose.yml ]; then
  echo "update.sh: $compose_dir 里没有 docker-compose.yml" >&2
  exit 1
fi

repo_root=$(git rev-parse --show-toplevel)
old_sha=$(git -C "$repo_root" rev-parse --short HEAD)   # 必须在 pull 之前取
new_sha=$old_sha

# 把代码钉回旧提交的命令（回滚只回镜像；下次 update.sh 的 git pull --ff-only 仍会走到上游最新）
pin_hint() {
  if [ "$new_sha" = "$old_sha" ]; then
    echo "  代码没有新提交（仍是 ${old_sha}），不用钉回。"
    return 0
  fi
  echo "  把代码也钉回上一版（会丢掉部署克隆工作区里的改动——部署克隆里本来就不该有改动）："
  echo "    git -C $repo_root reset --hard $old_sha"
  echo "  上游修好之后再跑 update.sh 即可（git pull --ff-only 会从 $old_sha 快进过去）。"
}

have_rollback=0
if docker image inspect tromox-webhook:latest >/dev/null 2>&1; then
  docker tag tromox-webhook:latest tromox-webhook:rollback
  have_rollback=1
  echo "== 当前镜像另存为 tromox-webhook:rollback（代码 ${old_sha}）"
else
  echo "== 没有 tromox-webhook:latest（首次部署？）：这次新版本起不来的话，没有镜像可回滚"
fi

echo "== git pull --ff-only（${repo_root}）"   # 全角括号紧跟变量名要写 ${var}，否则 bash 会吞掉括号的首字节
if ! git -C "$repo_root" pull --ff-only; then
  echo "update.sh: git pull --ff-only 失败（本地有改动或与上游分叉？），代码、镜像、容器都没动" >&2
  exit 1
fi
new_sha=$(git -C "$repo_root" rev-parse --short HEAD)
echo "== 现在的版本：$(git -C "$repo_root" log --oneline -1)"

echo "== docker compose build webhook"
if ! docker compose build webhook; then
  {
    echo "update.sh: 镜像构建失败，线上容器没动（仍在跑更新前的镜像）；代码已停在新提交 ${new_sha}，上一版是 ${old_sha}。"
    pin_hint
  } >&2
  exit 1
fi

# 等 /health 返回 200：最多 attempts 次、每 2 秒一次。宿主机侧的地址由 compose 告诉我们（受 TROMOX_BIND / TROMOX_HTTP_PORT 影响）
health_body=""
wait_healthy() {
  local addr="" url="" i
  for i in $(seq 1 "$attempts"); do
    if [ -z "$url" ] && addr=$(docker compose port webhook 8000 2>/dev/null) && [ -n "$addr" ]; then
      url="http://${addr}/health"
      echo "== 等待 ${url}（最多 ${wait_s} 秒）"
    fi
    if [ -n "$url" ] && health_body=$(curl -fsS --max-time 3 "$url" 2>/dev/null); then
      return 0
    fi
    if [ "$i" -lt "$attempts" ]; then sleep 2; fi
  done
  return 1
}

echo "== docker compose up -d webhook"
if docker compose up -d webhook && wait_healthy; then
  echo "== 更新完成（$old_sha → ${new_sha}）：$health_body"
  docker compose ps webhook
  exit 0
fi

echo "update.sh: 新版本 $new_sha 在 ${wait_s} 秒内没有让 /health 返回 200" >&2
docker compose ps webhook >&2 || true
# 回滚会重建容器，新版本容器的日志跟着就没了：先把最后 50 行打到 stderr 留底
echo "== 新版本容器最后 50 行日志：" >&2
docker compose logs --no-color --tail 50 webhook >&2 || true

if [ "$no_rollback" = 1 ]; then
  {
    echo "update.sh: --no-rollback：不回滚，新版本的容器留着排查。要手动回到上一版："
    if [ "$have_rollback" = 1 ]; then
      echo "    docker tag tromox-webhook:rollback tromox-webhook:latest && docker compose up -d --no-build webhook"
    fi
    pin_hint
  } >&2
  exit 1
fi

if [ "$have_rollback" = 0 ]; then
  echo "update.sh: 更新前没有 tromox-webhook:latest（首次部署），无可回滚的镜像；线上此刻没有健康的版本，立刻人工处理。" >&2
  exit 2
fi

echo "== 回滚到上一版镜像：docker tag tromox-webhook:rollback tromox-webhook:latest"
if docker tag tromox-webhook:rollback tromox-webhook:latest \
  && echo "== docker compose up -d --no-build webhook" \
  && docker compose up -d --no-build webhook \
  && wait_healthy; then
  {
    echo "update.sh: 更新失败，已回滚到上一版镜像；代码仍停在新提交 ${new_sha}，上一版是 ${old_sha}。"
    pin_hint
    echo "  新版本为什么起不来：看上面留底的那 50 行日志（新版本的容器已被替换，docker compose logs 里只剩回滚后的）。"
  } >&2
  exit 1
fi

{
  echo "update.sh: 回滚后 /health 仍然不通，线上此刻没有健康的版本，立刻人工处理：docker compose logs --tail 100 webhook"
  pin_hint
} >&2
docker compose ps webhook >&2 || true
exit 2
