#!/usr/bin/env bash
# 每日备份线索库：在线一致性备份（库开了 WAL，不直接拷贝正在写的文件），并清理过期备份。
# 用法：backup.sh <data_dir> <backup_dir> [keep_days=30]
#   data_dir    容器挂载的数据目录（里面有 leads.db），如 /opt/tromox/data
#   backup_dir  备份目录，不存在会创建，如 /opt/tromox/backup
#   keep_days   保留天数，更早的 leads-*.db 会被删除
# 成功时 stdout 打印备份文件路径。需要宿主机装有 sqlite3（apt-get install sqlite3）。
set -euo pipefail

data_dir=${1:?用法：backup.sh <data_dir> <backup_dir> [keep_days=30]}
backup_dir=${2:?用法：backup.sh <data_dir> <backup_dir> [keep_days=30]}
keep_days=${3:-30}

src="$data_dir/leads.db"
if [ ! -f "$src" ]; then
  echo "backup.sh: 找不到 $src" >&2
  exit 1
fi
if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "backup.sh: 宿主机没有 sqlite3 命令（apt-get install sqlite3）" >&2
  exit 1
fi

mkdir -p "$backup_dir"
out="$backup_dir/leads-$(date +%F).db"
sqlite3 "$src" ".backup '$out'"

# 备份完成后再清理，避免备份失败那天把旧备份也删了
find "$backup_dir" -maxdepth 1 -type f -name 'leads-*.db' -mtime +"$keep_days" -delete

echo "$out"
