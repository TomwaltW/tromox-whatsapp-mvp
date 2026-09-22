#!/usr/bin/env bash
# 用备份文件恢复线索库：覆盖 <data_dir>/leads.db，删除同目录的 -wal / -shm。
# 用法：restore.sh <backup_file> <data_dir>
#   backup_file  backup.sh 产出的 leads-YYYY-MM-DD.db
#   data_dir     容器挂载的数据目录，如 /opt/tromox/data
# 不负责停 / 起容器：恢复前先 docker compose stop webhook，恢复后按 stdout 的提示操作。
set -euo pipefail

backup_file=${1:?用法：restore.sh <backup_file> <data_dir>}
data_dir=${2:?用法：restore.sh <backup_file> <data_dir>}

if [ ! -f "$backup_file" ]; then
  echo "restore.sh: 找不到备份文件 $backup_file" >&2
  exit 1
fi
if [ ! -d "$data_dir" ]; then
  echo "restore.sh: 数据目录不存在 $data_dir" >&2
  exit 1
fi
# 只检查备份文件本身是不是完好的 SQLite 库；现有 leads.db 可能已损坏，不去碰它
if command -v sqlite3 >/dev/null 2>&1; then
  if [ "$(sqlite3 "$backup_file" 'PRAGMA integrity_check;' 2>/dev/null | head -n 1)" != "ok" ]; then
    echo "restore.sh: $backup_file 不是完好的 SQLite 库，停止恢复" >&2
    exit 1
  fi
fi

target="$data_dir/leads.db"
if [ -f "$target" ]; then
  keep="$data_dir/leads.db.pre-restore-$(date +%Y%m%d-%H%M%S)"
  cp -p "$target" "$keep"
  echo "现有库已留底：${keep}（确认恢复无误后可删除）"
fi

cp "$backup_file" "$target"
rm -f "$data_dir/leads.db-wal" "$data_dir/leads.db-shm"
# 容器以 uid 10001 运行；恢复文件由当前用户写入，尽量把属主交还（非 root 时 chown 会失败，忽略）
chown 10001 "$target" 2>/dev/null || true

# 变量名后紧跟全角标点时一律写 ${var}：UTF-8 locale 下 bash 会把全角字符的首字节当成变量名的一部分
cat <<EOF
已恢复：${backup_file} -> ${target}（-wal / -shm 已删除）
下一步（在 05-integration/deploy 目录执行）：
  1. docker compose restart webhook          # 已停的话用 docker compose up -d webhook
  2. docker compose exec -T webhook python -m app.replay --export   # 重建 CSV
  3. curl -fsS http://127.0.0.1:8000/health  # 端口按 TROMOX_HTTP_PORT
EOF
