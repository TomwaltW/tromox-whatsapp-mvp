# ADR 0003：AI 路线 A / B 与决策门

> 用途：记录"字段抽取由谁来做"的决策：默认用 Botmaker 内置 AI Agent（路线 A），不稳定时改为外部固定 JSON 调用（路线 B），以及两者之间的量化决策门。读者：集成工程师、张宝文。
> 状态：已采纳决策方法（2026-09-21）；走哪条路线在开工第 1 周的决策门（`07-project/timeline.md`）后记录到本文件末尾。

## 背景

- MVP 的难点是分类与筛选，不是链路。线索字段必须稳定、结构化地落到变量里，后面的标签、入库、通知才成立。
- Botmaker 的 AI Agent 能按指令把用户信息写进变量（官方示例写法为 "store it in ${fullName}"），但稳定性与是否支持结构化 JSON 输出没有公开说明（SOURCES S-B9）。
- 单 Agent，不做多 Agent：B 端或 C 端由按钮决定，AI 只负责理解自由文本、答 FAQ、追问并抽取字段。

## 决策

1. **路线 A（默认）**：Botmaker 内置 AI Agent 加知识库，抽取结果写入与线索字段同名的会话变量。
2. **路线 B（兜底）**：把"分类 + 抽字段"单拎出来，做成一次固定输出 JSON 的外部调用，由 Code Action 触发；prompt 在仓库里（`04-eval/prompts/classify-v1.md`）。对话与 FAQ 仍由内置 AI Agent 承担。架构见 `01-design/architecture.md` 第 3 节。
3. **决策门**：在 Botmaker 试用账号里跑 20 条样例（`02-botmaker/trial-test-plan.md`），字段写入成功率不低于 95% 走 A，否则走 B。阈值的机器可读版本在 `06-acceptance/thresholds.json`（`route_a_trial_samples`、`route_a_variable_write_success_min`）【张宝文确认】。
4. **"写入成功"的定义**：一条样例里，应写的必填变量全部写入、取值落在枚举范围内、没有写进不该写的变量，才算成功；20 条里至多允许 1 条失败。
5. **同一模型、同一版 prompt**：无论哪条路线，离线评测与生产必须一致。
   - 路线 B：天然一致。集成服务与评测工具读同一个 prompt 文件，用同一个解析器与同一个规则层（`shared/tromox_lead/routing.py`）。
   - 路线 A：离线评测用与 Botmaker 所选模型相同的模型（选型见 `0006-model-selection.md`），抽取规则与 JSON 块由 `scripts/gen_schema_artifacts.py` 从同一份源头注入两个 prompt，逐字相同。平台会在我们的指令之外再包一层自己的上下文，离线结果只能近似生产；所以决策门在平台内实测，上线后每周抽查真实对话作为补充。
6. **prompt 版本管理**：改 prompt 即新建 `classify-v2.md`，附一份评测报告；生产切换版本要在仓库里留记录。

## 备选方案

| 方案 | 结论 |
|---|---|
| 一开始就走路线 B | 不采用为默认。多一段自写代码与一个外部依赖；内置能力够用时没有必要 |
| 全部对话都交给外部模型，Botmaker 只当通道 | 不采用。等于自建 Agent，与"平台优先不自建"和张宝文对客户的口径相悖 |
| 多 Agent（分类 Agent、B 端 Agent、C 端 Agent） | 不采用。按钮已经完成了分流，多 Agent 只增加 token 消耗与调试面 |
| 不设决策门，凭感觉选 | 不采用。"验收可量化"原则要求决策有数字依据 |

## 影响

- 路线 A：零自写推理代码；token 费由 Botmaker 计（SOURCES S-B7）；抽取行为受平台黑盒影响，靠每周抽查兜住。
- 路线 B：集成服务要新增一个分类端点，Code Action 要写一段调用代码；外部模型费很小（`03-whatsapp/cost-model.md` 第 5 节第 4 条）；多一个需要客户主体开通的模型账号。
- 两条路线下，线索字段、标签、通知、验收指标完全相同，切换路线不影响其他文件。
- Code Action 单次执行上限 90 秒（SOURCES S-B10），外部调用必须设更短的超时并有失败兜底：调用失败时不阻塞对话，按 `low_confidence` 转人工。

## 待决事项

| 事项 | 标记 |
|---|---|
| AI Agent 写变量的稳定性、是否支持 JSON 输出 | 【待核实】SOURCES S-B9，由决策门回答 |
| Code Action 调用频率上限 | 【待核实】SOURCES S-B10 |
| 决策门阈值 95% 与样例数 20 | 【张宝文确认】 |

## 决策记录

| 日期 | 试用结果（成功条数 / 20） | 结论 | 记录人 |
|---|---|---|---|
| 待填（计划 2026-10-16） | | | |
