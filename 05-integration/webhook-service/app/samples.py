"""试用期原始回调样本导出：把 `raw_events.payload_json` 里留存的真实回调脱敏落成文件，并与 fixture 的结构做对照。

    python -m app.samples --out DIR [--db PATH] [--limit 200] [--since YYYY-MM-DD] [--no-redact]

只读打开 SQLite（`mode=ro`），不经过服务、不改库。样本只有在 `KEEP_RAW_PAYLOADS=true` 时才留在库里
（默认落盘即删，见 README 第 6 节），所以这条命令是试用期专用的。

默认脱敏：号码（≥ 9 位的数字串，可带 `+`）只留尾号 4 位；姓名类字段整个换成 `<redacted>`——键名先去掉下划线、
不分大小写再比对，所以 Botmaker 变量的 `contact_name` 与 `contactName` 同算；`events[].info[]` 里 `name` 是
`agentName` 这类的条目，`value` 也换掉；邮箱换成 `<email>`。事件名与结束分类（`events[].name`、`events[].info[].name`）
不是个人数据，照原文保留。消息正文与 `ai_summary` 这类自由文本保留——要看结构就得看到正文落在哪个字段里，
里面的号码与邮箱同样打码，但提到的人名不会被换掉。`--no-redact` 导出原文，只在本机比对时用，stderr 会提醒
不要把目录留在仓库里。

`<out>/schema-summary.md` 是结构摘要：只统计键名与出现次数，不含任何字段值，因此不含号码、姓名与正文；
第 3 节把样本的键与 `fixtures/` 的键对起来，差异就是 README 第 8 节第 1、2、6 条要改 `app/models.py`
与 fixture 的地方。
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

from pydantic import ValidationError

from .logging_setup import mask_phone, redact
from .models import BotmakerWebhook

DEFAULT_LIMIT = 200
SUMMARY_NAME = "schema-summary.md"
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
RAW_WARNING = "WARNING: raw payloads contain personal data; keep this directory out of the repo"

# 键名按 name_key() 规范化（小写、去下划线）后落在这里的字符串值整个换掉：这些字段装的就是人名，打码留尾号没有意义。
# contact_name / first_name / profile_name（Botmaker 变量的写法）与驼峰写法都命中。
NAME_KEYS = frozenset({"firstname", "lastname", "fromname", "contactname", "profilename"})  # 不含裸 name：events[].name / info[].name 是事件类型与结束分类，不是个人数据
# events[].info[] 是 {"name": …, "value": …} 成对的条目：name 规范化后落在这里时，人名在 value 里，value 整个换掉。
NAME_INFO_LABELS = NAME_KEYS | {"agentname", "operatorname"}
REDACTED_NAME = "<redacted>"
REDACTED_EMAIL = "<email>"
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# 整值是号码的字段（contactId / whatsappNumber 这类）按位数判定，口径与 logging_setup 的号码正则一致。
MIN_PHONE_DIGITS = 9

SCOPE_TOP = "顶层"
SCOPE_MESSAGES = "messages[]"
SCOPE_VARIABLES = "variables"
SCOPE_EVENTS = "events[]"
SCOPE_EVENT_INFO = "events[].info[]"
# 前三个每种 kind 都列（没有就写「（无）」），后两个只在有键时才列。
CORE_SCOPES = (SCOPE_TOP, SCOPE_MESSAGES, SCOPE_VARIABLES)
ALL_SCOPES = CORE_SCOPES + (SCOPE_EVENTS, SCOPE_EVENT_INFO)


# ------------------------------------------------------------------ 脱敏
def name_key(key: str) -> str:
    """名字类键的比对口径：小写、去下划线，于是 contact_name / contactName / CONTACT_NAME 是同一个键。"""
    return key.lower().replace("_", "")


def redact_value(value: Any, key: str | None = None) -> Any:
    """递归脱敏一整份 JSON。只动值，不动键名：键名是结构，摘要与差异都靠它。"""
    if isinstance(value, dict):
        out = {k: redact_value(v, k) for k, v in value.items()}
        label = value.get("name")
        if isinstance(label, str) and name_key(label) in NAME_INFO_LABELS and isinstance(out.get("value"), str):
            out["value"] = REDACTED_NAME  # {"name": "agentName", "value": "Li Wei"}：名字在 value 里，name 本身照留
        return out
    if isinstance(value, list):
        return [redact_value(item, key) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, str):
        if key is not None and name_key(key) in NAME_KEYS:
            return REDACTED_NAME
        return redact(_EMAIL_RE.sub(REDACTED_EMAIL, value))
    if isinstance(value, int) and len(str(abs(value))) >= MIN_PHONE_DIGITS:
        return mask_phone(str(abs(value)))
    return value


# ------------------------------------------------------------------ 读库
def open_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"线索库不存在：{path}")
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_rows(conn: sqlite3.Connection, limit: int, since: date | None) -> list[sqlite3.Row]:
    """最新 limit 条留有原文的回调，按时间升序返回。`--since` 按 received_at 的 UTC 日期。"""
    sql = "SELECT id, kind, received_at, payload_json FROM raw_events WHERE payload_json IS NOT NULL AND payload_json != ''"
    params: list[Any] = []
    if since is not None:
        sql += " AND received_at >= ?"
        params.append(since.isoformat())
    sql += " ORDER BY received_at DESC, id DESC LIMIT ?"
    params.append(limit)
    return list(reversed(conn.execute(sql, params).fetchall()))


def stamp(received_at: str) -> str:
    """received_at -> 文件名用的 YYYYMMDDTHHMMSS；解析不了就退回把非数字去掉后取前 15 位。"""
    try:
        return datetime.fromisoformat((received_at or "").replace("Z", "+00:00")).strftime("%Y%m%dT%H%M%S")
    except (TypeError, ValueError):
        return (re.sub(r"\D", "", received_at or "") or "unknown")[:15]


# ------------------------------------------------------------------ 键统计
def payload_kind(payload: dict[str, Any]) -> str:
    try:
        return BotmakerWebhook.model_validate(payload).kind
    except ValidationError:
        return "unknown"


def new_scopes() -> dict[str, Counter]:
    return {scope: Counter() for scope in ALL_SCOPES}


def count_keys(payload: dict[str, Any], scopes: dict[str, Counter]) -> None:
    scopes[SCOPE_TOP].update(payload.keys())
    for message in payload.get("messages") or []:
        if isinstance(message, dict):
            scopes[SCOPE_MESSAGES].update(message.keys())
    variables = payload.get("variables")
    if isinstance(variables, dict):
        scopes[SCOPE_VARIABLES].update(variables.keys())
    for event in payload.get("events") or []:
        if isinstance(event, dict):
            scopes[SCOPE_EVENTS].update(event.keys())
            for info in event.get("info") or []:
                if isinstance(info, dict):
                    scopes[SCOPE_EVENT_INFO].update(info.keys())


def collect_stats(items: Iterable[tuple[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """(kind, payload) 序列 -> {kind: {"count": n, "scopes": {scope: Counter}}}。"""
    stats: dict[str, dict[str, Any]] = {}
    for kind, payload in items:
        entry = stats.setdefault(kind, {"count": 0, "scopes": new_scopes()})
        entry["count"] += 1
        count_keys(payload, entry["scopes"])
    return stats


def fixture_items(fixtures_dir: Path = FIXTURES_DIR) -> list[tuple[str, dict[str, Any]]]:
    """fixtures/*.json 与 fixtures/uat/*.json 里的回调样例；判不出 kind 的文件跳过（uat/manifest.json）。"""
    items: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(fixtures_dir.glob("*.json")) + sorted(fixtures_dir.glob("uat/*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        kind = payload_kind(payload)
        if kind != "unknown":
            items.append((kind, payload))
    return items


# ------------------------------------------------------------------ 摘要
def _scopes_to_list(scopes: dict[str, Counter]) -> list[str]:
    """要列出来的 scope：三个固定的 + 有键的事件两项。"""
    return [s for s in ALL_SCOPES if s in CORE_SCOPES or scopes.get(s)]


def _key_table(counter: Counter) -> list[str]:
    if not counter:
        return ["（无）", ""]
    lines = ["| 键 | 出现次数 |", "|---|---|"]
    lines += [f"| `{key}` | {count} |" for key, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))]
    lines.append("")
    return lines


def _diff_cell(keys: Iterable[str]) -> str:
    ordered = sorted(keys)
    return "、".join(f"`{key}`" for key in ordered) if ordered else "（无）"


def render_summary(sample_stats: dict[str, dict[str, Any]], fixture_stats: dict[str, dict[str, Any]],
                   total: int, time_range: tuple[str, str] | None) -> str:
    kind_counts = {kind: entry["count"] for kind, entry in sorted(sample_stats.items())}
    lines = [
        "# 回调结构摘要",
        "",
        "由 `python -m app.samples` 生成。本文件只统计键名与出现次数，不含任何字段值，"
        "因此不含号码、姓名与消息正文，可以直接贴进仓库或发给同事。",
        f"生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        f"同目录的样本文件默认脱敏：键名去掉下划线、不分大小写后是 {'、'.join(sorted(NAME_KEYS))} 的字符串值"
        f"整个换成 `{REDACTED_NAME}`（`contact_name`、`first_name`、`profileName` 都算）；"
        f"`events[].info[]` 里 `name` 是 `agentName` / `operatorName` 或上述名字类键的条目，`value` 也换成 `{REDACTED_NAME}`；"
        f"号码（≥ {MIN_PHONE_DIGITS} 位的数字串）只留尾号 4 位，邮箱换成 `{REDACTED_EMAIL}`。"
        "事件名与结束分类不打码：`events[].name`、`events[].info[].name` 是事件类型，不是个人数据，导出里照原文保留。"
        "消息正文与 `ai_summary` 这类自由文本同样保留（结构对照要看正文落在哪个字段），里面的号码与邮箱照样处理，"
        "但提到的人名不会被换掉——样本文件只留在本机，别提交。",
        "",
        "## 1. 样本",
        "",
        f"- 条数：{total}",
        "- kind 分布：" + ("、".join(f"{kind} {count}" for kind, count in kind_counts.items()) or "（无）"),
        "- 时间范围：" + (f"`{time_range[0]}` 至 `{time_range[1]}`（`raw_events.received_at`）"
                     if time_range else "（无样本）"),
        "",
        "## 2. 每种 kind 的键",
        "",
    ]
    if not sample_stats:
        lines += ["（本次没有样本，只有下面第 3 节的 fixture 侧统计。）", ""]
    for kind, entry in sorted(sample_stats.items()):
        lines += [f"### {kind}（{entry['count']} 条）", ""]
        for scope in _scopes_to_list(entry["scopes"]):
            lines += [f"{scope}：", ""]
            lines += _key_table(entry["scopes"][scope])
    lines += [
        "## 3. 与 fixture 的差异",
        "",
        "fixture 侧统计 `fixtures/*.json` 与 `fixtures/uat/*.json`，判不出 `kind` 的文件跳过"
        "（`uat/manifest.json` 是用例清单、不是回调）。`_note` 是 fixture 自带的中文注解字段，"
        "真实回调不会有，出现在「fixture 有样本没有」里属正常。",
        "",
        "「样本有 fixture 没有」的键要补进 `app/models.py` 与 `fixtures/`；"
        "「fixture 有样本没有」的键先确认是这批样本没覆盖到的场景，还是 fixture 本来就写错了"
        "（README 第 8 节第 1、2、6 条）。",
        "",
    ]
    for kind in sorted(set(sample_stats) | set(fixture_stats)):
        sample_entry = sample_stats.get(kind, {"count": 0, "scopes": new_scopes()})
        fixture_entry = fixture_stats.get(kind, {"count": 0, "scopes": new_scopes()})
        lines += [
            f"### {kind}（样本 {sample_entry['count']} 条 / fixture {fixture_entry['count']} 条）",
            "",
            "| 范围 | 样本有 fixture 没有 | fixture 有样本没有 |",
            "|---|---|---|",
        ]
        scopes = [s for s in ALL_SCOPES
                  if s in CORE_SCOPES or sample_entry["scopes"].get(s) or fixture_entry["scopes"].get(s)]
        for scope in scopes:
            sample_keys = set(sample_entry["scopes"][scope])
            fixture_keys = set(fixture_entry["scopes"][scope])
            lines.append(f"| {scope} | {_diff_cell(sample_keys - fixture_keys)} | {_diff_cell(fixture_keys - sample_keys)} |")
        lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------ 导出
def export(db_path: Path, out_dir: Path, limit: int, since: date | None, redact_payloads: bool) -> dict[str, Any]:
    conn = open_readonly(db_path)
    try:
        rows = load_rows(conn, limit, since)
    finally:
        conn.close()

    out_dir.mkdir(parents=True, exist_ok=True)
    items: list[tuple[str, dict[str, Any]]] = []
    written: list[Path] = []
    stamps: list[str] = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"])
        except (TypeError, json.JSONDecodeError):
            continue  # 库里存的不是 JSON（理论上不会有），跳过而不是整次失败
        if not isinstance(payload, dict):
            continue
        kind = row["kind"] or payload_kind(payload)
        items.append((kind, payload))
        stamps.append(row["received_at"])
        path = out_dir / f"{stamp(row['received_at'])}_{kind}_{row['id']}.json"
        body = redact_value(payload) if redact_payloads else payload
        path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(path)

    sample_stats = collect_stats(items)
    fixture_stats = collect_stats(fixture_items())
    time_range = (min(stamps), max(stamps)) if stamps else None
    summary = render_summary(sample_stats, fixture_stats, len(written), time_range)
    (out_dir / SUMMARY_NAME).write_text(summary, encoding="utf-8")
    return {
        "files": written,
        "kinds": {kind: entry["count"] for kind, entry in sorted(sample_stats.items())},
        "summary_path": out_dir / SUMMARY_NAME,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.samples", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True, help="导出目录；不存在会建出来")
    parser.add_argument("--db", type=Path, default=None, help="SQLite 线索库路径；默认取 DATABASE_PATH / .env")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"最多导出几条（取最新的），默认 {DEFAULT_LIMIT}")
    parser.add_argument("--since", help="只导这个 UTC 日期（含）之后收到的回调，YYYY-MM-DD")
    parser.add_argument("--no-redact", dest="redact", action="store_false",
                        help="导出原文，不脱敏；只在本机比对时用")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit 至少是 1")
    since: date | None = None
    if args.since:
        try:
            since = date.fromisoformat(args.since)
        except ValueError as exc:
            parser.error(f"--since 不是合法日期：{exc}")

    db_path = args.db
    if db_path is None:
        from .config import Settings  # 延后导入：只在没给 --db 时才读 .env

        db_path = Settings().database_path

    if not args.redact:
        print(RAW_WARNING, file=sys.stderr)

    try:
        result = export(db_path, args.out, args.limit, since, args.redact)
    except (FileNotFoundError, sqlite3.Error) as exc:
        print(f"samples: {exc}", file=sys.stderr)
        return 2

    kinds = ",".join(f"{kind}:{count}" for kind, count in result["kinds"].items())
    print(f"samples={len(result['files'])} kinds={kinds} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
