"""CLI: python -m eval.import_history --input <export.csv|export.xlsx> --out <labeling-batch.csv>

把客户导出的历史咨询（任意列名的 CSV / XLSX）变成可直接标注的文件：
表头逐字等于 tromox_lead.LABEL_COLUMNS，正文已脱敏，号码已归一化为 E.164，语种已预填，
标注列留空给标注人。输出只该放在被 git 忽略的 data/ 下：号码不打码，eval.data 加载时按 E.164 校验。
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from tromox_lead import LABEL_COLUMNS, country_from_phone, detect_language, normalize_e164

EXIT_OK, EXIT_ERROR, EXIT_NO_TEXT_COLUMN = 0, 1, 2

# 与 04-eval/eval/report.py 第 11–12 行的 _EMAIL_RE / _DIGITS_RE 相同（抄一份，不 import 私有名）。
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_DIGITS_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")

# 列自动识别：大小写不敏感、按"包含"匹配，按 text → phone → date → channel 的顺序认领，已认领的列不再参与。
COLUMN_HINTS: dict[str, tuple[str, ...]] = {
    "text": ("message", "text", "content", "内容", "消息", "咨询", "conversation", "正文"),
    "phone": ("phone", "number", "mobile", "号码", "电话", "whatsapp", "wa"),
    "date": ("date", "time", "时间", "日期"),
    "channel": ("channel", "source", "platform", "来源", "渠道", "平台"),
}


class ImportError_(Exception):
    """User-facing failure (bad file, unknown sheet, missing column); message goes to stderr."""


@dataclass(frozen=True)
class ColumnMap:
    text: str
    phone: str | None
    date: str | None
    channel: str | None


@dataclass
class Summary:
    rows_in: int = 0
    rows_out: int = 0
    dropped_empty: int = 0
    dropped_duplicate: int = 0
    languages: Counter = field(default_factory=Counter)
    countries: Counter = field(default_factory=Counter)

    def lines(self) -> list[str]:
        def fmt(counter: Counter) -> str:
            return ",".join(f"{k}:{v}" for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])))
        return [
            f"rows_in={self.rows_in}",
            f"rows_out={self.rows_out}",
            f"dropped_empty={self.dropped_empty}",
            f"dropped_duplicate={self.dropped_duplicate}",
            f"languages={fmt(self.languages)}",
            f"countries={fmt(self.countries)}",
        ]


# ---------------------------------------------------------------- reading the export

def _cell(value: object) -> str:
    """Excel / CSV cell -> stripped text. None is empty; integral floats lose the '.0' (phone columns)."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, datetime.datetime):  # openpyxl hands date cells back as datetime / date / time
        return value.isoformat(sep=" ")
    if isinstance(value, (datetime.date, datetime.time)):
        return value.isoformat()
    return str(value).strip()


def read_rows(path: Path, sheet: str | None = None) -> tuple[list[str], list[dict[str, str]]]:
    """Return (header, rows) with every value already passed through _cell()."""
    if not path.exists():
        raise ImportError_(f"input not found: {path}")
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        return _read_xlsx(path, sheet)
    if sheet:
        raise ImportError_("--sheet only applies to .xlsx input")
    return _read_csv(path)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    text = path.read_bytes().decode("utf-8-sig")
    reader = csv.reader(text.splitlines(keepends=True))
    try:
        header = [_cell(h) for h in next(reader)]
    except StopIteration:
        raise ImportError_(f"empty file: {path}") from None
    rows = []
    for raw in reader:
        values = [_cell(v) for v in raw]
        if not any(values):
            continue
        values += [""] * (len(header) - len(values))
        rows.append(dict(zip(header, values)))
    return header, rows


def _read_xlsx(path: Path, sheet: str | None) -> tuple[list[str], list[dict[str, str]]]:
    try:
        import openpyxl
    except ImportError:  # pragma: no cover - dependency declared in pyproject [eval]
        raise ImportError_("reading .xlsx needs openpyxl: uv pip install -e '.[eval]'") from None
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet is not None:
            if sheet not in wb.sheetnames:
                raise ImportError_(f"sheet {sheet!r} not found; sheets: {', '.join(wb.sheetnames)}")
            ws = wb[sheet]
        else:
            ws = wb.worksheets[0]
        iterator = ws.iter_rows(values_only=True)
        header: list[str] = []
        for first in iterator:
            header = [_cell(h) for h in first]
            break
        if not any(header):
            raise ImportError_(f"empty sheet: {ws.title}")
        rows = []
        for raw in iterator:
            values = [_cell(v) for v in raw]
            if not any(values):
                continue
            values = values[: len(header)] + [""] * (len(header) - len(values))
            rows.append(dict(zip(header, values)))
        return header, rows
    finally:
        wb.close()


# ---------------------------------------------------------------- column detection

def _find(header: Sequence[str], hints: Iterable[str], taken: set[str]) -> str | None:
    for column in header:
        if column in taken or not column:
            continue
        lowered = column.lower()
        if any(hint in lowered for hint in hints):
            return column
    return None


def detect_columns(header: Sequence[str], *, text: str | None = None, phone: str | None = None,
                   date: str | None = None, channel: str | None = None) -> ColumnMap:
    """Explicit names win; the rest is auto-detected (case-insensitive, substring match)."""
    explicit = {"text": text, "phone": phone, "date": date, "channel": channel}
    for role, name in explicit.items():
        if name is not None and name not in header:
            raise ImportError_(f"--{role}-col {name!r} is not a column; header: {', '.join(header)}")
    taken = {name for name in explicit.values() if name}
    chosen: dict[str, str | None] = {}
    for role in ("text", "phone", "date", "channel"):
        if explicit[role] is not None:
            chosen[role] = explicit[role]
            continue
        found = _find(header, COLUMN_HINTS[role], taken)
        chosen[role] = found
        if found:
            taken.add(found)
    if not chosen["text"]:
        raise ImportError_("cannot find the conversation text column (use --text-col); "
                           f"header: {', '.join(header)}")
    return ColumnMap(text=chosen["text"], phone=chosen["phone"], date=chosen["date"], channel=chosen["channel"])


# ---------------------------------------------------------------- transformation

def scrub_text(text: str) -> str:
    """Mask e-mail addresses and long digit runs, collapse whitespace. Same masks as report.excerpt()."""
    masked = _DIGITS_RE.sub("<number>", _EMAIL_RE.sub("<email>", text or ""))
    return " ".join(masked.split())


def sample_id(phone: str, scrubbed_text: str) -> str:
    return "H-" + hashlib.sha1(f"{phone}|{scrubbed_text}".encode("utf-8")).hexdigest()[:8]


def convert(rows: list[dict[str, str]], columns: ColumnMap, *, data_origin: str = "real",
            limit: int | None = None) -> tuple[list[dict[str, str]], Summary]:
    summary = Summary(rows_in=len(rows))
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        scrubbed = scrub_text(row.get(columns.text, ""))
        if not scrubbed:
            summary.dropped_empty += 1
            continue
        raw_phone = row.get(columns.phone, "") if columns.phone else ""
        phone = normalize_e164(raw_phone) or ""  # 归一化失败留空，不打码
        key = (phone, scrubbed)
        if key in seen:
            summary.dropped_duplicate += 1
            continue
        seen.add(key)
        notes = []
        if columns.channel and row.get(columns.channel):
            notes.append(f"来源:{row[columns.channel]}")
        if columns.date and row.get(columns.date):
            notes.append(f"日期:{row[columns.date]}")
        record = {column: "" for column in LABEL_COLUMNS}
        record.update({
            "sample_id": sample_id(phone, scrubbed),
            "data_origin": data_origin,
            "phone": phone,
            "conversation_text": scrubbed,
            "language": detect_language(scrubbed),
            "label_notes": ";".join(notes),
        })
        out.append(record)
    if limit is not None:
        out = out[:limit]
    summary.rows_out = len(out)
    for record in out:
        summary.languages[record["language"]] += 1
        summary.countries[country_from_phone(record["phone"] or None) or "unknown"] += 1
    return out, summary


def write_batch(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(LABEL_COLUMNS))
        writer.writeheader()
        writer.writerows(records)


def check_template() -> list[str]:
    """--check: the header we write must be byte-for-byte the first line of labeling-template.csv."""
    template = Path(__file__).resolve().parents[1] / "labeling-template.csv"
    if not template.exists():
        return [f"template not found: {template}"]
    first = template.read_bytes().decode("utf-8-sig").splitlines()[0] if template.stat().st_size else ""
    expected = ",".join(LABEL_COLUMNS)
    return [] if first == expected else [f"template header differs\n  template: {first}\n  expected: {expected}"]


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m eval.import_history", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="client export: .csv (UTF-8 / UTF-8 BOM) or .xlsx")
    parser.add_argument("--out", required=True, help="labelling CSV to write (keep it under data/, which git ignores)")
    parser.add_argument("--sheet", default=None, help="xlsx worksheet name (default: first sheet)")
    parser.add_argument("--text-col", default=None, help="column with the customer's messages")
    parser.add_argument("--phone-col", default=None, help="column with the customer's number")
    parser.add_argument("--date-col", default=None, help="column with the date / time (goes to label_notes)")
    parser.add_argument("--channel-col", default=None, help="column with the channel / source (goes to label_notes)")
    parser.add_argument("--limit", type=int, default=None, help="keep only the first N rows after de-duplication")
    parser.add_argument("--data-origin", default="real", help="value for the data_origin column (default: real)")
    parser.add_argument("--check", action="store_true",
                        help="only verify that the header equals labeling-template.csv, then exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check:
        problems = check_template()
        for problem in problems:
            print(problem, file=sys.stderr)
        print(f"header={'OK' if not problems else 'MISMATCH'} columns={len(LABEL_COLUMNS)}")
        return EXIT_OK if not problems else EXIT_ERROR
    try:
        header, rows = read_rows(Path(args.input), args.sheet)
        columns = detect_columns(header, text=args.text_col, phone=args.phone_col,
                                 date=args.date_col, channel=args.channel_col)
    except ImportError_ as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_NO_TEXT_COLUMN if "text column" in str(exc) else EXIT_ERROR
    records, summary = convert(rows, columns, data_origin=args.data_origin, limit=args.limit)
    write_batch(Path(args.out), records)
    print("\n".join(summary.lines()))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
