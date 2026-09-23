#!/usr/bin/env bash
# 用备份文件恢复线索库：覆盖 <data_dir>/leads.db；现有库连同它的 -wal / -shm 一起留底。
# 用法：sudo ./restore.sh <backup_file> <data_dir>
#   backup_file  backup.sh 产出的 leads-YYYY-MM-DD.db
#   data_dir     容器挂载的数据目录，如 /opt/tromox/data
# 要以 root（sudo）运行：数据目录属容器用户 uid 10001，备份目录与备份文件属 root、0700 / 0600，
# 别的用户既读不了备份，也写不进数据目录。恢复出的 leads.db 会 chown 回 10001。
# 需要宿主机装有 sqlite3（apt-get install sqlite3）：没有就无法确认备份可用，直接退出、不恢复。
# 拒绝的备份文件（退出非 0、不留底、不碰 leads.db）：integrity_check 不是 ok、0 字节、没有 leads 表。
# 不负责停 / 起容器：恢复前先 docker compose stop webhook，恢复后按 stdout 的提示操作。
set -euo pipefail
umask 077

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
if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "restore.sh: 宿主机没有 sqlite3 命令（apt-get install sqlite3），无法确认备份可用，停止恢复" >&2
  exit 1
fi
# 只检查备份文件本身；现有 leads.db 可能已损坏，不去碰它
if [ "$(sqlite3 "$backup_file" 'PRAGMA integrity_check;' 2>/dev/null | head -n 1)" != "ok" ]; then
  echo "restore.sh: $backup_file 不是完好的 SQLite 库，停止恢复" >&2
  exit 1
fi
# integrity_check 对 0 字节文件、没有 leads 表的库都回 ok（备份失败那天留下的 0 字节文件恰好是最新的），再拒这两种
if [ ! -s "$backup_file" ]; then
  echo "restore.sh: $backup_file 是 0 字节文件（多半是失败的备份），停止恢复" >&2
  exit 1
fi
tables=$(sqlite3 "$backup_file" "select count(*) from sqlite_master where type='table' and name='leads';" 2>/dev/null) || true
if [ "$tables" != "1" ]; then
  echo "restore.sh: $backup_file 里没有 leads 表，不是线索库的备份，停止恢复" >&2
  exit 1
fi
backup_rows=$(sqlite3 "$backup_file" 'select count(*) from leads;' 2>/dev/null) || backup_rows="?"

target="$data_dir/leads.db"
keep=""
if [ -f "$target" ]; then
  keep="$data_dir/leads.db.pre-restore-$(date +%Y%m%d-%H%M%S)"
  cp -p "$target" "$keep"
  # -wal 里可能还有已提交、没 checkpoint 回主文件的事务（docker kill、库打不开之后的恢复正是这种情形）：
  # 移到留底文件旁边（SQLite 打开留底文件时会读到 <keep>-wal / <keep>-shm），不删
  for ext in wal shm; do
    if [ -e "$target-$ext" ]; then
      mv -f "$target-$ext" "$keep-$ext"
    fi
  done
  echo "现有库已留底：${keep}（连同 -wal / -shm；确认恢复无误后可一并删除）"
  # 只读打开，不 checkpoint、不改留底；读不了（库已损坏）就不打条数
  if before_rows=$(sqlite3 -readonly "$keep" 'select count(*) from leads;' 2>/dev/null) && [ -n "$before_rows" ]; then
    echo "恢复前线索条数：${before_rows}"
  else
    echo "恢复前线索条数：读不了现有库（可能已损坏），留底照样保留"
  fi
else
  rm -f "$target-wal" "$target-shm"
fi

cp "$backup_file" "$target"
# 容器以 uid 10001 运行；恢复文件由当前用户写入，把属主交还（非 root 时 chown 会失败，忽略）
chown 10001 "$target" 2>/dev/null || true

# 变量名后紧跟全角标点时一律写 ${var}：UTF-8 locale 下 bash 会把全角字符的首字节当成变量名的一部分
if [ -n "$keep" ]; then
  sidecars="原有 -wal / -shm 已随留底移走"
else
  sidecars="-wal / -shm 已删除"
fi
cat <<EOF
已恢复：${backup_file} -> ${target}（${sidecars}），备份里的线索条数：${backup_rows}
下一步（在 05-integration/deploy 目录执行）：
  1. docker compose restart webhook          # 已停的话用 docker compose up -d webhook
  2. docker compose exec -T webhook python -m app.replay --export   # 重建 CSV
  3. curl -fsS http://127.0.0.1:8000/health  # 端口按 TROMOX_HTTP_PORT
EOF
