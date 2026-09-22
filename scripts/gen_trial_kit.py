#!/usr/bin/env python3
"""Generate the Botmaker trial sample kit from 02-botmaker/trial-test-plan.md (sections 3 and 4).

    python scripts/gen_trial_kit.py --out-dir dist/trial-kit-2026-10-12
    python scripts/gen_trial_kit.py --out-dir dist/trial-kit-2026-10-12 --date 2026-10-12 \
        [--plan 02-botmaker/trial-test-plan.md] [--data-origin example|synthetic]

Sources (read only, never written back):
  * 02-botmaker/trial-test-plan.md  section 4 (the 20-row sample table S-01…S-20) and section 3 (the platform
    verification table T-1…T-12). That file is the requirement source; this script only reads it.

Outputs (both under --out-dir, which is created):
  trial-samples.csv   header exactly tromox_lead.LABEL_COLUMNS, one row per sample, loadable with
                      eval.data.load_dataset(path, include_examples=True). Mapping from the md columns:
                        sample_id = ID; data_origin = --data-origin (default example); phone blank;
                        conversation_text = 客户输入 (multi-turn "第 1 条：… 第 2 条：…" joined with " / ",
                        prefixes dropped); language = 语种 lower-cased; segment as is;
                        b2b_type / b2c_intent = the md cell routed to the column that matches segment;
                        country_gold = country_stated; product_interest = codes joined with ";";
                        escalation_flag / escalation_reason = the "true / reason" cell split on "/";
                        is_valid_lead blank; annotator = trial-plan; label_notes = 进入方式:<…>;备注:<…>.
                      "空" in the md means blank. When the md lists several acceptable values ("support 或
                      warranty 均可", "任意或空") the CSV takes the first named value, or "other" when the
                      schema requires a value (segment B2B / B2C) and none is named; label_notes records the
                      original wording after a third ";期望取值:" segment so nothing is lost.
  trial-scoring.xlsx  three sheets: 样例 (fixed 18-column header, expected values verbatim from the md,
                      the 实测… / scoring columns left blank for the site), 平台验证项 (section 3 table plus a
                      blank 结果 column), 说明 (source, date, command, the 7 scoring fields, the mapping notes).

Route B comparison: eval.run skips data_origin=example rows (they are template rows there), so run
    python scripts/gen_trial_kit.py --out-dir dist/trial-kit --data-origin synthetic
    cd 04-eval && python -m eval.run --input ../dist/trial-kit/trial-samples.csv --prompt prompts/classify-v1.md --model mock --out /tmp/trial-mock.md
The default (example) keeps the file marked as hand-written plan samples, which is what the acceptance
check expects; load it with include_examples=True.

Markdown cells: `<br>` -> newline, backticks stripped, `\\|` -> `|`. Prints `samples=20 csv=<path> xlsx=<path>`
and exits 0; exits 2 when the md does not hold exactly 20 samples or a table is malformed. Needs openpyxl.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from tromox_lead import LABEL_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "02-botmaker/trial-test-plan.md"
CSV_NAME = "trial-samples.csv"
XLSX_NAME = "trial-scoring.xlsx"
EXPECTED_SAMPLES = 20
ANNOTATOR = "trial-plan"
DATA_ORIGINS = ("example", "synthetic")

# `ID | 语种 | 进入方式 | 客户输入 | segment | b2b_type / b2c_intent | country_stated | product_interest | escalation_flag / reason | 备注`
MD_SAMPLE_COLUMNS = 10
# `编号 | 验证内容 | 步骤要点 | 通过标准 | 结果回填到`
MD_CHECK_COLUMNS = 5
SCORING_FIELDS = ("language", "segment", "b2b_type 或 b2c_intent", "country_stated", "product_interest",
                  "escalation_flag", "escalation_reason")

SAMPLE_HEADER = ["ID", "语种", "进入方式", "客户输入",
                 "期望 segment", "期望 b2b_type/b2c_intent", "期望 country_stated", "期望 product_interest", "期望 escalation",
                 "实测 segment", "实测 b2b_type/b2c_intent", "实测 country_stated", "实测 product_interest", "实测 escalation",
                 "写对的字段数", "回复语言正确", "消息条数", "备注"]
SITE_COLUMNS = 8  # 实测 segment … 消息条数, left blank
SAMPLE_WIDTHS = [7, 6, 22, 60, 12, 20, 14, 16, 26, 12, 20, 14, 16, 26, 12, 12, 10, 40]
CHECK_WIDTHS = [7, 18, 70, 40, 36, 30]
BLANK = "空"

_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")
_TURN_PREFIX = re.compile(r"第\s*\d+\s*条：")
_TOKEN = re.compile(r"[a-z][a-z_]*")
_PRODUCT_SPLIT = re.compile(r"[;,，、/\s]+")


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
        raise ValueError(f"section {number} not found in the plan")
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


def parse_samples(text: str) -> list[list[str]]:
    rows = [r for r in table_rows(section(text, 4)) if re.fullmatch(r"S-\d\d", r[0])]
    bad = [r[0] for r in rows if len(r) != MD_SAMPLE_COLUMNS]
    if bad:
        raise ValueError(f"sample rows with a column count other than {MD_SAMPLE_COLUMNS}: {bad}")
    return rows


def parse_checks(text: str) -> tuple[list[str], list[list[str]]]:
    rows = table_rows(section(text, 3))
    if not rows:
        raise ValueError("section 3 holds no table")
    header, body = rows[0], [r for r in rows[1:] if re.fullmatch(r"T-\d+", r[0])]
    bad = [r[0] for r in body if len(r) != MD_CHECK_COLUMNS]
    if len(header) != MD_CHECK_COLUMNS or bad:
        raise ValueError(f"verification rows with a column count other than {MD_CHECK_COLUMNS}: {bad or header}")
    return header, body


# ---------- md cells -> label values ----------

def blank(value: str) -> str:
    return "" if value.strip() in ("", BLANK) else value.strip()


def conversation_text(raw: str) -> str:
    """"第 1 条：A 第 2 条：B" -> "A / B"; single-turn text is returned as is."""
    parts = [p.strip() for p in _TURN_PREFIX.split(raw) if p.strip()]
    return " / ".join(parts)


def turns(raw: str) -> str:
    """Same split, but one turn per line for the on-site sheet (prefixes kept)."""
    if not _TURN_PREFIX.search(raw):
        return raw
    return "\n".join(m.strip() for m in re.findall(r"第\s*\d+\s*条：.*?(?=第\s*\d+\s*条：|\Z)", raw, flags=re.DOTALL))


def type_or_intent(raw: str, segment: str) -> tuple[str, str | None]:
    """The md cell -> (csv value, note). Note is set when the md allows several values."""
    text = blank(raw)
    if not text:
        return "", None
    tokens = _TOKEN.findall(text)
    single = len(tokens) == 1 and tokens[0] == text
    if single:
        return text, None
    chosen = tokens[0] if tokens else ("other" if segment.upper() in ("B2B", "B2C") else "")
    return chosen, f"期望取值:{text}→{chosen or BLANK}"


def products(raw: str) -> str:
    text = blank(raw)
    return ";".join(t.upper() for t in _PRODUCT_SPLIT.split(text) if t) if text else ""


def escalation(raw: str) -> tuple[str, str]:
    flag, _, reason = raw.partition("/")
    return flag.strip().lower(), blank(reason)


def label_row(row: list[str], data_origin: str) -> dict[str, str]:
    sample_id, lang, entry, text, segment, tio, country, prod, esc, remark = row
    tio_value, note = type_or_intent(tio, segment)
    flag, reason = escalation(esc)
    notes = f"进入方式:{entry};备注:{remark}" + (f";{note}" if note else "")
    return {
        "sample_id": sample_id, "data_origin": data_origin, "phone": "",
        "conversation_text": conversation_text(text),
        "language": lang.strip().lower(), "segment": segment.strip(),
        "b2b_type": tio_value if segment.strip().upper() == "B2B" else "",
        "b2c_intent": tio_value if segment.strip().upper() == "B2C" else "",
        "country_gold": blank(country), "product_interest": products(prod),
        "escalation_flag": flag, "escalation_reason": reason,
        "is_valid_lead": "", "annotator": ANNOTATOR, "label_notes": notes,
    }


# ---------- workbook ----------

def _style_header(ws, widths: list[int]) -> None:
    fill = PatternFill("solid", fgColor="DDEBF7")
    for index, cell in enumerate(ws[1], start=1):
        cell.font = Font(bold=True)
        cell.fill = fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[get_column_letter(index)].width = widths[index - 1] if index <= len(widths) else 20
    ws.freeze_panes = "A2"


def _wrap_body(ws) -> None:
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")


def build_workbook(samples: list[list[str]], check_header: list[str], checks: list[list[str]],
                   notes: list[str]) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "样例"
    ws.append(SAMPLE_HEADER)
    for sample_id, lang, entry, text, segment, tio, country, prod, esc, remark in samples:
        ws.append([sample_id, lang, entry, turns(text), segment, tio, country, prod, esc,
                   *([None] * SITE_COLUMNS), remark])
    _style_header(ws, SAMPLE_WIDTHS)
    _wrap_body(ws)

    ws_checks = wb.create_sheet("平台验证项")
    ws_checks.append([*check_header, "结果"])
    for row in checks:
        ws_checks.append([*row, None])
    _style_header(ws_checks, CHECK_WIDTHS)
    _wrap_body(ws_checks)

    ws_notes = wb.create_sheet("说明")
    for note in notes:
        ws_notes.append([note])
    ws_notes.column_dimensions["A"].width = 120
    for row in ws_notes.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    return wb


def explanation(plan_label: str, generated: str, command: str, data_origin: str, choices: list[str]) -> list[str]:
    notes = [
        f"生成自：{plan_label} 第 3 节（平台验证项）与第 4 节（20 条样例）；该文件是源头，本表只读它，不改它。",
        f"生成日期：{generated}　命令：{command}",
        "样例表：\"期望\" 各列逐字取自计划第 4 节；\"实测\" 各列、写对的字段数、回复语言正确、消息条数由现场填写。",
        "7 个计分字段（每条样例按这 7 项计分，\"应为空\" 也算一项，写了就算错）：" + "、".join(f"{i}. {f}" for i, f in enumerate(SCORING_FIELDS, start=1)),
        "多值期望（如 \"support 或 warranty 均可\"）：实测落在给定取值内即算对；写对的字段数按计划第 5 节的口径填。",
        f"同目录的 {CSV_NAME}：表头等于 tromox_lead.LABEL_COLUMNS，data_origin={data_origin}，annotator={ANNOTATOR}，"
        "供路线 B 离线评测对照（eval.data.load_dataset(..., include_examples=True)）。",
    ]
    if choices:
        notes.append("CSV 里多值期望的取值（原文见样例表，取第一个具名值；schema 要求 B2B/B2C 必填而计划未具名时取 other）：" + "；".join(choices))
    notes.append("平台验证项表：计划第 3 节原样，\"结果\" 列现场填写。")
    return notes


# ---------- entry ----------

def generate(plan: Path, out_dir: Path, generated: str, command: str, data_origin: str) -> tuple[int, Path, Path]:
    text = plan.read_text(encoding="utf-8")
    samples = parse_samples(text)
    if len(samples) != EXPECTED_SAMPLES:
        raise ValueError(f"expected {EXPECTED_SAMPLES} samples in section 4, found {len(samples)}")
    check_header, checks = parse_checks(text)

    labels = [label_row(row, data_origin) for row in samples]
    choices = [f"{r['sample_id']} {r['label_notes'].split(';期望取值:')[1]}" for r in labels if ";期望取值:" in r["label_notes"]]

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path, xlsx_path = out_dir / CSV_NAME, out_dir / XLSX_NAME
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(LABEL_COLUMNS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(labels)

    try:
        plan_label = plan.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        plan_label = plan.as_posix()
    wb = build_workbook(samples, check_header, checks, explanation(plan_label, generated, command, data_origin, choices))
    wb.save(xlsx_path)
    return len(samples), csv_path, xlsx_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate the trial sample kit (labelled CSV + on-site scoring xlsx).")
    ap.add_argument("--out-dir", required=True, help="output directory; created if missing")
    ap.add_argument("--plan", default=str(DEFAULT_PLAN), help="trial test plan markdown (read only)")
    ap.add_argument("--date", default=date.today().isoformat(), help="generation date, YYYY-MM-DD (default today)")
    ap.add_argument("--data-origin", choices=DATA_ORIGINS, default="example",
                    help="data_origin column of the CSV; synthetic lets eval.run consume it (default example)")
    args = ap.parse_args(argv)
    command = "python scripts/gen_trial_kit.py " + " ".join(sys.argv[1:] if argv is None else argv)
    try:
        count, csv_path, xlsx_path = generate(Path(args.plan), Path(args.out_dir), args.date, command, args.data_origin)
    except (ValueError, OSError) as exc:
        print(f"gen_trial_kit: {exc}", file=sys.stderr)
        return 2
    print(f"samples={count} csv={csv_path} xlsx={xlsx_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
