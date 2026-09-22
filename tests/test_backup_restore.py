"""05-integration/deploy/backup.sh、restore.sh：往返一致、过期清理、-wal / -shm 清除、拒绝坏文件。"""
from __future__ import annotations

import os
import re
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "05-integration" / "deploy"
DAY = 86400

# 两个脚本都调宿主机的 sqlite3（备份用 .backup，恢复前查 integrity_check）
pytestmark = pytest.mark.skipif(shutil.which("sqlite3") is None, reason="宿主机没有 sqlite3 命令")


def run_script(name: str, *args: str) -> subprocess.CompletedProcess:
    """跑 deploy 目录下的脚本；stderr 里的中文提示要按 UTF-8 解，不跟调用方的 locale 走。"""
    return subprocess.run(
        ["bash", str(DEPLOY / name), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def make_wal_db(path: Path, companies: tuple[str, ...] = ("A", "B", "C")) -> sqlite3.Connection:
    """造一个 WAL 模式的 leads.db，返回还开着的写连接（调用方负责关）。"""
    conn = sqlite3.connect(path)
    conn.execute("pragma journal_mode=wal")
    conn.execute("create table leads(id integer primary key, company text)")
    conn.executemany("insert into leads(company) values (?)", [(c,) for c in companies])
    conn.commit()
    return conn


def count_rows(db: Path) -> int:
    conn = sqlite3.connect(db)
    try:
        return conn.execute("select count(*) from leads").fetchone()[0]
    finally:
        conn.close()


def backup_path(result: subprocess.CompletedProcess) -> Path:
    """backup.sh 成功时 stdout 末行是备份文件路径。"""
    return Path(result.stdout.strip().splitlines()[-1])


def age(path: Path, days: float) -> None:
    stamp = time.time() - days * DAY
    os.utime(path, (stamp, stamp))


def test_backup_includes_writes_still_sitting_in_the_wal(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    backup = tmp_path / "backup"  # 不预先建，backup.sh 自己 mkdir -p
    conn = make_wal_db(data / "leads.db")
    # 写连接还开着：这三行提交了但没 checkpoint 回主库，直接拷 leads.db 会丢
    assert (data / "leads.db-wal").stat().st_size > 0
    try:
        result = run_script("backup.sh", str(data), str(backup), "30")
    finally:
        conn.close()

    assert result.returncode == 0, result.stderr
    out = backup_path(result)
    assert out.parent == backup
    assert re.fullmatch(r"leads-\d{4}-\d{2}-\d{2}\.db", out.name), out.name
    assert count_rows(out) == 3


def test_backup_deletes_only_expired_files_named_leads(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    backup = tmp_path / "backup"
    backup.mkdir()
    make_wal_db(data / "leads.db").close()
    expired = backup / "leads-2020-01-01.db"
    expired.write_bytes(b"old backup")
    age(expired, 100)
    # 清理只看 mtime、不看文件名里的日期；名字避开今天，否则会被这次备份覆盖
    fresh = backup / "leads-2020-06-01.db"
    fresh.write_bytes(b"recent backup")
    age(fresh, 1)
    # 同样过期，但不叫 leads-*.db：不归这个脚本管
    other = backup / "leads.csv"
    other.write_bytes(b"id,company\n")
    age(other, 100)

    result = run_script("backup.sh", str(data), str(backup), "30")

    assert result.returncode == 0, result.stderr
    assert not expired.exists()
    assert fresh.exists()
    assert other.exists()
    assert backup_path(result).is_file()


def test_restore_puts_the_backup_back_and_clears_wal_shm(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    backup = tmp_path / "backup"
    backup.mkdir()
    make_wal_db(data / "leads.db").close()
    out = backup_path(run_script("backup.sh", str(data), str(backup), "30"))
    conn = sqlite3.connect(data / "leads.db")
    conn.execute("delete from leads")
    conn.commit()
    conn.close()
    (data / "leads.db-wal").write_bytes(b"")
    (data / "leads.db-shm").write_bytes(b"")

    result = run_script("restore.sh", str(out), str(data))

    assert result.returncode == 0, result.stderr
    # 先断言 -wal / -shm 没了：打开恢复后的库会把它们重新造出来
    assert not (data / "leads.db-wal").exists()
    assert not (data / "leads.db-shm").exists()
    assert count_rows(data / "leads.db") == 3
    assert list(data.glob("leads.db.pre-restore-*")), "现有库应留底"
    assert "已恢复" in result.stdout


def test_restore_refuses_a_file_that_is_not_a_sqlite_db(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    make_wal_db(data / "leads.db").close()
    junk = tmp_path / "junk.db"
    junk.write_bytes(b"not a database")

    result = run_script("restore.sh", str(junk), str(data))

    assert result.returncode != 0
    assert "不是完好的 SQLite 库" in result.stderr
    assert count_rows(data / "leads.db") == 3
    assert not list(data.glob("leads.db.pre-restore-*")), "拒绝发生在留底之前"


def test_backup_fails_when_the_data_dir_has_no_leads_db(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    backup = tmp_path / "backup"

    result = run_script("backup.sh", str(data), str(backup), "30")

    assert result.returncode == 1
    assert "找不到" in result.stderr
    assert not backup.exists(), "源库都没有，别顺手建备份目录"
