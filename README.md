# 摩兽（Tromox）海外社媒 → WhatsApp AI 接待与线索分类 MVP 方案包

> 用途：仓库索引、三类读者的阅读顺序、评测工具与集成服务的运行方法。读者：客户对接人、张宝文、集成工程师。
> 状态：2026-09-21 初稿；2026-09-22 按平台事实二次核实更新（见 `SOURCES.md` 表头）。所有代码以 mock / fixture 跑通；没有创建任何账号，没有调用任何真实 API。

## 1. 这是什么

把海外社媒带来的咨询统一接到 WhatsApp，由限定用途的 AI 做基础接待，识别国家、B 端或 C 端、产品需求；C 端分类沉淀，B 端线索转销售在公司号上接手。第一阶段用 Botmaker（Meta 官方 BSP）加一个轻量线索库，不建复杂 CRM，不自建 Agent。

设计原则：官方接入；限定用途的 AI；平台优先不自建；能用按钮就不让 AI 猜；验收可量化；所有账号与数据资产在客户名下；prompt 与知识库保存在仓库里，不被锁死在平台。

## 2. 三层产出物，物理分开

| 层 | 目录 | 给谁 | 规则 |
|---|---|---|---|
| A | `00-client/` | 客户（Kim 与客户领导） | 非技术语言；不含内部价格与工作量；不引用 B、C 类文件 |
| B | `01-design/` 至 `07-project/`、`shared/`、`scripts/`、`tests/`、`SOURCES.md` | 集成工程师 | 技术设计、配置指南、代码、验收 |
| C | `99-internal/` | 沈思锴、张宝文 | 工作量、内部报价、待决问题；绝不进 A 类 |

三类标记：【待核实】平台、政策、价格等未经核实的事实；【待客户确认】需摩兽提供或拍板；【张宝文确认】需张宝文定的商务数字与承诺。汇总见 `99-internal/open-questions.md`。

## 3. 阅读顺序

**客户**：`00-client/方案书.md` → `00-client/客户需提供清单.md` → `00-client/报价单.md` → `00-client/维护服务说明.md`；上线前读 `00-client/运维手册.md`、`00-client/销售接手SOP.md`、`00-client/培训计划.md`。

**张宝文**：`99-internal/zhang-baowen-brief.md` → `99-internal/zhang-baowen-changelog-2026-09-22.md`（手上是 9/21 版时先看这份）→ `00-client/方案书.md`（改一改转 Kim）→ `07-project/meeting-prep.md`（中秋碰面）→ `99-internal/pricing-internal.md` → `99-internal/open-questions.md` → `06-acceptance/acceptance-criteria.md`。

**集成工程师**：`SOURCES.md` → `01-design/architecture.md` → `01-design/adr/` → `01-design/lead-schema.md` → `01-design/conversation-flow.md`、`routing-rules.md` → `02-botmaker/trial-test-plan.md`（开工第一件事）→ `02-botmaker/setup-guide.md` → `04-eval/README.md` → `05-integration/webhook-service/README.md` → `06-acceptance/`。

## 4. 目录

| 路径 | 内容 |
|---|---|
| `SOURCES.md` | 平台、政策、价格事实的核实结论与出处，唯一源头 |
| `00-client/` | 方案书、报价单、客户需提供清单、运维手册、销售接手 SOP、培训计划、维护服务说明 |
| `01-design/` | 架构、会话流程、路由规则、线索数据结构、标签体系、来源追踪、六条 ADR |
| `02-botmaker/` | 配置指南、AI Agent system prompt、知识库模板、试用账号测试计划、再触达模板、需要 Botmaker 书面答复的问题清单（含英文邮件稿） |
| `03-whatsapp/` | Meta 接入清单、成本模型（CSV + 脚本 + 结果 + xlsx）、合规要点 |
| `04-eval/` | 离线评测工具：标注指南、标注模板、合成样本、分类 prompt、评测包、历史咨询导入器（`eval.import_history`）、双人标注一致性（`eval.agreement`）、测试 |
| `05-integration/` | FastAPI 回调服务（含调优期周报 `app.report`（可 `--post` 推送到通知渠道）、演示卡片 `app.demo`、删除请求命令 `app.forget`、数据保留任务 `app.retention`、原始回调样本导出 `app.samples`、`/metrics` 指标端点、飞书多维表格 sink、CSV 镜像写后合并、并发压测 `tools/loadtest.py`）、Botmaker API 笔记、部署说明与部署套件（`deploy/`：加固后的 compose、Caddyfile、上线演练脚本 `rehearsal.sh`）、飞书多维表格设置说明 |
| `06-acceptance/` | 验收标准（含机器可读阈值）、UAT 用例、上线检查表 |
| `07-project/` | 时间计划、RACI、风险登记、碰面准备、第二阶段展望 |
| `99-internal/` | 工作量、内部报价、待决问题、给张宝文的一页说明与 9/22 变更说明 |
| `shared/tromox_lead/` | 线索数据结构与规则的唯一代码源头：pydantic 模型、枚举、国家 / 语言 / 短码 / 路由 / 标签规则 |
| `shared/prompt_blocks/`、`shared/snippets/` | 两个 prompt 共用的抽取规则；报价单与工作量表共用的两档范围表 |
| `scripts/` | 生成器与机器检查；客户文档导出；UAT 执行记录表生成器（`gen_uat_sheet.py`）；试用样例包生成器（`gen_trial_kit.py`） |
| `tests/` | 根目录测试：数据结构一致性、成本模型、文档导出、UAT 记录表、试用样例包 |

## 5. 单一源头

| 什么 | 源头 | 谁引用 | 怎么保证一致 |
|---|---|---|---|
| 字段名、枚举、抽取 JSON 块 | `shared/tromox_lead/` | lead-schema、两个 prompt、标注模板、回调服务、评测工具 | `scripts/gen_schema_artifacts.py` 生成；`tests/test_shared_schema.py` 校验 |
| 抽取规则文本 | `shared/prompt_blocks/extraction-rules.md` | system prompt、classify prompt | 同上，逐字注入 |
| 第三方费用数字 | `03-whatsapp/cost-model-*.csv` + `cost_model.py` | 报价单、给张宝文的说明 | `scripts/check_repo.py` 校验 |
| 验收阈值 | `06-acceptance/thresholds.json` | 验收标准、方案书、评测报告 | 同上 |
| 两档范围表 | `shared/snippets/tier-scope-table.md` | 报价单、工作量表 | 同上，逐字比对 |
| 日期 | `07-project/timeline.md` | 方案书、碰面准备等 | 人工引用 |
| 人天 | `99-internal/work-breakdown.md` | 内部报价 | 仅内部 |

## 6. 从零跑通

本机用 `python3` / `uv`；下面命令在仓库根目录执行。

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e ".[eval,service,cost,dev]"

# 生成物（数据结构派生文件、成本模型结果、待决问题汇总）
.venv/bin/python scripts/gen_schema_artifacts.py
.venv/bin/python 03-whatsapp/cost_model.py
.venv/bin/python scripts/collect_open_questions.py

# 离线评测：mock 客户端在合成集上出报告
cd 04-eval
../.venv/bin/python -m eval.run --input synthetic-samples.csv --prompt prompts/classify-v1.md --model mock --out reports/synthetic-mock-report.md
cd ..

# 集成服务：本地起服务（细节见 05-integration/webhook-service/README.md）
cd 05-integration/webhook-service
cp .env.example .env    # 填 BOTMAKER_WEBHOOK_TOKEN
../../.venv/bin/python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
cd ../..

# 全部自动检查（测试 + 一致性）；加 --with-mermaid 会逐个渲染 Mermaid 图，较慢
bash scripts/check_all.sh
# 开发时用 --fast：跳过 Chrome / npx / 子进程的慢测试（TROMOX_FAST_TESTS=1），20 秒内出结果；提交前仍跑全量

# 客户文档导出：00-client/*.md → dist/<名>.docx（可编辑 Word）+ dist/<名>.pdf；dist/ 不入库
# 需要 Node（npx，渲染流程图）与本机 Chrome（打印 PDF）；check_all.sh 加 --with-exports 会顺带全量导出
# Mermaid 渲染的 npm 缓存在 scratch/npm-cache/（已 gitignore，每个 checkout 各一份，多个 worktree 并行不互相干扰；TROMOX_NPM_CACHE 可指到别处）
uv pip install --python .venv/bin/python -e ".[export]"
.venv/bin/python scripts/export_client_docs.py                          # 全部文档，docx + pdf
.venv/bin/python scripts/export_client_docs.py --docs 方案书 报价单 --formats docx
.venv/bin/python scripts/export_client_docs.py --package zhang              # 发给张宝文的包：dist/zhang-<日期>/ 内 6 份 docx+pdf，再打成 dist/zhang-<日期>.zip
```

换成真实模型评测：设置 `OPENAI_BASE_URL`、`OPENAI_API_KEY` 后用 `--model openai:<模型名>`，或设置 `ANTHROPIC_API_KEY` 后用 `--model anthropic:<模型名>`。离线评测与生产必须使用同一模型、同一版 prompt。

## 7. 自动检查清单

| 命令 | 检查什么 |
|---|---|
| `scripts/gen_schema_artifacts.py --check` | 数据结构派生文件是否过期 |
| `03-whatsapp/cost_model.py --check` | 成本模型结果是否过期 |
| `scripts/collect_open_questions.py --check` | 待决问题汇总是否过期 |
| `scripts/check_repo.py` | 文件齐全；客户文档无内部价格、工作量、内部引用；无非官方库与购号建议；两档范围表、费用数字、验收阈值一致；方案书回答五个问题、列全八个包含项；URL 白名单；时间计划含关键路径 |
| `pytest`（根目录、`04-eval`、`05-integration/webhook-service`） | 代码测试；`check_all.sh --fast`（即 `TROMOX_FAST_TESTS=1`）跳过带 `slow` 标记的用例（真 Chrome、真 npx、uvicorn 子进程），其余照跑 |
| `scripts/check_mermaid.py` | 所有 Mermaid 图可渲染（需要 Node 与本机 Chrome） |
| `scripts/export_client_docs.py` | 客户文档能导出成 Word 与 PDF（流程图渲染成图片、表格带边框、中文字体已设）；任一文档失败即非 0 退出（需要 Node 与本机 Chrome，`check_all.sh --with-exports` 时运行） |

## 8. 不做的事

不使用非官方的 WhatsApp 接入方式；不采用第三方购号；不上 Kubernetes 与微服务；不做复杂 CRM；AI 不做什么都能聊的通用助手。
