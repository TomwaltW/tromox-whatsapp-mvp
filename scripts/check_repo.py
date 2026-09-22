#!/usr/bin/env python3
"""Static consistency checks for the whole package (task Section 7, items 1-6, 8, 9).

Each check prints PASS / FAIL with details; exit code 1 if any check fails.
Pure standard library; does not use the shell `grep` (which may be aliased).

    python scripts/check_repo.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# .worktrees / review / .claude: local multi-track orchestration (worktree copies, dispatch notes, hooks); dist: export output.
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "data",
             ".worktrees", "review", ".claude", "dist"}
TEXT_SUFFIXES = {".md", ".py", ".csv", ".json", ".txt", ".toml", ".yml", ".yaml", ".example", ".sh", ""}

REQUIRED_FILES = [
    "README.md", "SOURCES.md",
    "00-client/方案书.md", "00-client/报价单.md", "00-client/客户需提供清单.md", "00-client/运维手册.md",
    "00-client/销售接手SOP.md", "00-client/培训计划.md", "00-client/维护服务说明.md",
    "01-design/architecture.md", "01-design/conversation-flow.md", "01-design/routing-rules.md",
    "01-design/lead-schema.md", "01-design/tag-taxonomy.md", "01-design/source-tracking.md",
    "01-design/adr/0001-platform-choice.md", "01-design/adr/0002-number-strategy.md",
    "01-design/adr/0003-ai-route-a-b.md", "01-design/adr/0004-lead-storage.md",
    "01-design/adr/0005-notification-channel.md", "01-design/adr/0006-model-selection.md",
    "02-botmaker/setup-guide.md", "02-botmaker/ai-agent-system-prompt.md",
    "02-botmaker/knowledge-base-template.md", "02-botmaker/trial-test-plan.md", "02-botmaker/templates/README.md",
    "03-whatsapp/meta-onboarding-checklist.md", "03-whatsapp/cost-model.md", "03-whatsapp/cost_model.py",
    "03-whatsapp/cost-model.xlsx", "03-whatsapp/compliance.md",
    "04-eval/labeling-guide.md", "04-eval/labeling-template.csv", "04-eval/synthetic-samples.csv",
    "04-eval/prompts/classify-v1.md", "04-eval/eval/run.py", "04-eval/README.md",
    "04-eval/reports/synthetic-mock-report.md",
    "05-integration/webhook-service/app/main.py", "05-integration/webhook-service/.env.example",
    "05-integration/webhook-service/Dockerfile", "05-integration/botmaker-api-notes.md", "05-integration/deployment.md",
    "06-acceptance/acceptance-criteria.md", "06-acceptance/uat-test-cases.md", "06-acceptance/go-live-checklist.md",
    "07-project/timeline.md", "07-project/raci.md", "07-project/risk-register.md",
    "07-project/meeting-prep.md", "07-project/phase-2-outline.md",
    "99-internal/work-breakdown.md", "99-internal/pricing-internal.md",
    "99-internal/open-questions.md", "99-internal/zhang-baowen-brief.md",
]

# A-class documents must never contain these (internal prices, effort, banned wording, internal references).
CLIENT_FORBIDDEN = [
    (r"人天", "effort unit"), (r"号商", "banned word"), (r"99-internal", "internal reference"),
    (r"底线", "internal pricing"), (r"分成", "internal pricing"), (r"利润", "internal pricing"),
    (r"1\.8\s*万|1\.3\s*万|1\.2\s*万|1\.5\s*[–\-~至到]\s*3\s*万", "internal or unconfirmed price"),
    (r"18[,，]?000|13[,，]?000|12[,，]?000", "internal price"),
    (r"2[,，]?500\s*元|1[,，]?200\s*元|2[,，]?500\s*CNY|1[,，]?200\s*CNY", "internal maintenance price"),
    (r"更正|纠正", "correcting-someone wording"),
    (r"SOURCES\.md|\badr/|路线\s*[AB]\b|work-breakdown|pricing-internal|open-questions", "reference to non-client files"),
    (r"Baileys|whatsapp-web\.js|wppconnect|venom-bot", "non-official library name"),
    (r"0[0-9]-[a-z-]+/|shared/|scripts/|\.(?:md|py|json|csv)\b", "repo path or file name (refer to client docs by title only)"),
    (r"只持有管理权限|保留我方.{0,30}管理权限", "outdated admin-access wording"),
]
# Any CNY service amount in client docs must be a marker, not a number.
CLIENT_CNY_AMOUNT = re.compile(r"(?<![\d.,])(\d{1,3}(?:[,，]\d{3})+|\d{4,6})\s*(?:元|CNY|人民币)|\d+(?:\.\d+)?\s*万(?:元|\s*CNY|人民币)?")

# Library names / number buying: only inside a "不采用" statement in the two files below.
# The word 号商 is not allowed anywhere (the agreed wording is "不采用第三方购号").
BANNED_REPO = re.compile(r"Baileys|whatsapp-web\.js|wppconnect|venom-bot|买号|号商", re.IGNORECASE)
BANNED_NEVER = re.compile(r"号商")
BANNED_ALLOWED_FILES = {"07-project/risk-register.md", "03-whatsapp/meta-onboarding-checklist.md"}
BANNED_ALLOW_LINE = re.compile(r"不采用|不使用|不买号|禁止|绝不")

URL_RE = re.compile(r"https?://[^\s)>\]\"'`，。；、）]+")
URL_ALLOW_PREFIXES = (
    "http://localhost", "http://127.0.0.1", "https://example.", "http://example.", "https://your-", "https://hooks.example",
    "https://open.feishu.cn/open-apis/bot/v2/hook", "https://qyapi.weixin.qq.com/cgi-bin/webhook/send",
    "https://api.anthropic.com", "https://api.openai.com", "https://wa.me/", "https://json-schema.org/",
    "https://go.botmaker.com/", "https://api.botmaker.com/v2.0", "https://docs.astral.sh/uv", "https://github.com/astral-sh/uv",
)

failures: list[str] = []


def report(name: str, problems: list[str]) -> None:
    if problems:
        failures.append(name)
        print(f"FAIL  {name}")
        for p in problems[:40]:
            print(f"        {p}")
        if len(problems) > 40:
            print(f"        ... and {len(problems) - 40} more")
    else:
        print(f"PASS  {name}")


def iter_files(suffixes: set[str] | None = None):
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or set(path.relative_to(ROOT).parts) & SKIP_DIRS:
            continue
        if suffixes is None or path.suffix in suffixes:
            yield path


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_required_files() -> None:
    report("7.0 prescribed files exist", [f"missing: {f}" for f in REQUIRED_FILES if not (ROOT / f).exists()])


def check_client_docs() -> None:
    problems: list[str] = []
    for path in sorted((ROOT / "00-client").glob("*.md")):
        for number, line in enumerate(read(path).splitlines(), start=1):
            for pattern, why in CLIENT_FORBIDDEN:
                if re.search(pattern, line):
                    problems.append(f"{rel(path)}:{number} [{why}] {line.strip()[:90]}")
            for match in CLIENT_CNY_AMOUNT.finditer(line):
                # third-party cost estimates in CNY are allowed when the line says 估算 / 第三方
                if not re.search(r"估算|第三方|汇率", line):
                    problems.append(f"{rel(path)}:{number} [CNY amount without marker] {match.group(0)} :: {line.strip()[:70]}")
    report("7.4 client docs free of internal prices / effort / banned wording / internal references", problems)


def check_banned_terms() -> None:
    problems: list[str] = []
    for path in iter_files(TEXT_SUFFIXES):
        name = rel(path)
        for number, line in enumerate(read(path).splitlines(), start=1):
            if name == "scripts/check_repo.py" or not BANNED_REPO.search(line):
                continue
            if (name in BANNED_ALLOWED_FILES and BANNED_ALLOW_LINE.search(line)
                    and not BANNED_NEVER.search(line)):
                continue
            problems.append(f"{name}:{number} {line.strip()[:100]}")
    report("7.5 no non-official libraries / number buying outside the two '不采用' statements", problems)


def check_tier_table() -> None:
    snippet = read(ROOT / "shared/snippets/tier-scope-table.md").strip()
    problems = [f"{f} does not contain shared/snippets/tier-scope-table.md verbatim"
                for f in ("00-client/报价单.md", "99-internal/work-breakdown.md")
                if not (ROOT / f).exists() or snippet not in read(ROOT / f)]
    report("7.1a tier scope table identical in 报价单 and work-breakdown", problems)


def check_cost_numbers() -> None:
    summary = json.loads(read(ROOT / "03-whatsapp/cost-model-summary.json"))
    quote = read(ROOT / "00-client/报价单.md") if (ROOT / "00-client/报价单.md").exists() else ""
    problems: list[str] = []
    for scenario, data in summary["scenarios"].items():
        for key in ("total_route_a_usd", "total_route_a_cny"):
            value = f"{data[key]:,}"
            if value not in quote and str(data[key]) not in quote:
                problems.append(f"报价单 lacks {scenario}.{key} = {value}")
        for key in ("meta_messaging_usd", "botmaker_plan_usd", "botmaker_ai_usd", "hosting_usd"):
            if data[key] and f"{data[key]:,}" not in quote:
                problems.append(f"报价单 lacks {scenario}.{key} = {data[key]:,}")
    if f"{summary['botmaker_setup_usd_one_time']:.0f}" not in quote:
        problems.append("报价单 lacks the one-time 99 USD setup fee")
    report("7.1b third-party cost numbers in 报价单 match cost-model-summary.json", problems)


def check_thresholds() -> None:
    t = json.loads(read(ROOT / "06-acceptance/thresholds.json"))
    expect = [str(t["offline_min_samples"]), f"{t['b2b_recall_min']:.0%}", f"{t['b2b_precision_min']:.0%}",
              f"{t['country_accuracy_min']:.0%}", f"{t['product_recognition_min']:.0%}",
              f"{t['escalation_rate_max']:.0%}", str(t["e2e_scenarios"]), str(t["notify_latency_max_seconds"])]
    problems: list[str] = []
    for f in ("06-acceptance/acceptance-criteria.md", "00-client/方案书.md"):
        text = read(ROOT / f) if (ROOT / f).exists() else ""
        problems += [f"{f} lacks threshold value {v}" for v in expect if v not in text]
    report("7.1c acceptance thresholds consistent (thresholds.json, acceptance-criteria, 方案书)", problems)


def check_kim_questions() -> None:
    path = ROOT / "00-client/方案书.md"
    text = read(path) if path.exists() else ""
    needles = {
        "Q1 价格包含项": r"首月|上线后监护|包含",
        "Q2a 账号谁准备": r"公司名下|自己名下|贵司名下",
        "Q2b 在用号码能否用": r"Coexistence|共存",
        "Q2c 是否买号": r"第三方购号|不需要.*购买|无需.*购买|不向第三方",
        "Q2d 批量加联系人风控": r"风控|质量评级|封号",
        "Q3 总包还是周期": r"总包",
        "Q4 是否需要长期技术人员": r"运营.{0,20}(维护|即可|就能)|长期技术",
        "Q5 工程师报价": r"档位|配置",
    }
    report("7.2 方案书 answers Kim's five questions (keyword presence; read it too)",
           [f"no match for {k}" for k, pattern in needles.items() if not re.search(pattern, text)])


def check_zhang_items() -> None:
    path = ROOT / "00-client/方案书.md"
    text = read(path) if path.exists() else ""
    items = ["需求梳理", "方案设计", "Agent 配置", "Botmaker 与 WhatsApp 接入", "基础分类和标签", "测试上线", "培训", "上线初期调整"]
    report("7.3 方案书 lists Zhang Baowen's eight included items",
           [f"missing item: {i}" for i in items if i not in text])


def check_purpose_line() -> None:
    problems = []
    for path in iter_files({".md"}):
        name = rel(path)
        if name.startswith(("04-eval/reports/", "shared/prompt_blocks/", "shared/snippets/",
                            "scripts/open_questions_preamble.md")):
            continue
        head = "\n".join(read(path).splitlines()[:6])
        if "用途" not in head:
            problems.append(f"{name}: no '用途' line near the top")
    report("6. every document states purpose and reader at the top", problems)


def check_urls() -> None:
    sources = set(URL_RE.findall(read(ROOT / "SOURCES.md")))
    allowed = {u.rstrip(".,;") for u in sources}
    problems = []
    for path in iter_files({".md"}):
        name = rel(path)
        if name == "SOURCES.md":
            continue
        for number, line in enumerate(read(path).splitlines(), start=1):
            for url in URL_RE.findall(line):
                url = url.rstrip(".,;")
                if re.search(r"[<{]|%7B", url):  # placeholder such as https://<your-domain>/... or {whatsapp_number}
                    continue
                if url in allowed or url.startswith(URL_ALLOW_PREFIXES) or any(url.startswith(a) for a in allowed):
                    continue
                problems.append(f"{name}:{number} {url}")
    report("6. only URLs confirmed in SOURCES.md (plus local / API endpoints) are used", problems)


def check_timeline() -> None:
    text = read(ROOT / "07-project/timeline.md")
    problems = [f"timeline lacks {needle}" for needle in ("2026-10-01", "crit", "商家认证", "中秋", "国庆") if needle not in text]
    report("7.9 timeline shows the Meta review critical path, the 10/1 billing node, the holidays", problems)


def check_no_emoji() -> None:
    emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⬆✅❌]")
    problems = []
    for path in iter_files({".md", ".csv"}):
        for number, line in enumerate(read(path).splitlines(), start=1):
            if emoji.search(line):
                problems.append(f"{rel(path)}:{number} {line.strip()[:80]}")
    report("6. no emoji in documents or bot wording", problems)


def main() -> int:
    for check in (check_required_files, check_client_docs, check_banned_terms, check_tier_table,
                  check_cost_numbers, check_thresholds, check_kim_questions, check_zhang_items,
                  check_purpose_line, check_urls, check_timeline, check_no_emoji):
        check()
    print(f"\n{len(failures)} check(s) failed" if failures else "\nall static checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
