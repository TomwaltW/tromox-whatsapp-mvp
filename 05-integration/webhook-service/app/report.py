"""调优期周报：从线索库出一份周复盘报告（Markdown + JSON）。

    python -m app.report --out report.md [--json report.json] [--db PATH] [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--latency-threshold 60] [--post]

只读打开 SQLite（`mode=ro`），不经过服务、不改库。窗口 `[since, until)` 按 UTC 日期，`until` 不含当天，默认最近 7 天。
线索按 `leads.updated_at` 计，通知按 `notifications.created_at` 计。指标口径见 README 第 10 节。
号码只显示尾号 4 位：报告会贴到群里，完整号码一个都不出现。
`--post` 额外把六项指标的摘要发到 `NOTIFIERS` 配置的渠道（摘要只有汇总数，不含线索明细）。
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sqlite3
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

from tromox_lead import EscalationReason, Lead, LeadStatus, Segment, SourceChannel

from .notify import Notifier, NotifyError, build_notifiers

log = logging.getLogger(__name__)

# 与 06-acceptance/thresholds.json 的 notify_latency_max_seconds 一致（服务不在仓库根目录跑，故不在运行时读该文件）。
DEFAULT_LATENCY_THRESHOLD_S = 60
NOTIFICATION_STATUSES = ("sent", "partial", "failed", "pending", "skipped")
# 有效线索率的代理口径：结束分类数据攒够之前，把"已交接 / 已联系 / 已成交"的 B 端线索当作有效。
VALID_PROXY_STATUSES = frozenset({LeadStatus.HANDED_OFF, LeadStatus.CONTACTED, LeadStatus.CLOSED_WON})
# 第 6 节复盘清单：这两个原因最可能是 AI 误判，每周人工复看。
REVIEW_REASONS = frozenset({EscalationReason.LOW_CONFIDENCE, EscalationReason.NOT_UNDERSTOOD_TWICE})
TOP_SOURCE_CODES = 20
# 推送摘要：每类只列前 3，整段不超过 20 行（群消息里一屏能读完）。
TOP_SUMMARY_ITEMS = 3
SUMMARY_MAX_LINES = 20
_PHONE_RE = re.compile(r"(?<![\dA-Za-z])\+?\d{7,15}(?!\d)")

REASON_ZH: dict[str, str] = {
    "human_requested": "客户要求人工",
    "b2b_qualified": "B 端信息已收集完成",
    "low_confidence": "AI 把握不足",
    "complaint_warranty_legal_safety": "投诉 / 质保 / 法律 / 安全",
    "price_negotiation": "价格谈判",
    "not_understood_twice": "连续两次没听懂",
}
STATUS_ZH: dict[str, str] = {
    "new": "新线索", "qualified": "已合格", "handed_off": "已交接", "contacted": "已联系",
    "closed_won": "成交", "closed_lost": "未成交", "nurture": "培育中", "invalid": "无效",
}
NOTIFY_STATUS_ZH: dict[str, str] = {
    "sent": "全部渠道成功", "partial": "部分渠道成功", "failed": "全部失败", "pending": "已登记未发送", "skipped": "未配置渠道",
}


# ------------------------------------------------------------------ 窗口与打码
def parse_window(since: str | None, until: str | None, today: date | None = None) -> tuple[date, date]:
    today = today or datetime.now(timezone.utc).date()
    until_d = date.fromisoformat(until) if until else today
    since_d = date.fromisoformat(since) if since else until_d - timedelta(days=7)
    if since_d >= until_d:
        raise ValueError(f"--since ({since_d}) 必须早于 --until ({until_d})")
    return since_d, until_d


def mask_phone(phone: str | None) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return f"尾号 {digits[-4:]}" if len(digits) >= 4 else "无号码"


def scrub(text: str) -> str:
    """兜底：文本里任何像号码的数字串都打码，只留尾号 4 位。"""
    return _PHONE_RE.sub(lambda m: f"***{m.group(0)[-4:]}", text or "")


def _percentile(values: Sequence[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(pct * len(ordered)))
    return round(ordered[rank - 1], 3)


def _parse_ts(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


# ------------------------------------------------------------------ 读库
def open_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"线索库不存在：{path}")
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_leads(conn: sqlite3.Connection, since: date, until: date) -> list[Lead]:
    rows = conn.execute(
        "SELECT data_json FROM leads WHERE updated_at >= ? AND updated_at < ? ORDER BY updated_at, lead_id",
        (since.isoformat(), until.isoformat()),
    ).fetchall()
    return [Lead.model_validate_json(row["data_json"]) for row in rows]


def load_notifications(conn: sqlite3.Connection, since: date, until: date) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT status, created_at, sent_at FROM notifications WHERE created_at >= ? AND created_at < ? ORDER BY id",
        (since.isoformat(), until.isoformat()),
    ).fetchall()


# ------------------------------------------------------------------ 统计
def summarize(leads: list[Lead], notifications: Sequence[sqlite3.Row], since: date, until: date,
              threshold_s: int) -> dict[str, Any]:
    total = len(leads)
    b2b = sum(1 for lead in leads if lead.segment is Segment.B2B)
    b2c = sum(1 for lead in leads if lead.segment is Segment.B2C)
    unknown = total - b2b - b2c

    by_channel = {channel.value: 0 for channel in SourceChannel}
    for lead in leads:
        by_channel[lead.source_channel.value] += 1
    code_counter = Counter(lead.source_code for lead in leads if lead.source_code)
    by_code = dict(sorted(code_counter.items(), key=lambda item: (-item[1], item[0]))[:TOP_SOURCE_CODES])

    flagged_leads = [lead for lead in leads if lead.escalation_flag]
    by_reason = Counter(lead.escalation_reason.value if lead.escalation_reason else "unspecified" for lead in flagged_leads)

    status_counts = Counter(status.value for status in (lead.status for lead in leads))
    funnel = {status.value: status_counts.get(status.value, 0) for status in LeadStatus}

    notif_counts = Counter(row["status"] for row in notifications)
    latencies: list[float] = []
    for row in notifications:
        created, sent = _parse_ts(row["created_at"]), _parse_ts(row["sent_at"]) if row["sent_at"] else None
        if created and sent:
            latencies.append((sent - created).total_seconds())

    b2b_valid = sum(1 for lead in leads if lead.segment is Segment.B2B and lead.status in VALID_PROXY_STATUSES)
    return {
        "window": {"since": since.isoformat(), "until": until.isoformat()},
        "leads": {"total": total, "b2b": b2b, "b2c": b2c, "unknown": unknown,
                  "b2b_share": b2b / total if total else 0.0},
        "by_source_channel": by_channel,
        "by_source_code": by_code,
        "escalation": {"flagged": len(flagged_leads), "rate": len(flagged_leads) / total if total else 0.0,
                       "by_reason": dict(by_reason)},
        "notifications": {
            "rows": len(notifications),
            **{status: notif_counts.get(status, 0) for status in NOTIFICATION_STATUSES},
            "latency_p50_s": _percentile(latencies, 0.5),
            "latency_p95_s": _percentile(latencies, 0.95),
            "over_threshold": sum(1 for value in latencies if value > threshold_s),
            "threshold_s": threshold_s,
        },
        "status_funnel": funnel,
        "valid_lead_rate": b2b_valid / b2b if b2b else None,
    }


def review_candidates(leads: list[Lead]) -> list[dict[str, str]]:
    """第 6 节：误判候选。号码只给尾号，摘要里像号码的数字串也打码。"""
    return [
        {"lead_id": lead.lead_id, "reason": lead.escalation_reason.value, "phone": mask_phone(lead.phone),
         "ai_summary": scrub(lead.ai_summary) or "（无摘要）"}
        for lead in leads if lead.escalation_flag and lead.escalation_reason in REVIEW_REASONS
    ]


# ------------------------------------------------------------------ Markdown
def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def _sec(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f} s"


def render_markdown(data: dict[str, Any], candidates: list[dict[str, str]], db_path: Path) -> str:
    w, leads, esc, notif, funnel = data["window"], data["leads"], data["escalation"], data["notifications"], data["status_funnel"]
    lines = [
        f"# 调优期周报 {w['since']} 至 {w['until']}",
        "",
        f"- 窗口：`{w['since']}` 起、`{w['until']}` 止（不含当天），UTC 日期；线索按 `updated_at`、通知按 `created_at` 计。",
        f"- 生成时间：{datetime.now(timezone.utc).isoformat(timespec='seconds')}　线索库：`{db_path}`",
        "",
        "## 1. 线索",
        "",
        "| 指标 | 值 |", "|---|---|",
        f"| 线索总数 | {leads['total']} |",
        f"| B 端 | {leads['b2b']} |",
        f"| C 端 | {leads['b2c']} |",
        f"| 未判定 | {leads['unknown']} |",
        f"| B 端占比 | {_pct(leads['b2b_share'])} |",
        f"| 有效线索率（代理口径） | {_pct(data['valid_lead_rate'])} |",
        "",
        "有效线索率是代理指标：结束分类（`04-eval/labeling-guide.md` 的有效线索标准）攒够之前，"
        "先把状态为已交接 / 已联系 / 成交的 B 端线索算作有效，分母是窗口内的 B 端线索数；B 端为 0 时不算。",
        "",
        "## 2. 来源",
        "",
        "| 渠道 | 线索数 |", "|---|---|",
    ]
    lines += [f"| {channel} | {count} |" for channel, count in data["by_source_channel"].items()]
    lines += ["", f"短码（前 {TOP_SOURCE_CODES}）：", "", "| 短码 | 线索数 |", "|---|---|"]
    lines += [f"| {code} | {count} |" for code, count in data["by_source_code"].items()] or ["| （无短码） | 0 |"]
    unknown_share = data["by_source_channel"].get("unknown", 0) / leads["total"] if leads["total"] else None
    lines += [
        "",
        f"未知来源占比 {_pct(unknown_share)}；持续高于三成说明有入口没挂短码或客户删掉了预填文案（`01-design/source-tracking.md` 第 7 节）。",
        "",
        "## 3. 转人工",
        "",
        "| 指标 | 值 |", "|---|---|",
        f"| 转人工线索数 | {esc['flagged']} |",
        f"| 升级率 | {_pct(esc['rate'])} |",
        "",
        "| 原因 | 线索数 |", "|---|---|",
    ]
    lines += [f"| {reason}（{REASON_ZH.get(reason, reason)}） | {count} |" for reason, count in esc["by_reason"].items()] or ["| （无） | 0 |"]
    lines += [
        "",
        "升级率的验收上限见 `06-acceptance/thresholds.json` 的 `escalation_rate_max`；`b2b_qualified` 是设计上必须转人工的，"
        "看误判先看 `low_confidence` 与 `not_understood_twice`（第 6 节）。",
        "",
        "## 4. 通知",
        "",
        "| 状态 | 条数 |", "|---|---|",
        f"| 登记总数 | {notif['rows']} |",
    ]
    lines += [f"| {status}（{NOTIFY_STATUS_ZH[status]}） | {notif[status]} |" for status in NOTIFICATION_STATUSES]
    lines += [
        "",
        f"时延（`sent_at − created_at`，只算已送达的行）：p50 {_sec(notif['latency_p50_s'])}，p95 {_sec(notif['latency_p95_s'])}。",
        f"超过 {notif['threshold_s']} 秒的 {notif['over_threshold']} 条"
        + ("；阈值取 `06-acceptance/thresholds.json` 的 `notify_latency_max_seconds`（60 秒）"
           if notif["threshold_s"] == DEFAULT_LATENCY_THRESHOLD_S
           else f"（本次用 `--latency-threshold {notif['threshold_s']}`；验收阈值是 `06-acceptance/thresholds.json` 的 "
                f"`notify_latency_max_seconds` 60 秒）")
        + "，超阈值条数应为 0，否则先查通知渠道与重试日志。",
        "",
        "## 5. 状态漏斗",
        "",
        "| 状态 | 线索数 |", "|---|---|",
    ]
    lines += [f"| {status}（{STATUS_ZH[status]}） | {count} |" for status, count in funnel.items()]
    lines += [
        "",
        "`handed_off` 之后的状态靠销售回写，长期停在 `qualified` 说明回写没跟上，而不是没交接。",
        "",
        "## 6. 复盘清单",
        "",
        f"窗口内 `low_confidence` / `not_understood_twice` 的线索共 {len(candidates)} 条，是本周误判复盘的候选；号码只给尾号。",
        "",
    ]
    if candidates:
        lines += ["| lead_id | 原因 | 号码 | AI 摘要 |", "|---|---|---|---|"]
        lines += [f"| {c['lead_id']} | {c['reason']} | {c['phone']} | {c['ai_summary'].replace('|', '／')} |" for c in candidates]
    else:
        lines.append("（本窗口没有候选。）")
    lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------ 推送摘要
def _top_items(counts: dict[str, int], limit: int = TOP_SUMMARY_ITEMS) -> str:
    ranked = sorted(((name, count) for name, count in counts.items() if count), key=lambda item: (-item[1], item[0]))
    return "、".join(f"{name} {count}" for name, count in ranked[:limit]) or "无"


def summary_title(data: dict[str, Any]) -> str:
    return f"调优期周报 {data['window']['since']} 至 {data['window']['until']}"


def build_summary(data: dict[str, Any]) -> str:
    """六项指标的一段话摘要，发到销售群用。只有汇总数：没有 lead_id、没有摘要、号码一个都不出现。"""
    w, leads, esc, notif, funnel = (data["window"], data["leads"], data["escalation"],
                                    data["notifications"], data["status_funnel"])
    review_count = sum(esc["by_reason"].get(reason.value, 0) for reason in REVIEW_REASONS)
    p95 = "—" if notif["latency_p95_s"] is None else f"{notif['latency_p95_s']:.2f}"
    lines = [
        f"窗口 {w['since']} 至 {w['until']}（不含 until 当天，UTC）。",
        f"1. 线索 {leads['total']} 条（B 端占比 {_pct(leads['b2b_share'])}）：B 端 {leads['b2b']}、C 端 {leads['b2c']}、"
        f"未判定 {leads['unknown']}；有效线索率（代理口径）{_pct(data['valid_lead_rate'])}。",
        f"2. 来源前 3：{_top_items(data['by_source_channel'])}；短码前 3：{_top_items(data['by_source_code'])}。",
        f"3. 转人工率 {_pct(esc['rate'])}（{esc['flagged']} 条）；原因前 3："
        f"{_top_items({REASON_ZH.get(name, name): count for name, count in esc['by_reason'].items()})}。",
        f"4. 通知 {notif['rows']} 条：sent {notif['sent']} / partial {notif['partial']} / failed {notif['failed']}；"
        f"p95 {p95} 秒（阈值 {notif['threshold_s']} 秒），超阈值 {notif['over_threshold']} 条。",
        f"5. 状态漏斗前 3：{_top_items({STATUS_ZH.get(name, name): count for name, count in funnel.items()})}"
        f"（合计 {sum(funnel.values())} 条）。",
        f"6. 复盘清单 {review_count} 条（AI 把握不足 / 连续两次没听懂），逐条见 Markdown 报告第 6 节。",
    ]
    return scrub("\n".join(lines[:SUMMARY_MAX_LINES]))


def _configured_notifiers() -> list[Notifier]:
    """按 NOTIFIERS / .env 建渠道。单独一层是为了测试能替换掉它，不去读真实环境。"""
    from .config import get_settings  # 延后导入：只在 --post 时才读 .env

    return build_notifiers(get_settings())


def post_summary(data: dict[str, Any]) -> int:
    """把摘要发到每个已配置渠道；全部成功返回 0，任一失败返回 1（失败不打断其余渠道）。"""
    try:
        notifiers = _configured_notifiers()
    except ValueError as exc:
        log.error("周报推送：渠道配置有误 %s", exc)
        print(f"report: 渠道配置有误 {exc}", file=sys.stderr)
        return 1
    if not notifiers:
        print("posted=none")
        return 0

    title, text = summary_title(data), build_summary(data)
    posted: list[str] = []
    failed: list[str] = []
    for notifier in notifiers:
        try:
            notifier.send_text(title, text)
        except Exception as exc:  # noqa: BLE001 - 一个渠道挂掉不该拖累其余渠道
            # NotifyError 的文案按约定不含 URL；其它异常只留类型名，免得把带密钥的地址写进日志
            detail = str(exc) if isinstance(exc, NotifyError) else type(exc).__name__
            failed.append(notifier.name)
            log.error("周报推送失败 channel=%s error=%s", notifier.name, detail)
        else:
            posted.append(notifier.name)
            log.info("周报已推送 channel=%s", notifier.name)
    print("posted=" + (",".join(posted) or "none"))
    if failed:
        print(f"report: 推送失败的渠道 {','.join(failed)}（原因见 error 日志）", file=sys.stderr)
        return 1
    return 0


# ------------------------------------------------------------------ 入口
def build_report(db_path: Path, since: date, until: date, threshold_s: int) -> tuple[dict[str, Any], str]:
    conn = open_readonly(db_path)
    try:
        leads = load_leads(conn, since, until)
        notifications = load_notifications(conn, since, until)
    finally:
        conn.close()
    data = summarize(leads, notifications, since, until, threshold_s)
    return data, render_markdown(data, review_candidates(leads), db_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.report", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=None, help="SQLite 线索库路径；默认取 DATABASE_PATH / .env")
    parser.add_argument("--since", help="窗口起点（含），YYYY-MM-DD，UTC；默认 until 往前 7 天")
    parser.add_argument("--until", help="窗口终点（不含），YYYY-MM-DD，UTC；默认今天")
    parser.add_argument("--out", type=Path, default=None, help="Markdown 输出路径；只推送（--post）时可省")
    parser.add_argument("--json", type=Path, default=None, help="JSON 输出路径（可选）")
    parser.add_argument("--latency-threshold", type=int, default=DEFAULT_LATENCY_THRESHOLD_S,
                        help="通知时延阈值（秒），默认 60")
    parser.add_argument("--post", action="store_true",
                        help="把六项指标摘要发到 NOTIFIERS 配置的渠道；任一渠道失败退出码 1")
    args = parser.parse_args(argv)
    if args.out is None and not args.post:
        parser.error("需要 --out（只推送不落盘时可以只给 --post）")

    try:
        since, until = parse_window(args.since, args.until)
    except ValueError as exc:
        parser.error(str(exc))
    db_path = args.db
    if db_path is None:
        from .config import Settings  # 延后导入：只在没给 --db 时才读 .env

        db_path = Settings().database_path

    try:
        data, markdown = build_report(db_path, since, until, args.latency_threshold)
    except (FileNotFoundError, sqlite3.Error) as exc:
        print(f"report: {exc}", file=sys.stderr)
        return 2

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(markdown, encoding="utf-8")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report: {since} 至 {until}，线索 {data['leads']['total']} 条，通知 {data['notifications']['rows']} 条 "
          f"-> {args.out if args.out else '（未落盘，只推送）'}")
    return post_summary(data) if args.post else 0


if __name__ == "__main__":
    raise SystemExit(main())
