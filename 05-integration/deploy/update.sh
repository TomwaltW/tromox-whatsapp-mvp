#!/usr/bin/env bash
# 更新回调服务：git pull --ff-only → 重建镜像 → 重建容器 → 等 /health 返回 200（最多 60 秒）。
# 用法：update.sh [compose_dir]
#   compose_dir  docker-compose.yml 所在目录，默认本脚本所在目录
# 切换有数秒不可用，放在咨询低谷做（deployment.md 第 7 节）。任一步失败退出非 0。
set -euo pipefail

compose_dir=${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}
cd "$compose_dir"
if [ ! -f docker-compose.yml ]; then
  echo "update.sh: $compose_dir 里没有 docker-compose.yml" >&2
  exit 1
fi

repo_root=$(git rev-parse --show-toplevel)
echo "== git pull --ff-only（${repo_root}）"   # 全角括号紧跟变量名要写 ${var}，否则 bash 会吞掉括号的首字节
git -C "$repo_root" pull --ff-only
echo "== 现在的版本：$(git -C "$repo_root" log --oneline -1)"

echo "== docker compose build webhook"
docker compose build webhook

echo "== docker compose up -d webhook"
docker compose up -d webhook

# 宿主机侧的地址由 compose 告诉我们（受 TROMOX_BIND / TROMOX_HTTP_PORT 影响）
addr=$(docker compose port webhook 8000)
url="http://${addr}/health"
echo "== 等待 $url"
for _ in $(seq 1 30); do
  if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
    echo "== 更新完成：$(curl -fsS --max-time 3 "$url")"
    docker compose ps webhook
    exit 0
  fi
  sleep 2
done

echo "update.sh: 60 秒内 $url 没有返回 200，请看 docker compose logs --tail 100 webhook" >&2
docker compose ps webhook >&2 || true
exit 1
