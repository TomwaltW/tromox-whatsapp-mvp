#!/usr/bin/env python3
"""Generate the on-site UAT record sheet (xlsx) from the 20 UAT cases and the replay manifest.

    python scripts/gen_uat_sheet.py --out dist/uat-record-2026-10-30.xlsx
    python scripts/gen_uat_sheet.py --out dist/uat-record.xlsx --date 2026-10-30 \
        [--cases-md 06-acceptance/uat-test-cases.md] \
        [--manifest 05-integration/webhook-service/fixtures/uat/manifest.json]

Sources (read only, never written back):
  * 06-acceptance/uat-test-cases.md  section 2 (the 20-row case table), section 4 (language plan table),
    section 1 (numbered execution notes). That file is the requirement source; this script only reads it.
  * fixtures/uat/manifest.json  `cases.<Uxx>.expect`: the service-layer expectation of the replay test.

Workbook (three sheets, fixed names):
  用例      header fixed to 15 columns; rows U01…U20 in md order; column "服务层期望（回放）" renders
            `expect` as `lead.segment=B2B; lead.b2b_type=dealer; notifications=1; tags=seg_b2b,prio_high`
            (key path joined with `.`, list of scalars joined with `,`, list of objects indexed `lead[1].phone`,
            JSON scalars `true` / `false` / `null`, empty list or empty string renders as nothing after `=`);
            the last 6 columns are left blank for the site (结果 has a 通过 / 失败 / 阻塞 drop-down).
  语种安排  section 4 table as is.
  说明      section 1 notes one per row, then two provenance rows (sources, date + command).

Markdown cells: `<br>` -> newline, backticks stripped, `\\|` -> `|`. Exit 0 and print `cases=20 out=<path>`;
exit 2 when the md does not hold exactly 20 cases or a case is missing from the manifest. Needs openpyxl.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MD = ROOT / "06-acceptance/uat-test-cases.md"
DEFAULT_MANIFEST = ROOT / "05-integration/webhook-service/fixtures/uat/manifest.json"

CASE_HEADER = ["用例", "场景", "语种", "输入", "期望分类", "期望动作", "期望通知", "通过标准",
               "服务层期望（回放）", "结果", "通知时延（秒）", "执行日期", "执行人", "见证人", "问题与修复"]
MD_CASE_COLUMNS = 8          # `# | 场景 | 语种 | 输入 | 期望分类 | 期望动作 | 期望通知 | 通过标准`
SITE_COLUMNS = 6             # 结果 … 问题与修复, left blank
RESULT_OPTIONS = "通过,失败,阻塞"
EXPECTED_CASES = 20
CASE_WIDTHS = [7, 22, 7, 40, 40, 36, 30, 32, 44, 9, 13, 12, 10, 10, 30]

_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


# ---------- markdown ----------

def cell_text(raw: str) -> str:
    """Markdown table cell -> plain text: <br> to newline, drop backticks, unescape pipes."""
    text = re.sub(r"<br\s*/?>", "\n", raw.strip(), flags=re.IGNORECASE)
    text = text.replace("`", "").replace("\\|", "|")
    return "\n".join(part.strip() for part in text.split("\n"))


def split_row(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [cell_text(c) for c in _UNESCAPED_PIPE.split(body)]


def section(text: str, number: int) -> str:
    """Body of `## <number>.` up to the next `## ` heading."""
    match = re.search(rf"^## {number}\.[^\n]*\n(.*?)(?=^## |\Z)", text, flags=re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"section {number} not found in the markdown")
    return match.group(1)


def table_rows(body: str) -> list[list[str]]:
    """All rows of the first table in the body, header first, separator row dropped."""
    rows: list[list[str]] = []
    for line in body.splitlines():
        if not line.lstrip().startswith("|"):
            if rows:
                break
            continue
        if re.fullmatch(r"\|(\s*:?-+:?\s*\|)+", line.strip()):
            continue
        rows.append(split_row(line))
    return rows


def parse_cases(text: str) -> list[list[str]]:
    rows = [r for r in table_rows(section(text, 2)) if re.fullmatch(r"U\d\d", r[0])]
    bad = [r[0] for r in rows if len(r) != MD_CASE_COLUMNS]
    if bad:
        raise ValueError(f"case rows with a column count other than {MD_CASE_COLUMNS}: {bad}")
    return rows


def parse_notes(text: str) -> list[str]:
    notes = []
    for line in section(text, 1).splitlines():
        match = re.match(r"^\s*(\d+)\.\s+(.*\S)\s*$", line)
        if match:
            notes.append(f"{match.group(1)}. {cell_text(match.group(2))}")
    return notes


# ---------- manifest ----------

def render_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def flatten_expect(value: object, path: str = "") -> list[str]:
    """`expect` -> ["lead.segment=B2B", "tags=seg_b2b,prio_high", ...] in manifest order."""
    if isinstance(value, dict):
        out: list[str] = []
        for key, sub in value.items():
            out.extend(flatten_expect(sub, f"{path}.{key}" if path else str(key)))
        return out
    if isinstance(value, list):
        if all(isinstance(v, (dict, list)) for v in value) and value:
            out = []
            for index, sub in enumerate(value):
                out.extend(flatten_expect(sub, f"{path}[{index}]"))
            return out
        return [f"{path}={','.join(render_scalar(v) for v in value)}"]
    return [f"{path}={render_scalar(value)}"]


def render_expect(expect: dict) -> str:
    return "; ".join(flatten_expect(expect))


# ---------- workbook ----------

def _style_header(ws, width_list: list[int]) -> None:
    fill = PatternFill("solid", fgColor="DDEBF7")
    for index, cell in enumerate(ws[1], start=1):
        cell.font = Font(bold=True)
        cell.fill = fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[get_column_letter(index)].width = width_list[index - 1] if index <= len(width_list) else 20
    ws.freeze_panes = "A2"


def _wrap_body(ws) -> None:
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")


def build_workbook(cases: list[list[str]], expects: dict[str, str], lang_rows: list[list[str]],
                   notes: list[str], generated: str, command: str, md_label: str, manifest_label: str) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "用例"
    ws.append(CASE_HEADER)
    for row in cases:
        ws.append([*row, expects[row[0]], *([None] * SITE_COLUMNS)])
    _style_header(ws, CASE_WIDTHS)
    _wrap_body(ws)
    dv = DataValidation(type="list", formula1=f'"{RESULT_OPTIONS}"', allow_blank=True, showDropDown=False)
    dv.error = f"只能填 {RESULT_OPTIONS.replace(',', ' / ')}"
    dv.errorTitle = "结果"
    ws.add_data_validation(dv)
    result_col = get_column_letter(CASE_HEADER.index("结果") + 1)
    dv.add(f"{result_col}2:{result_col}{len(cases) + 1}")

    ws_lang = wb.create_sheet("语种安排")
    for row in lang_rows:
        ws_lang.append(row)
    _style_header(ws_lang, [12, 60, 44])
    _wrap_body(ws_lang)

    ws_notes = wb.create_sheet("说明")
    for note in notes:
        ws_notes.append([note])
    ws_notes.append([f"生成自：{md_label} + {manifest_label}"])
    ws_notes.append([f"生成日期：{generated}　命令：{command}"])
    ws_notes.column_dimensions["A"].width = 110
    for row in ws_notes.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    return wb


def generate(md_path: Path, manifest_path: Path, out: Path, generated: str, command: str) -> int:
    text = md_path.read_text(encoding="utf-8")
    cases = parse_cases(text)
    if len(cases) != EXPECTED_CASES:
        raise ValueError(f"expected {EXPECTED_CASES} cases in section 2, found {len(cases)}")
    manifest_cases = json.loads(manifest_path.read_text(encoding="utf-8"))["cases"]
    missing = [row[0] for row in cases if row[0] not in manifest_cases or "expect" not in manifest_cases[row[0]]]
    if missing:
        raise ValueError(f"cases without an `expect` in the manifest: {missing}")
    expects = {row[0]: render_expect(manifest_cases[row[0]]["expect"]) for row in cases}
    lang_rows = table_rows(section(text, 4))
    notes = parse_notes(text)

    def label(path: Path) -> str:
        try:
            return path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            return path.as_posix()

    md_label = label(md_path)
    manifest_label = label(manifest_path).replace("05-integration/webhook-service/", "")
    wb = build_workbook(cases, expects, lang_rows, notes, generated, command, md_label, manifest_label)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return len(cases)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate the UAT on-site record sheet (xlsx).")
    ap.add_argument("--out", required=True, help="output .xlsx path; parent directory is created")
    ap.add_argument("--cases-md", default=str(DEFAULT_MD))
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--date", default=date.today().isoformat(), help="generation date, YYYY-MM-DD (default today)")
    args = ap.parse_args(argv)
    command = "python scripts/gen_uat_sheet.py " + " ".join(sys.argv[1:] if argv is None else argv)
    try:
        count = generate(Path(args.cases_md), Path(args.manifest), Path(args.out), args.date, command)
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"gen_uat_sheet: {exc}", file=sys.stderr)
        return 2
    print(f"cases={count} out={args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
