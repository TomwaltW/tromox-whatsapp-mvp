"""CSV 镜像的写后合并：单条回调立即落盘，一阵回调只重写一次，flush / 退出前补写。

计文件被替换的次数（`os.replace`）而不是计时：判据是"整表重写了几次"，与机器快慢无关。
"""
from __future__ import annotations

import csv
import os
import threading
import time
from pathlib import Path
from unittest.mock import patch

from app.config import Settings
from app.store import CsvExportSink, SqliteStore, build_sinks
from tromox_lead import B2BType, Lead, Segment


def mk_lead(i: int) -> Lead:
    return Lead(lead_id=f"L-{i:06d}", phone=f"+49151{i:08d}", segment=Segment.B2B,
                b2b_type=B2BType.DEALER, company=f"Firma {i} GmbH")


def seeded_store(tmp_path: Path, n: int) -> SqliteStore:
    store = SqliteStore(tmp_path / "leads.db")
    for i in range(n):
        store.update_lead(f"+49151{i:08d}", lambda _existing, i=i: mk_lead(i))
    return store


def csv_phones(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [row["phone"] for row in csv.DictReader(fh)]


class CountingReplace:
    """os.replace 的计数包装：sink 是按模块属性调用它的，所以 patch 得到的就是真实次数。"""

    def __init__(self) -> None:
        self.n = 0
        self._real = os.replace

    def __call__(self, src, dst):
        self.n += 1
        return self._real(src, dst)


def test_a_burst_inside_the_interval_rewrites_the_file_at_most_twice(tmp_path):
    store = seeded_store(tmp_path, 0)
    path = tmp_path / "leads.csv"
    fake = {"t": 1000.0}
    sink = CsvExportSink(store, path, min_interval_s=5.0, clock=lambda: fake["t"])
    counter = CountingReplace()
    with patch.object(os, "replace", counter):
        for i in range(50):                        # 一条回调 = 一条新线索入库 + 一次 upsert
            store.update_lead(f"+49151{i:08d}", lambda _e, i=i: mk_lead(i))
            sink.upsert_lead(mk_lead(i))
            fake["t"] += 0.01                      # 全部 50 条落在同一个 5 秒窗口里
        during_burst = counter.n
        assert during_burst == 1                   # 第一条立即写，其余只标脏
        assert csv_phones(path) == ["+49151" + "0" * 8]        # 此刻文件只反映第一条
        sink.flush()
        assert counter.n == during_burst + 1       # 补写一次，不是 50 次
    assert len(csv_phones(path)) == 50
    assert not list(tmp_path.glob(".leads-*.tmp"))             # 原子替换不留临时文件


def test_the_first_callback_is_written_immediately_and_flush_is_a_no_op_when_clean(tmp_path):
    store = seeded_store(tmp_path, 3)
    sink = CsvExportSink(store, tmp_path / "leads.csv", min_interval_s=60.0)
    counter = CountingReplace()
    with patch.object(os, "replace", counter):
        sink.upsert_lead(mk_lead(0))
        assert counter.n == 1 and len(csv_phones(tmp_path / "leads.csv")) == 3
        assert sink.flush() == 0                   # 没有待写的，就不该再动文件
        assert counter.n == 1


def test_zero_interval_keeps_the_old_write_every_callback_behaviour(tmp_path):
    store = seeded_store(tmp_path, 4)
    sink = CsvExportSink(store, tmp_path / "leads.csv", min_interval_s=0)
    counter = CountingReplace()
    with patch.object(os, "replace", counter):
        for i in range(20):
            sink.upsert_lead(mk_lead(i))
    assert counter.n == 20
    assert len(csv_phones(tmp_path / "leads.csv")) == 4


def test_a_pending_write_lands_on_its_own_when_the_interval_expires(tmp_path):
    """没有第二次 flush / 回调，到期的定时器也要把文件补齐——服务空闲时镜像不会一直停在旧版本。"""
    store = seeded_store(tmp_path, 2)
    path = tmp_path / "leads.csv"
    sink = CsvExportSink(store, path, min_interval_s=0.05)
    sink.upsert_lead(mk_lead(0))                   # 立即写
    store.update_lead("+4915199999999", lambda _e: mk_lead(99))
    sink.upsert_lead(mk_lead(99))                  # 在窗口内：只标脏
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and len(csv_phones(path)) < 3:
        time.sleep(0.01)
    assert len(csv_phones(path)) == 3
    assert sink.flush() == 0                       # 定时器写完就不脏了
    sink.close()


def test_concurrent_upserts_do_not_raise_and_flush_leaves_the_full_table(tmp_path):
    store = seeded_store(tmp_path, 30)
    sink = CsvExportSink(store, tmp_path / "leads.csv", min_interval_s=5.0)
    errors: list[BaseException] = []

    def worker(base: int) -> None:
        try:
            for i in range(20):
                sink.upsert_lead(mk_lead((base + i) % 30))
        except BaseException as exc:  # noqa: BLE001 - 线程里的异常要带回主线程断言
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(t * 5,)) for t in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    sink.flush()
    assert len(csv_phones(tmp_path / "leads.csv")) == 30


def test_build_sinks_takes_the_interval_from_settings_and_still_accepts_the_old_signature(tmp_path):
    settings = Settings(_env_file=None, botmaker_webhook_token="t", csv_export_min_interval_s=12.5,
                        database_path=tmp_path / "l.db", csv_export_path=tmp_path / "l.csv")
    store = SqliteStore(settings.database_path)
    sink, = build_sinks(["sqlite", "csv"], store, settings.csv_export_path, settings=settings)
    assert sink.name == "csv" and sink.min_interval_s == 12.5

    legacy, = build_sinks(["sqlite", "csv"], store, tmp_path / "old.csv")
    assert legacy.name == "csv" and legacy.min_interval_s == 5.0
