#!/usr/bin/env bash
# 每日备份线索库：在线一致性备份（库开了 WAL，不直接拷贝正在写的文件），并清理过期备份。
# 用法：backup.sh <data_dir> <backup_dir> [keep_days=30]
#   data_dir    容器挂载的数据目录（里面有 leads.db），如 /opt/tromox/data
#   backup_dir  备份目录，不存在会创建（0700），如 /opt/tromox/backup
#   keep_days   保留天数，更早的 leads-*.db 会被删除
# 成功时 stdout 末行打印备份文件路径。需要宿主机装有 sqlite3（apt-get install sqlite3）。
#
# 要以 root 运行（cron 写在 /etc/cron.d/tromox-backup，见 cron.example；手工跑用 sudo）：
# 数据目录属容器用户 uid 10001、0755，服务空闲时 SQLite 会删掉 -wal / -shm，
# 别的用户跑 .backup 时建不了 -shm，报 "attempt to write a readonly database"。
# root 建的 -wal / -shm 会被 SQLite 交还给库文件的属主，不会把容器写坏。
#
# 先写到同目录的 <备份>.tmp，integrity_check 为 ok 且有 leads 表才改名成 leads-YYYY-MM-DD.db；
# 任何一步失败都删掉临时文件、退出非 0，备份目录里不留 0 字节或半截的 leads-*.db。
# 备份里有号码与姓名：umask 077，备份文件 0600、新建的备份目录 0700。
set -euo pipefail
umask 077

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
tmp="$out.tmp"
# 成功时临时文件已改名，rm -f 是空操作；失败时连同 sqlite3 可能留下的 -journal / -wal / -shm 一起删
trap 'rm -f "$tmp" "$tmp-journal" "$tmp-wal" "$tmp-shm"' EXIT
rm -f "$tmp" "$tmp-journal" "$tmp-wal" "$tmp-shm"

# 变量名后紧跟全角标点时一律写 ${var}：UTF-8 locale 下 bash 会把全角字符的首字节当成变量名的一部分
if ! err=$(sqlite3 "$src" ".backup '$tmp'" 2>&1); then
  if [ -n "$err" ]; then printf '%s\n' "$err" >&2; fi
  echo "backup.sh: sqlite3 .backup 失败，没有生成备份。数据目录属容器用户 uid 10001，请以 root 运行（/etc/cron.d/tromox-backup，见 cron.example）或 sudo ./backup.sh …" >&2
  exit 1
fi

check=$(sqlite3 "$tmp" 'PRAGMA integrity_check;' 2>&1 | head -n 1) || true
tables=$(sqlite3 "$tmp" "select count(*) from sqlite_master where type='table' and name='leads';" 2>&1) || true
if [ ! -s "$tmp" ] || [ "$check" != "ok" ] || [ "$tables" != "1" ]; then
  echo "backup.sh: 备份结果校验不通过（integrity_check=${check:-空}，leads 表=${tables:-空}），已删除临时文件，没有生成备份" >&2
  exit 1
fi

mv -f "$tmp" "$out"

# 备份完成后再清理，避免备份失败那天把旧备份也删了
find "$backup_dir" -maxdepth 1 -type f -name 'leads-*.db' -mtime +"$keep_days" -delete

echo "$out"
