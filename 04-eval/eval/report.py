"""Markdown report. Deterministic: no timestamps, stable ordering, paths as given on the CLI."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .data import Dataset
from .metrics import SEGMENTS, EvalResult, Outcome, ThresholdCheck, ratio
from .prompt import PromptSpec

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_DIGITS_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")
_EXCERPT_LEN = 110


@dataclass(frozen=True)
class RunInfo:
    model: str
    input_path: str
    thresholds_path: str
    cost_per_100_usd: float | None
    prices: tuple[float, float] | None


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def excerpt(text: str) -> str:
    """One-line, PII-masked snippet that is safe inside a Markdown table."""
    masked = _DIGITS_RE.sub("<number>", _EMAIL_RE.sub("<email>", text))
    flat = " ".join(masked.split()).replace("|", "/")
    return flat if len(flat) <= _EXCERPT_LEN else flat[: _EXCERPT_LEN - 1] + "…"


def _threshold_value(check: ThresholdCheck) -> tuple[str, str]:
    if check.key.endswith("_samples"):
        value = "n/a" if check.value is None else f"{check.value:.0f}"
        return value, f"{check.comparator} {check.threshold:.0f}"
    return pct(check.value), f"{check.comparator} {check.threshold * 100:.0f}%"


def _outcome_rows(outcomes: list[Outcome]) -> list[str]:
    rows = ["| 样本 | 语种 | 标注 | 预测 | 置信度 | 已转人工 | 文本摘录 |", "|---|---|---|---|---|---|---|"]
    for o in outcomes:
        gold = o.sample.segment.value + (f" / {o.sample.b2b_type.value}" if o.sample.b2b_type else "")
        pred = o.prediction.segment.value if o.parse.ok else "解析失败（按 unknown 处理）"
        rows.append(
            f"| {o.sample.sample_id} | {o.sample.language} | {gold} | {pred} | {o.prediction.ai_confidence:.2f} | "
            f"{'是' if o.prediction.escalation_flag else '否'} | {excerpt(o.sample.conversation_text)} |"
        )
    return rows


def render_report(dataset: Dataset, prompt: PromptSpec, result: EvalResult,
                  checks: list[ThresholdCheck], info: RunInfo) -> str:
    failed = [c for c in checks if not c.passed]
    origins = "、".join(f"{k} {v}" for k, v in sorted(dataset.origins.items()))
    out: list[str] = [
        "# 离线评测报告",
        "",
        "> 用途：记录一次离线评测的指标、与验收阈值的对照、以及需要人工复盘的样本清单。读者：集成工程师、张宝文。",
        "> 本报告由 `python -m eval.run` 生成，请勿手改；口径见 `04-eval/README.md` 与 `06-acceptance/acceptance-criteria.md`。",
        "",
        "## 1. 运行信息",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 数据文件 | `{info.input_path}`（sha256 前 12 位 `{dataset.sha256[:12]}`） |",
        f"| 样本数 | {result.n_total}（{origins}）；跳过模板示例行 {dataset.skipped_examples} 行 |",
        f"| 模型 | `{info.model}` |",
        f"| Prompt 版本 | `{prompt.version}`（sha256 前 12 位 `{prompt.sha256[:12]}`） |",
        f"| 阈值文件 | `{info.thresholds_path}` |",
        "",
    ]
    verdict = "通过" if not failed else f"未通过（{len(failed)} / {len(checks)} 项不达标：" + "、".join(c.label for c in failed) + "）"
    out += [f"**结论：{verdict}**", ""]
    if dataset.origins.get("synthetic"):
        out += ["> 注意：本次数据含合成样本。合成数据只用于跑通流程，不能作为验收依据；上线前必须换成标注后的真实咨询。", ""]
    if info.model == "mock":
        out += ["> 注意：模型为 mock（对标注答案做确定性扰动），下列数字只说明工具可用，不代表任何真实模型的水平。", ""]

    out += ["## 2. 验收阈值对照", "", "| 指标 | 实测 | 阈值 | 结论 | 备注 |", "|---|---|---|---|---|"]
    for check in checks:
        value, limit = _threshold_value(check)
        out.append(f"| {check.label} | {value} | {limit} | {'达标' if check.passed else '不达标'} | {check.note} |")
    out.append("")

    out += ["## 3. B 端漏判清单（先看这里）", "",
            f"标注为 B2B 却没有被判为 B2B 的样本：{len(result.b2b_misses)} / {result.n_gold_b2b}。"
            "漏掉一个经销商的代价远高于误判一个个人，这张表每一行都要人工复盘；"
            "\"已转人工\"为\"是\"的行，销售仍然会看到这位客户。", ""]
    out += _outcome_rows(result.b2b_misses) if result.b2b_misses else ["无。"]
    out.append("")

    out += ["## 4. 客户类型混淆矩阵", "", "| 标注 \\ 预测 | " + " | ".join(s.value for s in SEGMENTS) + " | 合计 |",
            "|---|" + "---|" * (len(SEGMENTS) + 1)]
    for gold in SEGMENTS:
        counts = [result.confusion[(gold.value, pred.value)] for pred in SEGMENTS]
        out.append(f"| {gold.value} | " + " | ".join(str(c) for c in counts) + f" | {sum(counts)} |")
    out += ["",
            f"B 端：召回率 {pct(result.b2b_recall)}，精确率 {pct(result.b2b_precision)}，F1 {pct(result.b2b_f1)}"
            f"（TP {result.b2b_tp} / FP {result.b2b_fp} / FN {result.b2b_fn}）。", ""]

    out += ["## 5. B 端误报清单", "", f"标注不是 B2B 却被判为 B2B 的样本：{len(result.b2b_false_positives)}。", ""]
    out += _outcome_rows(result.b2b_false_positives) if result.b2b_false_positives else ["无。"]
    out.append("")

    out += ["## 6. 分语种分布", "", "| 语种 | 样本数 | B 端样本数 | B 端召回率 | 类型准确率 | 升级率 |", "|---|---|---|---|---|---|"]
    for row in result.per_language:
        out.append(f"| {row.language} | {row.n} | {row.n_b2b} | {pct(row.b2b_recall)} | "
                   f"{pct(row.segment_accuracy)} | {pct(row.escalation_rate)} |")
    out.append("")

    micro_p = ratio(result.product_tp, result.product_tp + result.product_fp)
    micro_r = ratio(result.product_tp, result.product_tp + result.product_fn)
    out += [
        "## 7. 其他指标", "",
        "| 指标 | 实测 | 口径 |", "|---|---|---|",
        f"| 国家准确率 | {pct(result.country_accuracy)}（{result.country_correct} / {result.country_eligible}） | 有号码的样本；判定国家 = 客户自述国家，没有则取号码国家码；与 `country_gold` 比较 |",
        f"| 产品识别率 | {pct(result.product_recognition)}（{result.product_exact} / {result.product_eligible}） | 标注了产品的样本，代码集合完全一致 |",
        f"| 产品代码级精确率 / 召回率 | {pct(micro_p)} / {pct(micro_r)} | 全部样本逐个代码统计，供参考 |",
        f"| 升级率（预测） | {pct(result.escalation_rate)}（{result.escalation_pred} / {result.n_total}） | 经路由规则后需要人工接管的比例 |",
        f"| 升级率（标注） | {pct(ratio(result.escalation_gold, result.n_total))}（{result.escalation_gold} / {result.n_total}） | 标注员认为应当转人工的比例 |",
        f"| 应升级样本的召回率 | {pct(result.escalation_recall)} | 标注应转人工的样本中被转人工的比例 |",
        f"| 升级精确率 | {pct(result.escalation_precision)} | 被转人工的样本中标注确应转人工的比例 |",
        f"| 升级原因一致率 | {pct(ratio(result.escalation_reason_match, result.escalation_tp))} | 双方都判升级的样本中原因相同的比例 |",
        f"| B 端类型准确率 | {pct(ratio(result.b2b_type_correct, result.b2b_type_eligible))} | 标注与预测都是 B2B 的样本 |",
        f"| C 端意图准确率 | {pct(ratio(result.b2c_intent_correct, result.b2c_intent_eligible))} | 标注与预测都是 B2C 的样本 |",
        f"| 语言识别准确率 | {pct(ratio(result.language_correct, result.n_total))} | 全部样本 |",
        "",
    ]
    if result.escalation_by_reason:
        out += ["升级原因分布（预测）：", "", "| 原因 | 样本数 |", "|---|---|"]
        out += [f"| `{reason}` | {count} |" for reason, count in sorted(result.escalation_by_reason.items())]
        out.append("")
    if result.country_errors:
        out += ["国家判错的样本：", "", "| 样本 | 号码国家 | 模型抽取的自述国家 | 判定 | 标注 |", "|---|---|---|---|---|"]
        for o in result.country_errors:
            out.append(f"| {o.sample.sample_id} | {o.sample.country_by_phone or '-'} | {o.prediction.country_stated or '-'} | "
                       f"{o.predicted_country or '-'} | {o.sample.country_gold} |")
        out.append("")

    usage = result.usage
    n = max(result.n_total, 1)
    if info.cost_per_100_usd is None:
        cost_line = "未设置单价（环境变量 `EVAL_PRICE_INPUT_PER_1M`、`EVAL_PRICE_OUTPUT_PER_1M`），不计算。"
    else:
        assert info.prices is not None
        cost_line = (f"{info.cost_per_100_usd:.4f} USD（单价：输入 {info.prices[0]:g}、输出 {info.prices[1]:g} USD / 百万 token；"
                     "缓存写入按输入价 1.25 倍、缓存读取按 0.1 倍计）。")
    out += [
        "## 8. 成本与时延", "",
        "| 项 | 值 |", "|---|---|",
        f"| 输入 token（未命中缓存） | {usage.input_tokens:,}（平均 {usage.input_tokens / n:,.0f} / 条） |",
        f"| 缓存写入 / 缓存读取 token | {usage.cache_write_tokens:,} / {usage.cache_read_tokens:,} |",
        f"| 输出 token | {usage.output_tokens:,}（平均 {usage.output_tokens / n:,.0f} / 条） |",
        f"| 每 100 条成本 | {cost_line} |",
        f"| 时延 p50 / p95 | {_seconds(result.latency_p50)} / {_seconds(result.latency_p95)} |",
        f"| 被兜底模型回答的样本 | {result.served_by_fallback} |",
        f"| 被模型拒答的样本 | {result.refusals} |",
        "",
    ]

    out += ["## 9. 解析失败与调用失败", "",
            f"JSON 解析成功率 {pct(result.parse_success)}（{result.parse_ok} / ({result.n_total} - {result.client_failures})，"
            "即解析成功 / (样本数 - 调用失败)）；"
            f"调用失败 {result.client_failures} 条（没有模型输出，不计入解析成功率的分母）；"
            f"输出缺键但仍可用 {result.missing_key_outputs} 条。"
            "解析或调用失败的样本按生产兜底处理：`segment=unknown` 且转人工，照常计入召回率与升级率。", ""]
    if result.parse_failures:
        out += ["| 样本 | 原因 |", "|---|---|"]
        for o in result.parse_failures:
            reason = o.client_error or (o.completion.error if o.completion and o.completion.error else None) or o.parse.error or "-"
            out.append(f"| {o.sample.sample_id} | {excerpt(reason)} |")
        out.append("")

    out += [
        "## 10. 口径说明", "",
        "1. 每条预测先经过 `tromox_lead.apply_routing_rules`（与集成服务同一函数），再统计：置信度低于 0.6 的会被规则追加为转人工，B 端类型、联系人或公司、市场三项齐备的会被追加为 `b2b_qualified`。",
        "2. 模型看不到号码，也看不到号码国家；国家由号码国家码按规则判定，模型只负责抽取客户自述的国家。",
        "3. 发送给模型的内容 = prompt 文件去掉 HTML 注释后的全文 + 单条咨询文本（来源短码已剥离）。",
        "4. 验收只认真实数据（`data_origin=real`）；阈值取自验收阈值文件，数值待张宝文确认。",
        "5. 离线评测与生产必须使用同一模型、同一版 prompt：换模型或改 prompt 后要重跑并保留本报告。",
        "",
    ]
    return "\n".join(out)


def _seconds(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f} s"
