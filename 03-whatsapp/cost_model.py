#!/usr/bin/env python3
"""Third-party monthly cost model for the Tromox WhatsApp MVP.

Inputs : cost-model-inputs.csv (low / mid / high scenarios), cost-model-rates.csv (markets)
Outputs: cost-model-results.md (tables), cost-model-summary.json (numbers other docs quote),
         cost-model.xlsx (static export; edit the CSVs and re-run instead of editing the xlsx)

Billing regime is parametrised (free allowance, BSP markup, CTWA share), so the 2026-10-01
rules are inputs rather than constants. Usage:

    python 03-whatsapp/cost_model.py            # regenerate outputs
    python 03-whatsapp/cost_model.py --check    # exit 1 if outputs are stale
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
SCENARIOS = ("low", "mid", "high")
SCENARIO_ZH = {"low": "低", "mid": "中", "high": "高"}
WEU_VERIFIED = ("DE", "NL", "GB")

BOTMAKER_PLANS = (  # SOURCES S-B3
    ("Standard", 149.0, 3000),
    ("Scale", 249.0, 5000),
    ("Pro", 499.0, 10000),
)
BOTMAKER_OVERAGE_USD = 0.025  # per additional conversation/user beyond the plan, SOURCES S-B3
BOTMAKER_SETUP_USD = 99.0     # one-time WhatsApp Business Platform account setup, SOURCES S-B3


@dataclass(frozen=True)
class Params:
    daily_inquiries: float
    b2b_share: float
    ai_msgs_per_conv_b2b: float
    ai_msgs_per_conv_b2c: float
    human_msgs_per_conv_b2b: float
    human_handoff_share_b2c: float
    human_msgs_per_conv_b2c: float
    ctwa_share: float
    template_followup_share_b2b: float
    templates_per_followup: float
    free_service_msgs_per_month: float
    bsp_markup_service: float
    bsp_markup_template: float
    ai_tokens_per_ai_msg: float
    botmaker_ai_usd_per_1m_tokens: float
    route_b_calls_per_conv: float
    route_b_input_tokens: float
    route_b_output_tokens: float
    ext_model_usd_per_1m_input: float
    ext_model_usd_per_1m_output: float
    hosting_usd_per_month: float
    usd_to_cny: float


@dataclass(frozen=True)
class Market:
    code: str
    label_zh: str
    share: float
    rate_usd: float
    status: str
    is_proxy: bool


@dataclass(frozen=True)
class Breakdown:
    conversations: float
    service_msgs_total: float
    service_msgs_free_entry: float
    service_msgs_free_allowance: float
    service_msgs_billable: float
    blended_rate_usd: float
    meta_service_usd: float
    meta_template_usd: float
    botmaker_plan_name: str
    botmaker_plan_usd: float
    botmaker_ai_usd: float
    route_b_model_usd: float
    hosting_usd: float

    @property
    def total_route_a_usd(self) -> float:
        return (self.meta_service_usd + self.meta_template_usd + self.botmaker_plan_usd
                + self.botmaker_ai_usd + self.hosting_usd)

    @property
    def total_route_b_usd(self) -> float:
        return self.total_route_a_usd + self.route_b_model_usd


def load_params(path: Path) -> dict[str, Params]:
    columns: dict[str, dict[str, float]] = {s: {} for s in SCENARIOS}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for scenario in SCENARIOS:
                columns[scenario][row["param"]] = float(row[scenario])
    return {s: Params(**values) for s, values in columns.items()}


def load_markets(path: Path) -> list[Market]:
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    verified = {r["market"]: float(r["rate_usd"]) for r in rows if r["rate_usd"].strip()}
    proxies = {
        "WEU": round(mean(verified[m] for m in WEU_VERIFIED), 4),
        "ALL": round(mean(verified.values()), 4),
    }
    markets: list[Market] = []
    for r in rows:
        share = float(r["share"])
        if share <= 0:
            continue
        has_rate = bool(r["rate_usd"].strip())
        rate = float(r["rate_usd"]) if has_rate else proxies[r["proxy_group"]]
        markets.append(Market(r["market"], r["label_zh"], share, rate, r["rate_status"], not has_rate))
    total_share = sum(m.share for m in markets)
    if abs(total_share - 1.0) > 1e-6:
        raise SystemExit(f"market shares must sum to 1.0, got {total_share}")
    return markets


def pick_botmaker_plan(conversations: float) -> tuple[str, float]:
    best: tuple[str, float] | None = None
    for name, price, included in BOTMAKER_PLANS:
        cost = price + max(0.0, conversations - included) * BOTMAKER_OVERAGE_USD
        if best is None or cost < best[1]:
            best = (name, cost)
    assert best is not None
    return best


def compute(p: Params, markets: list[Market]) -> Breakdown:
    conversations = p.daily_inquiries * 30
    b2b = conversations * p.b2b_share
    b2c = conversations - b2b
    ai_msgs = b2b * p.ai_msgs_per_conv_b2b + b2c * p.ai_msgs_per_conv_b2c
    human_msgs = b2b * p.human_msgs_per_conv_b2b + b2c * p.human_handoff_share_b2c * p.human_msgs_per_conv_b2c
    service_total = ai_msgs + human_msgs
    free_entry = service_total * p.ctwa_share
    chargeable = service_total - free_entry
    free_allowance = min(chargeable, p.free_service_msgs_per_month)
    billable = chargeable - free_allowance
    blended = sum(m.share * m.rate_usd for m in markets)
    meta_service = billable * blended * (1 + p.bsp_markup_service)
    templates = b2b * p.template_followup_share_b2b * p.templates_per_followup
    meta_template = templates * blended * (1 + p.bsp_markup_template)
    plan_name, plan_usd = pick_botmaker_plan(conversations)
    botmaker_ai = ai_msgs * p.ai_tokens_per_ai_msg / 1_000_000 * p.botmaker_ai_usd_per_1m_tokens
    route_b = conversations * p.route_b_calls_per_conv * (
        p.route_b_input_tokens / 1_000_000 * p.ext_model_usd_per_1m_input
        + p.route_b_output_tokens / 1_000_000 * p.ext_model_usd_per_1m_output
    )
    return Breakdown(conversations, service_total, free_entry, free_allowance, billable, blended,
                     meta_service, meta_template, plan_name, plan_usd, botmaker_ai, route_b,
                     p.hosting_usd_per_month)


def sensitivity(p: Params, markets: list[Market]) -> list[tuple[str, float, float]]:
    """(label, route A total USD, delta vs base) for the mid scenario."""
    base = compute(p, markets).total_route_a_usd
    cases = [
        ("基准（中档）", p),
        ("每对话 AI 消息 +2 条", replace(p, ai_msgs_per_conv_b2b=p.ai_msgs_per_conv_b2b + 2, ai_msgs_per_conv_b2c=p.ai_msgs_per_conv_b2c + 2)),
        ("每对话 AI 消息 -2 条", replace(p, ai_msgs_per_conv_b2b=max(1, p.ai_msgs_per_conv_b2b - 2), ai_msgs_per_conv_b2c=max(1, p.ai_msgs_per_conv_b2c - 2))),
        ("免费额度为 0 条（保守）", replace(p, free_service_msgs_per_month=0)),
        ("CTWA 入口占比 0%", replace(p, ctwa_share=0.0)),
        ("CTWA 入口占比 50%", replace(p, ctwa_share=0.5)),
        ("销售改用 App 回复（Coexistence，人工消息不计费）", replace(p, human_msgs_per_conv_b2b=0, human_msgs_per_conv_b2c=0)),
        ("Botmaker AI 单价取高档", replace(p, botmaker_ai_usd_per_1m_tokens=5.0)),
    ]
    return [(label, compute(params, markets).total_route_a_usd, compute(params, markets).total_route_a_usd - base)
            for label, params in cases]


def usd(value: float) -> str:
    return f"{value:,.0f}" if value >= 100 else f"{value:,.1f}"


def round_to(value: float, step: int) -> int:
    return int(round(value / step) * step)


def build_summary(results: dict[str, Breakdown], params: dict[str, Params]) -> dict:
    fx = params["mid"].usd_to_cny
    summary: dict = {"usd_to_cny": fx, "botmaker_setup_usd_one_time": BOTMAKER_SETUP_USD, "scenarios": {}}
    for s in SCENARIOS:
        b = results[s]
        messaging = b.meta_service_usd + b.meta_template_usd
        summary["scenarios"][s] = {
            "daily_inquiries": params[s].daily_inquiries,
            "conversations_per_month": b.conversations,
            "botmaker_plan": b.botmaker_plan_name,
            "botmaker_plan_usd": round_to(b.botmaker_plan_usd, 1),
            "meta_messaging_usd": round_to(messaging, 10),
            "botmaker_ai_usd": round_to(b.botmaker_ai_usd, 10),
            "route_b_model_usd": round_to(b.route_b_model_usd, 1),
            "hosting_usd": round_to(b.hosting_usd, 1),
            "total_route_a_usd": round_to(b.total_route_a_usd, 10),
            "total_route_a_cny": round_to(b.total_route_a_usd * fx, 100),
            "total_route_b_usd": round_to(b.total_route_b_usd, 10),
            "total_route_b_cny": round_to(b.total_route_b_usd * fx, 100),
        }
    return summary


def render_markdown(params: dict[str, Params], markets: list[Market], results: dict[str, Breakdown],
                    sens: list[tuple[str, float, float]], summary: dict) -> str:
    fx = params["mid"].usd_to_cny
    out: list[str] = [
        "# 第三方费用测算结果（自动生成）",
        "",
        "> 用途：`cost_model.py` 的输出；公式说明见 `cost-model.md`。读者：集成工程师、张宝文。",
        "> 本文件由脚本生成，请勿手改：改 `cost-model-inputs.csv` / `cost-model-rates.csv` 后重跑 `python 03-whatsapp/cost_model.py`。",
        "> 所有输入均为假设或待确认值，状态见两份 CSV 的 status 列；标【待核实】【待客户确认】的项确认后必须重跑。",
        "",
        "## 1. 市场与费率",
        "",
        "| 市场 | 对话占比 | 费率 USD/条 | 状态 |",
        "|---|---|---|---|",
    ]
    for m in markets:
        note = "（代理值）" if m.is_proxy else ""
        out.append(f"| {m.label_zh} | {m.share:.0%} | {m.rate_usd:.4f}{note} | {m.status} |")
    out += [
        "",
        f"加权平均费率：{results['mid'].blended_rate_usd:.4f} USD/条（Meta 基础价，未含 BSP 加价）。"
        "代理值 = 已复核市场的算术平均（西欧组：德、荷、英；全部组：所有已复核市场），仅用于量级估算。【待核实】",
        "",
        "## 2. 月度费用（USD）",
        "",
        "| 项目 | 低 | 中 | 高 |",
        "|---|---|---|---|",
    ]

    def row(label: str, getter) -> str:
        return f"| {label} | " + " | ".join(getter(results[s], params[s]) for s in SCENARIOS) + " |"

    out += [
        row("日均咨询（个）", lambda b, p: f"{p.daily_inquiries:,.0f}"),
        row("月对话数", lambda b, p: f"{b.conversations:,.0f}"),
        row("窗口内发出消息总数（AI + 人工）", lambda b, p: f"{b.service_msgs_total:,.0f}"),
        row("其中：免费入口（CTWA 72 小时）", lambda b, p: f"{b.service_msgs_free_entry:,.0f}"),
        row("其中：月度免费额度抵扣", lambda b, p: f"{b.service_msgs_free_allowance:,.0f}"),
        row("其中：计费条数", lambda b, p: f"{b.service_msgs_billable:,.0f}"),
        row("Meta 客服消息费（含 BSP 加价）", lambda b, p: usd(b.meta_service_usd)),
        row("Meta 模板消息费（再触达，含加价）", lambda b, p: usd(b.meta_template_usd)),
        row("Botmaker 套餐（含超量）", lambda b, p: f"{b.botmaker_plan_name} {usd(b.botmaker_plan_usd)}"),
        row("Botmaker AI token 费（路线 A、B 都有）", lambda b, p: usd(b.botmaker_ai_usd)),
        row("集成服务托管", lambda b, p: usd(b.hosting_usd)),
        row("**合计：路线 A**", lambda b, p: f"**{usd(b.total_route_a_usd)}**"),
        row("外部模型费（仅路线 B 增量）", lambda b, p: usd(b.route_b_model_usd)),
        row("**合计：路线 B**", lambda b, p: f"**{usd(b.total_route_b_usd)}**"),
        "",
        f"一次性费用：Botmaker 开通 WhatsApp 商业平台账户 {BOTMAKER_SETUP_USD:.0f} USD（SOURCES S-B3）。",
        "",
        f"## 3. 月度费用（CNY，汇率 {fx:.2f}，假设）",
        "",
        "| 项目 | 低 | 中 | 高 |",
        "|---|---|---|---|",
        row("合计：路线 A", lambda b, p: f"{b.total_route_a_usd * fx:,.0f}"),
        row("合计：路线 B", lambda b, p: f"{b.total_route_b_usd * fx:,.0f}"),
        "",
        "## 4. 敏感性分析（中档，路线 A）",
        "",
        "| 情景 | 月合计 USD | 与基准差额 USD |",
        "|---|---|---|",
    ]
    for label, total, delta in sens:
        out.append(f"| {label} | {usd(total)} | {delta:+,.0f} |")
    out += [
        "",
        "## 5. 供其他文档引用的取整数字",
        "",
        "客户文档（报价单、方案书）只引用下表的取整值；一致性由 `scripts/check_repo.py` 校验。",
        "",
        "| 档位 | 日均咨询 | 路线 A 月合计 USD | 路线 A 月合计 CNY | 其中消息费 USD | 其中 Botmaker 套餐 USD | 其中 AI token 费 USD |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in SCENARIOS:
        d = summary["scenarios"][s]
        out.append(
            f"| {SCENARIO_ZH[s]} | {d['daily_inquiries']:,.0f} | {d['total_route_a_usd']:,} | {d['total_route_a_cny']:,} | "
            f"{d['meta_messaging_usd']:,} | {d['botmaker_plan_usd']:,} | {d['botmaker_ai_usd']:,} |"
        )
    out.append("")
    return "\n".join(out)


def write_xlsx(path: Path, params_csv: Path, rates_csv: Path, results: dict[str, Breakdown],
               sens: list[tuple[str, float, float]], fx: float) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "说明"
    ws.append(["本文件由 03-whatsapp/cost_model.py 生成，为静态数值导出。"])
    ws.append(["请修改 cost-model-inputs.csv / cost-model-rates.csv 后重跑脚本，不要直接改本表。"])
    for title, source in (("输入参数", params_csv), ("国家费率", rates_csv)):
        sheet = wb.create_sheet(title)
        with source.open(encoding="utf-8") as fh:
            for line in csv.reader(fh):
                sheet.append(line)
    sheet = wb.create_sheet("结果")
    sheet.append(["项目", "低", "中", "高"])
    fields = [
        ("月对话数", "conversations"), ("窗口内消息总数", "service_msgs_total"),
        ("免费入口条数", "service_msgs_free_entry"), ("免费额度抵扣", "service_msgs_free_allowance"),
        ("计费条数", "service_msgs_billable"), ("Meta 客服消息费 USD", "meta_service_usd"),
        ("Meta 模板消息费 USD", "meta_template_usd"), ("Botmaker 套餐 USD", "botmaker_plan_usd"),
        ("Botmaker AI token 费 USD", "botmaker_ai_usd"), ("托管 USD", "hosting_usd"),
        ("外部模型费 USD（路线 B）", "route_b_model_usd"),
    ]
    for label, attr in fields:
        sheet.append([label, *[round(getattr(results[s], attr), 2) for s in SCENARIOS]])
    sheet.append(["合计 路线 A USD", *[round(results[s].total_route_a_usd, 2) for s in SCENARIOS]])
    sheet.append(["合计 路线 B USD", *[round(results[s].total_route_b_usd, 2) for s in SCENARIOS]])
    sheet.append([f"合计 路线 A CNY（汇率 {fx}）", *[round(results[s].total_route_a_usd * fx, 0) for s in SCENARIOS]])
    sheet = wb.create_sheet("敏感性")
    sheet.append(["情景", "月合计 USD", "与基准差额 USD"])
    for label, total, delta in sens:
        sheet.append([label, round(total, 2), round(delta, 2)])
    wb.save(path)


def run(inputs: Path, rates: Path) -> tuple[str, dict, dict[str, Breakdown], list, dict[str, Params]]:
    params = load_params(inputs)
    markets = load_markets(rates)
    results = {s: compute(params[s], markets) for s in SCENARIOS}
    sens = sensitivity(params["mid"], markets)
    summary = build_summary(results, params)
    return render_markdown(params, markets, results, sens, summary), summary, results, sens, params


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--inputs", type=Path, default=HERE / "cost-model-inputs.csv")
    parser.add_argument("--rates", type=Path, default=HERE / "cost-model-rates.csv")
    parser.add_argument("--out-dir", type=Path, default=HERE)
    parser.add_argument("--check", action="store_true", help="exit 1 if generated files are stale")
    parser.add_argument("--no-xlsx", action="store_true")
    args = parser.parse_args()

    markdown, summary, results, sens, params = run(args.inputs, args.rates)
    summary_text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    md_path = args.out_dir / "cost-model-results.md"
    json_path = args.out_dir / "cost-model-summary.json"
    if args.check:
        stale = [p.name for p, text in ((md_path, markdown), (json_path, summary_text))
                 if not p.exists() or p.read_text(encoding="utf-8") != text]
        for name in stale:
            print(f"STALE: {name}")
        return 1 if stale else 0
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(summary_text, encoding="utf-8")
    if not args.no_xlsx:
        write_xlsx(args.out_dir / "cost-model.xlsx", args.inputs, args.rates, results, sens, params["mid"].usd_to_cny)
    print(f"wrote {md_path.name}, {json_path.name}" + ("" if args.no_xlsx else ", cost-model.xlsx"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
