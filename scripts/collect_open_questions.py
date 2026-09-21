#!/usr/bin/env python3
"""Generate 99-internal/open-questions.md from the three markers found across the repo.

Markers -> owner:  【待核实】 -> 集成工程师（沈思锴）   【待客户确认】 -> 客户（经张宝文 / Kim）   【张宝文确认】 -> 张宝文
The curated top section lives in scripts/open_questions_preamble.md (hand-written); the full index is generated.

    python scripts/collect_open_questions.py          # write
    python scripts/collect_open_questions.py --check  # exit 1 if stale
"""
from __future__ import annotations

import re
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "99-internal" / "open-questions.md"
PREAMBLE = ROOT / "scripts" / "open_questions_preamble.md"
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "data"}
SUFFIXES = {".md", ".csv", ".py", ".json", ".example"}
MARKERS = OrderedDict([
    ("【待核实】", ("我要做的：平台、政策、价格类事实核实", "集成工程师（沈思锴）")),
    ("【张宝文确认】", ("张宝文要定的：商务数字与承诺", "张宝文")),
    ("【待客户确认】", ("客户要给的：需摩兽提供或拍板", "客户（经张宝文 / Kim 对接）")),
])
SELF_FILES = {"99-internal/open-questions.md", "scripts/collect_open_questions.py", "scripts/open_questions_preamble.md",
              "scripts/check_repo.py"}
# Lines that only explain the marker convention, not a real open item.
CONVENTION = re.compile(r"三类标记|标记含义|Exactly three markers|markers? spelled|标【待核实】【待客户确认】")


def clean(line: str) -> str:
    text = re.sub(r"^[\s>#*\-|0-9.]+", "", line.strip())
    text = re.sub(r"\s*\|\s*", " / ", text).strip(" /")
    text = re.sub(r"`", "", text)
    text = re.sub(r"https?://\S+", "（链接见出处）", text)  # the source file:line carries the link
    return (text[:170] + "…") if len(text) > 170 else text


def collect() -> dict[str, list[tuple[str, str, int]]]:
    found: dict[str, list[tuple[str, str, int]]] = {m: [] for m in MARKERS}
    seen: dict[str, set[str]] = {m: set() for m in MARKERS}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in SUFFIXES:
            continue
        rel = path.relative_to(ROOT)
        if set(rel.parts) & SKIP_DIRS or rel.as_posix() in SELF_FILES:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if CONVENTION.search(line):
                continue
            for marker in MARKERS:
                if marker in line:
                    text = clean(line)
                    key = re.sub(r"\W+", "", text)[:80]
                    if key and key not in seen[marker]:
                        seen[marker].add(key)
                        found[marker].append((text, rel.as_posix(), number))
    return found


def render(found: dict[str, list[tuple[str, str, int]]]) -> str:
    out = [
        "# 待决问题汇总（内部）",
        "",
        "> 用途：全仓库所有【待核实】【待客户确认】【张宝文确认】的汇总，按负责人分组；每条都有负责人与出处。读者：沈思锴、张宝文。**内部文件，不进客户文档。**",
        "> 第 1 节为人工整理的重点清单；第 2 节起由 `scripts/collect_open_questions.py` 自动生成，请勿手改，改完文档后重跑脚本。",
        "",
    ]
    if PREAMBLE.exists():
        out += [PREAMBLE.read_text(encoding="utf-8").strip(), ""]
    out += ["## 2. 全量索引：数量", "", "| 标记 | 负责人 | 条数（去重后） |", "|---|---|---|"]
    for marker, (_, owner) in MARKERS.items():
        out.append(f"| {marker} | {owner} | {len(found[marker])} |")
    out.append("")
    for index, (marker, (title, owner)) in enumerate(MARKERS.items(), start=3):
        out += [f"## {index}. {title}", "", f"负责人：{owner}", "", "| # | 事项 | 出处 | 负责人 |", "|---|---|---|---|"]
        for number, (text, rel, line) in enumerate(found[marker], start=1):
            out.append(f"| {number} | {text.replace('|', '/')} | `{rel}:{line}` | {owner} |")
        out.append("")
    return "\n".join(out)


def main() -> int:
    content = render(collect())
    if "--check" in sys.argv:
        stale = not OUT.exists() or OUT.read_text(encoding="utf-8") != content
        print("STALE: 99-internal/open-questions.md" if stale else "open-questions.md up to date")
        return 1 if stale else 0
    OUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
