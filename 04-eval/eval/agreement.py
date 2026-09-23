"""CLI: python -m eval.agreement --a first.csv --b second.csv [--columns ...] [--min-agreement 0.90] [--out r.md] [--json s.json]

双人标注一致性（labeling-guide.md 第 8 节）：两份 labeling-template.csv 格式的文件按 sample_id 取交集，
逐列算一致率与 Cohen's κ，列出分歧清单；segment / escalation_flag 任一列低于门槛时退出码 3。

退出码：0 通过；2 输入问题（表头不等于 LABEL_COLUMNS、交集为空、--columns 含未知列、文件不是 UTF-8）；3 门槛不过。
只按表头用 csv.DictReader 读，不走 eval.data 的完整校验：第二人可能只标子集、标注列可能未填全。
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from tromox_lead import LABEL_COLUMNS

EXIT_OK, EXIT_INPUT_ERROR, EXIT_LOW = 0, 2, 3
DEFAULT_COLUMNS: tuple[str, ...] = (
    "segment", "escalation_flag", "b2b_type", "b2c_intent", "country_gold", "escalation_reason", "is_valid_lead",
)
GATE_COLUMNS: tuple[str, ...] = ("segment", "escalation_flag")   # 门槛只看这两列，永远参与对比
BOOL_COLUMNS: frozenset[str] = frozenset({"escalation_flag", "is_valid_lead"})
_TRUE = frozenset({"true", "1", "yes", "是"})
_FALSE = frozenset({"false", "0", "no", "否", ""})
DEFAULT_MIN_AGREEMENT = 0.90
_EXCERPT_LEN = 60

# 与 04-eval/eval/report.py 第 11–12 行的 _EMAIL_RE / _DIGITS_RE 相同（抄一份，不 import 私有名）。
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_DIGITS_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")


class AgreementError(Exception):
    """User-facing input problem (header mismatch, empty intersection, unknown column); message goes to stderr."""


@dataclass(frozen=True)
class ColumnStat:
    column: str
    n: int
    agree: int
    kappa: float | None

    @property
    def agreement(self) -> float:
        return self.agree / self.n


@dataclass(frozen=True)
class Disagreement:
    sample_id: str
    column: str
    a: str
    b: str
    excerpt: str


@dataclass(frozen=True)
class AgreementResult:
    common: int
    min_agreement: float
    stats: list[ColumnStat]
    disagreements: list[Disagreement]
    skipped_examples: int
    sizes: tuple[int, int]

    def stat(self, column: str) -> ColumnStat | None:
        return next((s for s in self.stats if s.column == column), None)

    @property
    def passed(self) -> bool:
        return all(s.agreement >= self.min_agreement for c in GATE_COLUMNS if (s := self.stat(c)) is not None)

    @property
    def result(self) -> str:
        return "OK" if self.passed else "LOW"


# --- reading -----------------------------------------------------------------

def read_labels(path: Path) -> tuple[dict[str, dict[str, str]], int]:
    """sample_id -> row. Header must equal LABEL_COLUMNS verbatim. Template example rows are skipped,
    duplicated sample_ids keep the first occurrence (warning on stderr)."""
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AgreementError(f"{path}: 不是 UTF-8 编码（第 {exc.start + 1} 个字节起无法解码）；"
                             "Excel 请另存为『CSV UTF-8（逗号分隔）』") from None
    reader = csv.DictReader(io.StringIO(text, newline=""))
    header = list(reader.fieldnames or [])
    if header != list(LABEL_COLUMNS):
        raise AgreementError(
            f"{path}: header does not equal tromox_lead.LABEL_COLUMNS\n"
            f"  expected: {','.join(LABEL_COLUMNS)}\n  actual:   {','.join(header)}"
        )
    rows: dict[str, dict[str, str]] = {}
    skipped = 0
    for row in reader:
        number = reader.line_num
        if (row.get("data_origin") or "").strip().lower() == "example":
            skipped += 1
            continue
        sample_id = (row.get("sample_id") or "").strip()
        if not sample_id:
            print(f"warning: {path}:{number}: empty sample_id, row ignored", file=sys.stderr)
            continue
        if sample_id in rows:
            print(f"warning: {path}:{number}: duplicate sample_id {sample_id}, first occurrence kept", file=sys.stderr)
            continue
        rows[sample_id] = {k: (v or "") for k, v in row.items() if k is not None}
    return rows, skipped


# --- comparison ---------------------------------------------------------------

def normalize(column: str, value: str) -> str:
    """Trim + lowercase; boolean columns collapse true/1/yes/是 and false/0/no/否/empty. Empty is a value of its own."""
    text = (value or "").strip().lower()
    if column in BOOL_COLUMNS:
        if text in _TRUE:
            return "true"
        if text in _FALSE:
            return "false"
    return text


def cohen_kappa(pairs: Sequence[tuple[str, str]]) -> float | None:
    """Cohen's κ for two raters over the same items; None when undefined (single category or zero denominator)."""
    n = len(pairs)
    if n == 0:
        return None
    observed = sum(1 for a, b in pairs if a == b) / n
    count_a = Counter(a for a, _ in pairs)
    count_b = Counter(b for _, b in pairs)
    categories = set(count_a) | set(count_b)
    if len(categories) < 2:
        return None
    expected = sum((count_a[c] / n) * (count_b[c] / n) for c in categories)
    if expected >= 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def excerpt(text: str) -> str:
    """PII-masked (email / long digit runs), single-line, table-safe, at most 60 chars."""
    masked = _DIGITS_RE.sub("<number>", _EMAIL_RE.sub("<email>", text or ""))
    flat = " ".join(masked.split()).replace("|", "/")
    return flat if len(flat) <= _EXCERPT_LEN else flat[: _EXCERPT_LEN - 1] + "…"


def resolve_columns(requested: Sequence[str] | None) -> list[str]:
    columns = list(requested) if requested else list(DEFAULT_COLUMNS)
    unknown = [c for c in columns if c not in LABEL_COLUMNS]
    if unknown:
        raise AgreementError(f"--columns: not in LABEL_COLUMNS: {', '.join(unknown)}")
    for gate in GATE_COLUMNS:        # the threshold columns are always compared
        if gate not in columns:
            columns.append(gate)
    seen: set[str] = set()
    return [c for c in columns if not (c in seen or seen.add(c))]


def compare(a: dict[str, dict[str, str]], b: dict[str, dict[str, str]], columns: Sequence[str],
            min_agreement: float, skipped_examples: int = 0) -> AgreementResult:
    common_ids = [sid for sid in a if sid in b]
    if not common_ids:
        raise AgreementError("no common sample_id between the two files")
    stats: list[ColumnStat] = []
    disagreements: list[Disagreement] = []
    for column in columns:
        pairs = [(normalize(column, a[sid].get(column, "")), normalize(column, b[sid].get(column, ""))) for sid in common_ids]
        agree = sum(1 for x, y in pairs if x == y)
        stats.append(ColumnStat(column=column, n=len(pairs), agree=agree, kappa=cohen_kappa(pairs)))
        for sid, (x, y) in zip(common_ids, pairs):
            if x != y:
                text = a[sid].get("conversation_text") or b[sid].get("conversation_text") or ""
                disagreements.append(Disagreement(sample_id=sid, column=column, a=x, b=y, excerpt=excerpt(text)))
    order = {sid: i for i, sid in enumerate(common_ids)}
    disagreements.sort(key=lambda d: (order[d.sample_id], columns.index(d.column)))   # grouped per sample, file order
    return AgreementResult(common=len(common_ids), min_agreement=min_agreement, stats=stats,
                           disagreements=disagreements, skipped_examples=skipped_examples, sizes=(len(a), len(b)))


# --- output -------------------------------------------------------------------

def _fmt(value: float | None) -> str:
    return "null" if value is None else f"{value:.2f}"


def summary_line(result: AgreementResult) -> str:
    seg, esc = result.stat("segment"), result.stat("escalation_flag")
    return (f"common={result.common} segment={_fmt(seg.agreement if seg else None)} "
            f"escalation_flag={_fmt(esc.agreement if esc else None)} kappa_segment={_fmt(seg.kappa if seg else None)} "
            f"result={result.result}")


def to_json(result: AgreementResult) -> dict:
    return {
        "common": result.common,
        "min_agreement": result.min_agreement,
        "columns": {s.column: {"n": s.n, "agree": s.agree, "agreement": round(s.agreement, 4), "kappa": None if s.kappa is None else round(s.kappa, 4)}
                    for s in result.stats},
        "disagreements": [{"sample_id": d.sample_id, "column": d.column, "a": d.a, "b": d.b} for d in result.disagreements],
        "result": result.result,
    }


def _cell(value: str) -> str:
    return "（空）" if value == "" else value.replace("|", "/")


def render_markdown(result: AgreementResult, path_a: str, path_b: str) -> str:
    gate = "、".join(f"`{c}` {_fmt(s.agreement)}" for c in GATE_COLUMNS if (s := result.stat(c)) is not None)
    verdict = "通过" if result.passed else "未通过（先对齐口径、修订标注指南，再重标分歧集中的类型）"
    out = [
        "# 标注一致性",
        "",
        "> 用途：两份独立标注按 sample_id 取交集后的逐列一致率与 Cohen's κ、分歧清单；对应 `labeling-guide.md` 第 8 节的 90% 门槛。"
        "由 `python -m eval.agreement` 生成，请勿手改。",
        "",
        "## 1. 概览",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 文件 A | `{path_a}`（{result.sizes[0]} 条） |",
        f"| 文件 B | `{path_b}`（{result.sizes[1]} 条） |",
        f"| 交集（按 sample_id） | {result.common} 条；跳过模板示例行 {result.skipped_examples} 行 |",
        f"| 门槛 | `segment` 与 `escalation_flag` 一致率 ≥ {result.min_agreement * 100:.0f}% |",
        f"| 门槛列 | {gate} |",
        f"| 分歧 | {len(result.disagreements)} 处 |",
        "",
        f"**结论：{verdict}**",
        "",
        "## 2. 逐列一致率",
        "",
        "| 列 | n | 相同 | 一致率 | Cohen's κ |",
        "|---|---|---|---|---|",
    ]
    out += [f"| `{s.column}` | {s.n} | {s.agree} | {s.agreement * 100:.1f}% | {_fmt(s.kappa)} |" for s in result.stats]
    out += [
        "",
        "> κ 为 null 表示该列在交集里只有一个取值（或分母为 0），无法计算。布尔列（`escalation_flag`、`is_valid_lead`）比较前已归一为 true / false。",
        "",
        "## 3. 分歧清单",
        "",
        "| sample_id | 列 | A | B | 文本摘录 |",
        "|---|---|---|---|---|",
    ]
    if result.disagreements:
        out += [f"| {d.sample_id} | `{d.column}` | {_cell(d.a)} | {_cell(d.b)} | {d.excerpt} |" for d in result.disagreements]
    else:
        out.append("| （无） | | | | |")
    out += ["", "分歧样本由销售负责人裁决，结论与理由写进 `label_notes`（labeling-guide.md 第 8 节第 4 条）。", ""]
    return "\n".join(out)


# --- CLI ----------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m eval.agreement", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--a", required=True, help="first annotator's file (labeling-template.csv format)")
    parser.add_argument("--b", required=True, help="second annotator's file (labeling-template.csv format)")
    parser.add_argument("--columns", default=",".join(DEFAULT_COLUMNS),
                        help=f"comma-separated columns to compare (default: {','.join(DEFAULT_COLUMNS)}); "
                             "segment and escalation_flag are always included")
    parser.add_argument("--min-agreement", type=float, default=DEFAULT_MIN_AGREEMENT,
                        help="threshold for segment / escalation_flag agreement (default: 0.90)")
    parser.add_argument("--out", default=None, help="Markdown report to write")
    parser.add_argument("--json", default=None, help="JSON summary to write")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        columns = resolve_columns([c.strip() for c in args.columns.split(",") if c.strip()])
        rows_a, skipped_a = read_labels(Path(args.a))
        rows_b, skipped_b = read_labels(Path(args.b))
        result = compare(rows_a, rows_b, columns, args.min_agreement, skipped_examples=skipped_a + skipped_b)
    except (AgreementError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    if args.out:
        Path(args.out).write_text(render_markdown(result, args.a, args.b), encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(to_json(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for stat in result.stats:
        print(f"{stat.column}: n={stat.n} agree={stat.agree} agreement={stat.agreement:.2f} kappa={_fmt(stat.kappa)}")
    print(summary_line(result))
    return EXIT_OK if result.passed else EXIT_LOW


if __name__ == "__main__":
    sys.exit(main())
