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
import io
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from tromox_lead import LABEL_COLUMNS, country_from_phone, detect_language, normalize_e164

from .data import looks_excel_mangled

EXIT_OK, EXIT_ERROR, EXIT_NO_TEXT_COLUMN = 0, 1, 2

# 与 04-eval/eval/report.py 第 11–12 行的 _EMAIL_RE / _DIGITS_RE 相同（抄一份，不 import 私有名）。
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_DIGITS_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")

# 列自动识别：大小写不敏感、按"包含"匹配，按 text → phone → date → channel 的顺序认领，已认领的列不再参与。
# 同一角色有几列命中时取档位靠前的（_rank 数字小），同档取最左边的：
#   正文：同时命中日期提示或编号提示的表头（咨询时间、Message ID、Conversation ID）排在后面，别无选择才用；
#   号码：命中 phone / 号码 / 电话 / mobile / whatsapp / 整词 wa 的排在只命中 number 的（Ticket Number）前面。
COLUMN_HINTS: dict[str, tuple[str, ...]] = {
    "text": ("message", "text", "content", "内容", "消息", "咨询", "conversation", "正文"),
    "phone": ("phone", "number", "mobile", "号码", "电话", "whatsapp"),
    "date": ("date", "time", "时间", "日期"),
    "channel": ("channel", "source", "platform", "来源", "渠道", "平台"),
}
PHONE_WORD_HINTS: tuple[str, ...] = ("wa",)          # 两个字母，只按整词匹配（WA Number、wa_id），不命中 Awaiting reply
WEAK_PHONE_HINTS: tuple[str, ...] = ("number",)      # Ticket Number、Order Number 也会命中
ID_HINTS: tuple[str, ...] = ("编号", "序号", "number")
ID_WORD_HINTS: tuple[str, ...] = ("id",)            # 整词：Message ID、message_id、消息ID；不命中 video、paid
_WORD_SPLIT_RE = re.compile(r"[^0-9a-z]+")


class ImportError_(Exception):
    """User-facing failure (bad file, unknown sheet, missing column); message goes to stderr."""


@dataclass(frozen=True)
class ColumnMap:
    text: str
    phone: str | None
    date: str | None
    channel: str | None

    def describe(self) -> str:
        """The stderr line that says which columns were picked, e.g. columns: text=咨询内容 phone=客户电话 ..."""
        return (f"columns: text={self.text} phone={self.phone or '-'} date={self.date or '-'} "
                f"channel={self.channel or '-'}")


@dataclass
class Summary:
    rows_in: int = 0
    rows_out: int = 0
    dropped_empty: int = 0
    dropped_duplicate: int = 0
    phone_excel_mangled: int = 0
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
            f"phone_excel_mangled={self.phone_excel_mangled}",
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
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportError_(f"{path}: 不是 UTF-8 编码（第 {exc.start + 1} 个字节起无法解码）；"
                           "Excel 请另存为『CSV UTF-8（逗号分隔）』，或直接交 .xlsx") from None
    # 按记录读：splitlines() 会在 U+2028 / U+0085 / \x0c 等处断行，把未加引号的单元格切成两条记录。
    reader = csv.reader(io.StringIO(text, newline=""))
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

def _hits(lowered: str, hints: Iterable[str] = (), words: Iterable[str] = ()) -> bool:
    tokens = set(_WORD_SPLIT_RE.split(lowered))
    return any(hint in lowered for hint in hints) or any(word in tokens for word in words)


def _rank(role: str, column: str) -> int | None:
    """0 = best match for the role, 1 = fallback, None = not a candidate."""
    lowered = column.lower()
    if role == "text":
        if not _hits(lowered, COLUMN_HINTS["text"]):
            return None
        return 1 if _hits(lowered, COLUMN_HINTS["date"]) or _hits(lowered, ID_HINTS, ID_WORD_HINTS) else 0
    if role == "phone":
        strong = tuple(h for h in COLUMN_HINTS["phone"] if h not in WEAK_PHONE_HINTS)
        if _hits(lowered, strong, PHONE_WORD_HINTS):
            return 0
        return 1 if _hits(lowered, WEAK_PHONE_HINTS) else None
    return 0 if _hits(lowered, COLUMN_HINTS[role]) else None


def _find(header: Sequence[str], role: str, taken: set[str]) -> str | None:
    best: tuple[int, str] | None = None
    for column in header:
        if column in taken or not column:
            continue
        rank = _rank(role, column)
        if rank is not None and (best is None or rank < best[0]):
            best = (rank, column)
    return best[1] if best else None


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
        found = _find(header, role, taken)
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
    kept: list[tuple[dict[str, str], bool]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        scrubbed = scrub_text(row.get(columns.text, ""))
        if not scrubbed:
            summary.dropped_empty += 1
            continue
        raw_phone = row.get(columns.phone, "") if columns.phone else ""
        mangled = looks_excel_mangled(raw_phone)   # 4.91761E+12 / …678.0：不去猜，留空并计数
        phone = "" if mangled else (normalize_e164(raw_phone) or "")  # 归一化失败留空，不打码
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
        kept.append((record, mangled))
    if limit is not None:
        kept = kept[:limit]
    out = [record for record, _ in kept]
    summary.rows_out = len(out)
    summary.phone_excel_mangled = sum(mangled for _, mangled in kept)
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
    print(columns.describe(), file=sys.stderr)
    records, summary = convert(rows, columns, data_origin=args.data_origin, limit=args.limit)
    write_batch(Path(args.out), records)
    und = summary.languages.get("und", 0)
    if summary.rows_out and und * 2 > summary.rows_out:
        print(f"warning: {und} of {summary.rows_out} rows have language=und - check that text={columns.text} "
              "is the customers' message column (--text-col)", file=sys.stderr)
    print("\n".join(summary.lines()))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
