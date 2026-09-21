"""Storage: SQLite is the primary store (leads + idempotency ledger); sinks mirror leads."""
from .base import LeadSink, NotificationRow, RawEventState
from .csv_export import CsvExportSink
from .sqlite_store import SqliteStore

__all__ = ["CsvExportSink", "LeadSink", "NotificationRow", "RawEventState", "SqliteStore", "build_sinks"]


def build_sinks(names: list[str], store: SqliteStore, csv_path) -> list[LeadSink]:
    """Instantiate the sinks named in STORAGE_BACKENDS. `sqlite` is always on (it is the
    ledger), so it is accepted here and skipped. Stub sinks fail fast at start-up."""
    sinks: list[LeadSink] = []
    for name in names:
        if name == "sqlite":
            continue
        if name == "csv":
            sinks.append(CsvExportSink(store, csv_path))
        elif name == "feishu_bitable":
            from .feishu_bitable import FeishuBitableSink
            sinks.append(FeishuBitableSink())
        elif name == "gsheets":
            from .gsheets import GoogleSheetsSink
            sinks.append(GoogleSheetsSink())
        else:
            raise ValueError(f"unknown storage backend: {name!r}")
    return sinks
