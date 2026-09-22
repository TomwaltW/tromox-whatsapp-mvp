"""运行指标：给 `GET /metrics` 与健康告警脚本用的只读统计。

只读打开 SQLite（`mode=ro`，与 `app/report.py` 同一做法），不改表、不经过 store。
口径（窗口 = 最近 `hours` 小时，按库里的 ISO 时间戳字符串比较，格式与 `sqlite_store._now()` 一致）：

- `callbacks`：`processed_events` 中 `processed_at` 在窗口内的行数，`by_outcome` 按 `outcome` 计数；
- `notifications.by_status`：`notifications` 全表按 `status` 计数（五种状态键固定存在）；
  `failed_24h` = 窗口内 `created_at` 且 `status='failed'`；`pending` = 全表 `pending`；
- `raw_events_unprocessed`：`raw_events.processed = 0` 的行数（回放没跟上 / 处理一直失败的堆积）；
- `last_callback_at`：`raw_events.received_at` 最大值，没有则 null；
- `leads_total`：`leads` 行数。

库文件不存在或表为空都不报错，返回全 0。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

NOTIFICATION_STATUSES = ("sent", "partial", "failed", "pending", "skipped")
OUTCOMES = ("lead_upserted",)
MIN_HOURS, MAX_HOURS, DEFAULT_HOURS = 1, 168, 24


def _utc(now: datetime | None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now if now.tzinfo else now.replace(tzinfo=timezone.utc)


def _empty(now: datetime, hours: int) -> dict[str, Any]:
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_hours": hours,
        "callbacks": {"total": 0, "by_outcome": {o: 0 for o in OUTCOMES}},
        "notifications": {"by_status": {s: 0 for s in NOTIFICATION_STATUSES}, "failed_24h": 0, "pending": 0},
        "raw_events_unprocessed": 0,
        "last_callback_at": None,
        "leads_total": 0,
    }


def collect(db_path: Path | str, *, hours: int = DEFAULT_HOURS, now: datetime | None = None) -> dict[str, Any]:
    if not MIN_HOURS <= hours <= MAX_HOURS:
        raise ValueError(f"hours must be between {MIN_HOURS} and {MAX_HOURS}, got {hours}")
    now = _utc(now).astimezone(timezone.utc)
    result = _empty(now, hours)
    path = Path(db_path)
    if not path.is_file():
        return result
    since = (now - timedelta(hours=hours)).isoformat(timespec="milliseconds")

    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        for outcome, n in conn.execute(
            "SELECT outcome, COUNT(*) FROM processed_events WHERE processed_at >= ? GROUP BY outcome", (since,)
        ):
            result["callbacks"]["by_outcome"][outcome] = n
            result["callbacks"]["total"] += n
        for status, n in conn.execute("SELECT status, COUNT(*) FROM notifications GROUP BY status"):
            result["notifications"]["by_status"][status] = n
        result["notifications"]["pending"] = result["notifications"]["by_status"]["pending"]
        result["notifications"]["failed_24h"] = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE status = 'failed' AND created_at >= ?", (since,)
        ).fetchone()[0]
        result["raw_events_unprocessed"] = conn.execute(
            "SELECT COUNT(*) FROM raw_events WHERE processed = 0"
        ).fetchone()[0]
        result["last_callback_at"] = conn.execute("SELECT MAX(received_at) FROM raw_events").fetchone()[0]
        result["leads_total"] = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    finally:
        conn.close()
    return result
