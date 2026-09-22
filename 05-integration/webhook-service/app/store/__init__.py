"""Storage: SQLite is the primary store (leads + idempotency ledger); sinks mirror leads."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base import LeadSink, MirrorError, MirrorRow, NotificationRow, RawEventState
from .csv_export import DEFAULT_MIN_INTERVAL_S, CsvExportSink
from .sqlite_store import SqliteStore

if TYPE_CHECKING:  # pragma: no cover - import for type hints only
    from ..config import Settings

__all__ = ["CsvExportSink", "LeadSink", "MirrorError", "MirrorRow", "NotificationRow", "RawEventState",
           "SqliteStore", "build_sinks"]

# (Settings attribute, environment variable) pairs the feishu_bitable sink cannot run without.
FEISHU_BITABLE_SETTINGS: tuple[tuple[str, str], ...] = (
    ("feishu_app_id", "FEISHU_APP_ID"),
    ("feishu_app_secret", "FEISHU_APP_SECRET"),
    ("feishu_bitable_app_token", "FEISHU_BITABLE_APP_TOKEN"),
    ("feishu_bitable_table_id", "FEISHU_BITABLE_TABLE_ID"),
)


def build_sinks(names: list[str], store: SqliteStore, csv_path, *, settings: Settings | None = None) -> list[LeadSink]:
    """Instantiate the sinks named in STORAGE_BACKENDS. `sqlite` is always on (it is the
    ledger), so it is accepted here and skipped. A sink whose configuration is missing, and
    the remaining stub, fail fast at start-up instead of silently dropping leads.

    `settings` is required for `feishu_bitable` and carries the CSV mirror's write-behind
    interval; callers that need neither may keep the old three-argument form (the csv sink
    then falls back to the default interval)."""
    sinks: list[LeadSink] = []
    for name in names:
        if name == "sqlite":
            continue
        if name == "csv":
            sinks.append(CsvExportSink(store, csv_path, min_interval_s=(
                settings.csv_export_min_interval_s if settings is not None else DEFAULT_MIN_INTERVAL_S)))
        elif name == "feishu_bitable":
            from .feishu_bitable import DEFAULT_BASE_URL, FeishuBitableSink
            missing = [env for attr, env in FEISHU_BITABLE_SETTINGS
                       if settings is None or not str(getattr(settings, attr, "") or "").strip()]
            if missing:
                raise ValueError(
                    "feishu_bitable storage needs " + ", ".join(missing)
                    + (" (build_sinks was called without settings)" if settings is None else "")
                    + "; set them or remove feishu_bitable from STORAGE_BACKENDS"
                )
            assert settings is not None
            # Empty / blank (e.g. `FEISHU_BASE_URL=` left empty in .env) means the Feishu default;
            # anything else must be an https origin, so a typo cannot send the mirror over plain HTTP.
            base_url = str(settings.feishu_base_url or "").strip() or DEFAULT_BASE_URL
            if not base_url.startswith("https://"):
                raise ValueError(
                    f"feishu_bitable storage needs FEISHU_BASE_URL to start with https:// (got {base_url!r});"
                    " leave it empty for " + DEFAULT_BASE_URL
                )
            sinks.append(FeishuBitableSink(settings.feishu_app_id, settings.feishu_app_secret,
                                           settings.feishu_bitable_app_token, settings.feishu_bitable_table_id,
                                           base_url=base_url))
        elif name == "gsheets":
            from .gsheets import GoogleSheetsSink
            sinks.append(GoogleSheetsSink())
        else:
            raise ValueError(f"unknown storage backend: {name!r}")
    return sinks
