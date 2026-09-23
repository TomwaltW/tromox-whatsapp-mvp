"""Demo: replay the UAT cases offline into the cards the sales group would receive.

    python -m app.demo --out <dir> [--cases U01,U03] [--now 2026-11-10T12:00:00Z] [--timezone Asia/Shanghai]

No server, no network. Every case in fixtures/uat/manifest.json is replayed on its own throw-away
SQLite database through the real Pipeline (same parsing, normalisation, dedupe and card rendering
as production); the cards are collected instead of being posted anywhere. Written under --out:

    cards.md              every card as Markdown, grouped by case (send this to the client)
    cards.html            the same cards as one self-contained HTML page
    summary.md            one row per case: callbacks replayed, cards sent, reason, final status
    leads.csv             the lead records after each replay (LEAD_FIELDS columns, phones unmasked)
    payloads/<case>-<n>.feishu.json   the Feishu bot request body of each card

All fixture data is fictional. Cards, HTML and payloads only ever show the last 4 digits of a
phone number (the production default); leads.csv is the lead-library export and is not masked.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import logging
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from tromox_lead import LEAD_FIELDS, Lead

from .config import Settings, check_timezone
from .notify import FeishuNotifier, LeadCard
from .notify.card import REASON_ZH
from .pipeline import Pipeline
from .store import SqliteStore
from .store.csv_export import lead_to_row

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
UAT = FIXTURES / "uat"
DEMO_FEISHU_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/demo"  # placeholder: nothing is sent
PRIORITY_ZH = {"high": "高", "normal": "普通", "": "未定"}

log = logging.getLogger("app.demo")


class CollectingNotifier:
    """Notifier that keeps every card in memory instead of posting it."""

    name = "demo"

    def __init__(self) -> None:
        self.cards: list[LeadCard] = []

    def send(self, card: LeadCard) -> None:
        self.cards.append(card)


@dataclass
class CaseResult:
    case_id: str
    title: str
    callbacks: int
    cards: list[LeadCard] = field(default_factory=list)
    leads: list[Lead] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)
    delivery: list[str] = field(default_factory=list)

    @property
    def reasons(self) -> str:
        found = [REASON_ZH.get(lead.escalation_reason, lead.escalation_reason.value)
                 for lead in self.leads if lead.escalation_reason is not None]
        return "；".join(dict.fromkeys(found)) or "—"

    @property
    def final_status(self) -> str:
        statuses = [_enum_value(lead.status) for lead in self.leads]
        if not statuses:
            return "—"
        if len(statuses) == 1:
            return statuses[0]
        return " / ".join(statuses)


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def load_manifest() -> dict[str, dict[str, Any]]:
    return json.loads((UAT / "manifest.json").read_text(encoding="utf-8"))["cases"]


def parse_now(text: str | None) -> datetime:
    if not text:
        return datetime.now(timezone.utc)
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def replay_case(case_id: str, case: dict[str, Any], *, now: datetime, display_timezone: str) -> CaseResult:
    """Replay one case on a fresh temporary database and collect what the sales group would get."""
    result = CaseResult(case_id, str(case.get("title", "")), len(case["fixtures"]))
    with tempfile.TemporaryDirectory(prefix=f"demo-{case_id}-") as tmp:
        settings = Settings(_env_file=None, botmaker_webhook_token="demo", database_path=Path(tmp) / "leads.db",
                            csv_export_path=Path(tmp) / "leads.csv", display_timezone=display_timezone,
                            notify_mask_phone=True)
        store = SqliteStore(settings.database_path)
        collector = CollectingNotifier()
        pipeline = Pipeline(settings, store, sinks=[], notifiers=[collector], clock=lambda: now)
        for name in case["fixtures"]:
            payload = json.loads((UAT / name).read_text(encoding="utf-8"))
            handled = pipeline.handle(payload)
            result.outcomes.append(handled.outcome)
            if handled.notification_id is not None:
                result.delivery.append(pipeline.deliver(handled.notification_id))
        result.cards = list(collector.cards)
        result.leads = store.list_leads()
    return result


# ---------------------------------------------------------------------------- renderers
def render_cards_md(results: Sequence[CaseResult], *, now: datetime, display_timezone: str) -> str:
    total = sum(len(r.cards) for r in results)
    lines = [
        "# 演示卡片（UAT 回放）",
        "",
        "本文件由 `python -m app.demo` 把 `fixtures/uat/` 的 UAT 用例在回调服务上离线回放生成，"
        "公司、姓名、号码、对话内容全部虚构。号码已打码，卡片只显示尾号 4 位；"
        "销售在 Botmaker 内用公司号接手时才看到完整号码。",
        "",
        f"回放参数：now = {now.isoformat().replace('+00:00', 'Z')}，展示时区 {display_timezone}，"
        f"用例 {len(results)} 条，卡片 {total} 张。",
        "",
    ]
    for r in results:
        lines += [f"## {r.case_id} {r.title}".rstrip(), ""]
        if not r.cards:
            lines += ["（本用例不发卡：服务只入库，不通知销售。）", ""]
        for n, card in enumerate(r.cards, start=1):
            lines += [f"### {r.case_id} 第 {n} 张：{card.title}", "", card.to_markdown(), ""]
    return "\n".join(lines).rstrip() + "\n"


_HTML_CSS = """
:root { --bg: #f4f5f7; --card: #ffffff; --ink: #1f2329; --muted: #646a73; --line: #dee0e3;
        --blue: #3370ff; --red: #f54a45; --grey: #8f959e; }
* { box-sizing: border-box; }
body { margin: 0; padding: 24px 16px 48px; background: var(--bg); color: var(--ink);
       font: 15px/1.6 -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif; }
main { max-width: 720px; margin: 0 auto; }
h1 { font-size: 22px; margin: 0 0 8px; }
p.note { color: var(--muted); margin: 0 0 24px; }
section.case { margin: 32px 0 0; }
section.case > h2 { font-size: 16px; color: var(--muted); font-weight: 600; margin: 0 0 12px;
                    padding-bottom: 6px; border-bottom: 1px solid var(--line); }
p.nocard { color: var(--grey); font-size: 14px; margin: 0; }
article.card { background: var(--card); border: 1px solid var(--line); border-radius: 8px;
               margin: 0 0 16px; overflow: hidden; }
article.card > header { display: flex; align-items: center; gap: 12px; padding: 12px 16px; color: #fff;
                        background: var(--blue); }
article.card.prio-high > header { background: var(--red); }
article.card > header h3 { margin: 0; font-size: 16px; font-weight: 600; flex: 1; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 10px; background: rgba(255,255,255,.22);
         white-space: nowrap; }
.seq { font-size: 12px; color: var(--muted); padding: 8px 16px 0; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 6px 12px; margin: 0; padding: 12px 16px; }
dt { color: var(--muted); font-weight: 600; white-space: nowrap; }
dd { margin: 0; overflow-wrap: anywhere; }
p.summary { margin: 0; padding: 0 16px 12px; }
p.summary strong { color: var(--muted); }
a.btn { display: inline-block; margin: 0 16px 12px; padding: 8px 16px; border-radius: 6px;
        background: var(--blue); color: #fff; text-decoration: none; font-weight: 600; }
article.card.prio-high a.btn { background: var(--red); }
footer.foot { font-size: 12px; color: var(--muted); padding: 8px 16px 12px; border-top: 1px solid var(--line); }
@media (max-width: 480px) { dl { grid-template-columns: 1fr; gap: 2px; } dt { margin-top: 6px; } }
"""


def render_card_html(case_id: str, n: int, card: LeadCard) -> str:
    e = html.escape
    prio = card.priority if card.priority in PRIORITY_ZH else ""
    parts = [
        f'<article class="card prio-{prio or "none"}" data-case="{e(case_id)}" data-seq="{n}">',
        f"  <header><h3>{e(card.title)}</h3><span class=\"badge\">优先级：{PRIORITY_ZH[prio]}</span></header>",
        f'  <div class="seq">{e(case_id)} 第 {n} 张</div>',
        "  <dl>",
    ]
    parts += [f"    <dt>{e(label)}</dt><dd>{e(value)}</dd>" for label, value in card.fields]
    parts.append("  </dl>")
    if card.summary:
        parts.append(f'  <p class="summary"><strong>AI 摘要</strong>：{e(card.summary)}</p>')
    if card.link_url:
        parts.append(f'  <a class="btn" href="#">{e(card.link_text)}</a>')
    if card.footer:
        parts.append(f'  <footer class="foot">{e(card.footer)}</footer>')
    parts.append("</article>")
    return "\n".join(parts)


def render_cards_html(results: Sequence[CaseResult], *, now: datetime, display_timezone: str) -> str:
    e = html.escape
    total = sum(len(r.cards) for r in results)
    out = [
        "<!DOCTYPE html>", '<html lang="zh-CN">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>演示卡片（UAT 回放）</title>", f"<style>{_HTML_CSS}</style>", "</head>", "<body>", "<main>",
        "<h1>演示卡片（UAT 回放）</h1>",
        '<p class="note">销售群里收到的线索卡片长这样。数据全部虚构，号码只显示尾号；'
        "实际版式以飞书 / 企业微信渲染为准。"
        f"回放参数：now = {e(now.isoformat().replace('+00:00', 'Z'))}，展示时区 {e(display_timezone)}，"
        f"用例 {len(results)} 条，卡片 {total} 张。</p>",
    ]
    for r in results:
        out.append(f'<section class="case" id="{e(r.case_id)}">')
        out.append(f"<h2>{e(r.case_id)} {e(r.title)}</h2>")
        if not r.cards:
            out.append('<p class="nocard">本用例不发卡：服务只入库，不通知销售。</p>')
        for n, card in enumerate(r.cards, start=1):
            out.append(render_card_html(r.case_id, n, card))
        out.append("</section>")
    out += ["</main>", "</body>", "</html>"]
    return "\n".join(out) + "\n"


def render_summary_md(results: Sequence[CaseResult]) -> str:
    lines = ["# UAT 回放汇总", "", "| 用例 | 场景 | 回调数 | 卡片数 | 接管原因 | 最终状态 |",
             "| --- | --- | ---: | ---: | --- | --- |"]
    for r in results:
        cell = lambda s: str(s).replace("|", "\\|")  # noqa: E731
        lines.append(f"| {r.case_id} | {cell(r.title)} | {r.callbacks} | {len(r.cards)} | "
                     f"{cell(r.reasons)} | {cell(r.final_status)} |")
    total_cards = sum(len(r.cards) for r in results)
    total_cb = sum(r.callbacks for r in results)
    lines += ["", f"合计：用例 {len(results)} 条，回调 {total_cb} 条，卡片 {total_cards} 张。"]
    return "\n".join(lines) + "\n"


def write_outputs(out: Path, results: Sequence[CaseResult], *, now: datetime, display_timezone: str) -> int:
    out.mkdir(parents=True, exist_ok=True)
    (out / "cards.md").write_text(render_cards_md(results, now=now, display_timezone=display_timezone), encoding="utf-8")
    (out / "cards.html").write_text(render_cards_html(results, now=now, display_timezone=display_timezone),
                                    encoding="utf-8")
    (out / "summary.md").write_text(render_summary_md(results), encoding="utf-8")
    with (out / "leads.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(LEAD_FIELDS))
        writer.writeheader()
        for r in results:
            for lead in r.leads:
                writer.writerow(lead_to_row(lead))
    payloads = out / "payloads"
    payloads.mkdir(exist_ok=True)
    feishu = FeishuNotifier(DEMO_FEISHU_URL)
    count = 0
    for r in results:
        for n, card in enumerate(r.cards, start=1):
            body = feishu.build_body(card)
            (payloads / f"{r.case_id}-{n}.feishu.json").write_text(
                json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            count += 1
    return count


# ---------------------------------------------------------------------------- CLI
def select_cases(manifest: dict[str, dict[str, Any]], spec: str | None) -> list[str]:
    if not spec:
        return list(manifest)
    wanted = [item.strip().upper() for item in spec.split(",") if item.strip()]
    unknown = [c for c in wanted if c not in manifest]
    if unknown:
        raise KeyError(", ".join(unknown))
    return list(dict.fromkeys(wanted))


def _timezone_arg(value: str) -> str:
    """argparse `type=` for --timezone: the same check as DISPLAY_TIMEZONE; a typo is a usage error (exit 2)."""
    try:
        return check_timezone(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.demo", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, type=Path, help="output directory (created when missing)")
    parser.add_argument("--cases", help="comma-separated case ids, e.g. U01,U03 (default: all)")
    parser.add_argument("--now", help="ISO-8601 instant used as 'now' (default: current UTC time)")
    parser.add_argument("--timezone", default="Asia/Shanghai", type=_timezone_arg,
                        help="display timezone for the 24 h window (IANA name)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.ERROR, stream=sys.stderr)  # keep stdout for the summary line
    manifest = load_manifest()
    try:
        case_ids = select_cases(manifest, args.cases)
    except KeyError as exc:
        print(f"unknown case(s): {exc.args[0]}; available: {', '.join(manifest)}", file=sys.stderr)
        return 2
    now = parse_now(args.now)

    results: list[CaseResult] = []
    for case_id in case_ids:
        result = replay_case(case_id, manifest[case_id], now=now, display_timezone=args.timezone)
        results.append(result)
        print(f"{case_id} {result.title}: callbacks={result.callbacks} cards={len(result.cards)} "
              f"leads={len(result.leads)} outcomes={','.join(result.outcomes)}")
    cards = write_outputs(args.out, results, now=now, display_timezone=args.timezone)
    print(f"cases={len(results)} cards={cards} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
