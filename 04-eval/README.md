# 离线评测工具（04-eval）

> 用途：在不碰线上、不花消息费的前提下，量化"AI 能不能把杂乱咨询变成可销售的结构化线索"；产出验收用的指标报告，并为路线 A / B 决策和模型选型提供依据。读者：集成工程师。
> 假设：Python 3.11；依赖装在仓库根目录的 `.venv`；字段、枚举、路由规则全部来自共享包 `shared/tromox_lead`，本工具不重复定义。

## 1. 它回答什么问题

| 问题 | 看报告哪一节 |
|---|---|
| 会不会漏掉经销商（主指标：B 端召回率） | 第 2、3 节 |
| 会不会把个人误送给销售（B 端精确率） | 第 2、5 节 |
| 国家、产品识别准不准，转人工比例是否可接受 | 第 2、7 节 |
| 模型输出能不能稳定解析成固定 JSON | 第 2、9 节 |
| 哪个语种拖后腿 | 第 6 节 |
| 每 100 条咨询的模型成本 | 第 8 节 |

阈值取自 `../06-acceptance/thresholds.json`，口径见 `../06-acceptance/acceptance-criteria.md`。验收只认真实数据；`synthetic-samples.csv` 是手写的合成咨询，只用于跑通流程，上线前必须换成标注后的真实咨询。

## 2. 目录

| 路径 | 内容 |
|---|---|
| `labeling-guide.md` | 标注指南、"有效线索标准"模板（给销售填） |
| `labeling-template.csv` | 标注模板（生成物，列名与 lead schema 对齐，勿手改表头） |
| `synthetic-samples.csv` | 80 条多语言合成咨询（由 `tools/make_synthetic.py` 生成） |
| `prompts/classify-v1.md` | 单次"分类 + 抽字段"prompt，固定 JSON 输出；抽取规则与 JSON 块和 Botmaker system prompt 逐字相同 |
| `eval/` | 评测代码：`data` 加载校验、`prompt`、`clients/`（mock、OpenAI 兼容、Anthropic）、`parse`、`metrics`、`report`、`run`、`import_history`（导入器）、`agreement`（双人标注一致性） |
| `tests/` | pytest；真实客户端只通过 mock transport 测试，不访问网络 |
| `reports/` | 评测报告；`synthetic-mock-report.md` 是 mock 在合成集上的样例 |
| `data/` | 放真实标注数据与原始输出；整个目录已被 git 忽略 |

## 3. 从零跑通

```bash
cd tromox-whatsapp-mvp
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[eval,dev]"     # eval 依赖组已含官方 anthropic SDK（仅评测 Claude 模型时用到）

cd 04-eval
python -m eval.run --input synthetic-samples.csv --prompt prompts/classify-v1.md --model mock --out reports/synthetic-mock-report.md
python -m pytest -q
```

没有激活虚拟环境时，把 `python` 换成 `../.venv/bin/python`。

mock 客户端对标注答案做确定性扰动（按 `sample_id` 播种），两次运行的报告逐字节相同；它的数字只说明工具可用，不代表任何真实模型。`--mock-error-rate 0` 可得到全对的基线，`--mock-seed` 可换扰动。

命令行最后一行是 `RESULT: PASS` 或 `RESULT: FAIL（列出不达标项）`。退出码默认恒为 0；加 `--fail-under` 后，任一阈值不达标返回 1（数据错误返回 2，客户端配置错误返回 3）。

`data_origin=example` 的行默认被跳过（标注模板的示例行）；要评测试用样例包（`scripts/gen_trial_kit.py` 的默认产物，整份都是 `example`）时加 `--include-examples`，否则会因没有可用行返回 2。报告第 2 节的"真实样本数"仍只统计 `data_origin=real`。

## 4. 换成真实标注数据

### 4.0 从客户导出到标注模板

客户交来的历史咨询多半是 WhatsApp / Instagram 后台导出的 CSV 或 Excel，列名五花八门，正文里夹着号码和邮箱。先用导入器把它变成表头正确、正文已脱敏的标注文件，再交给标注人：

```bash
cd 04-eval
python -m eval.import_history --input data/export-2026-08.xlsx --out data/labeling-batch-1.csv
python -m eval.import_history --input data/export.csv --out data/labeling-batch-1.csv --text-col 客户消息 --phone-col 手机
```

- 列自动识别（大小写不敏感、按"包含"匹配）：正文 `message / text / content / 内容 / 消息 / 咨询 / conversation / 正文`；号码 `phone / number / mobile / 号码 / 电话 / whatsapp`，外加整词 `wa`（`WA Number`、`wa_id`；不会命中 `Awaiting reply`）；日期 `date / time / 时间 / 日期`；渠道 `channel / source / platform / 来源 / 渠道 / 平台`。按正文、号码、日期、渠道的顺序认领，已认领的列不再参与。同一角色有几列命中时不再取最左边那列：
  - 正文列跳过同时命中日期提示或编号提示（整词 `id`、`编号`、`序号`、`number`）的表头，别无选择才退回它们。中文 CRM 常见的 `咨询时间,客户电话,咨询内容` 选 `咨询内容`，`Message ID,Message` 选 `Message`。
  - 号码列里命中 `phone / 号码 / 电话 / mobile / whatsapp / wa` 的优先于只命中 `number` 的，`Ticket Number,Phone` 选 `Phone`。
  - 每次运行都在 stderr 打一行选中的列，例如 `columns: text=咨询内容 phone=客户电话 date=咨询时间 channel=-`（`-` 表示没有），先看这一行再交给标注人；认错了用 `--text-col` / `--phone-col` 等参数显式指定。输出里过半是 `language=und` 时 stderr 另有一句提醒，多半是正文列选错了。
  - 认不出正文列时退出码 2 并在 stderr 列出实际表头。XLSX 默认读第一个工作表，`--sheet` 可换。
- CSV 必须是 UTF-8（带不带 BOM 都行）。中文 Windows 上 Excel 的"CSV（逗号分隔）"是 GBK 编码，导入器会报错退出 1：请另存为"CSV UTF-8（逗号分隔）"，或直接交 .xlsx。CSV 按记录读，单元格里的换行、分页符、U+2028 之类不会把一条咨询切成两条。
- 每行：`sample_id` 由号码与脱敏正文哈希得到（`H-` 开头，同一条重跑不变）；`phone` 归一化为 E.164，认不出的留空；号码被 Excel 当成数字改坏的（科学计数法 `4.91761E+12`、带 `.0` 尾巴的 `4917612345678.0`）不去猜，同样留空，并计入摘要的 `phone_excel_mangled`；`conversation_text` 里的邮箱与 7 位以上数字串已替换成 `<email>` / `<number>`；`language` 已按规则预填（可能是 `und`，标注人复核）；`label_notes` 记 `来源:<渠道>;日期:<日期>`；其余标注列留空。
- 丢弃正文为空的行和（号码，正文）重复的行，`--limit N` 只留前 N 条。`--check` 只校验输出表头与 `labeling-template.csv` 一致。
- 输出文件含未打码的号码，只能放在 `data/` 下（已被 git 忽略）。

摘要打在 stdout，一行一个键值，看四处：`rows_out` 是标注人要处理的条数；`languages=de:41,en:23,...` 与 `countries=DE:38,ES:12,unknown:5,...` 看语种、国家分布是否覆盖目标市场，`unknown` 多说明导出里的号码格式有问题；`phone_excel_mangled` 大于 0 说明号码列被 Excel 改坏了，请客户从原系统重新导出（号码列设为文本格式，或直接导出 .xlsx）；`dropped_duplicate` 偏大说明导出重复拉了同一段对话。

```
rows_in=6
rows_out=4
dropped_empty=1
dropped_duplicate=1
phone_excel_mangled=0
languages=de:1,en:1,es:1,fr:1
countries=AU:1,DE:1,ES:1,unknown:1
```

### 4.1 标注与质检

1. 按 `labeling-guide.md` 标注，保存为 `data/labeled-v1.csv`，`data_origin` 填 `real`。表头必须与 `labeling-template.csv` 完全一致（导入器的输出已满足）。
2. 先用 mock 跑一遍做格式质检：加载器会一次性列出所有问题行（行号 + 原因），例如 B2B 行缺 `b2b_type`、产品代码不在目录内、号码不是合法 E.164。数据问题退出码 2（与"门槛不过"的 1 区分开）。
   - 文件必须是 UTF-8：Excel 保存时选"CSV UTF-8（逗号分隔）"。选成"CSV（逗号分隔）"在中文 Windows 上是 GBK，会报"不是 UTF-8 编码"。
   - `product_interest` 写产品代码，多个之间用分号、逗号、顿号、`/` 或 `|` 分隔，半角全角都行（`MC10;UKKO`、`MC10；UKKO`、`MC10、UKKO`）。空格不算分隔：`MC10 UKKO` 会报"一格里有两个代码"，请加分号。单个产品的常见写法照常认（`Ukko S+`、`UKKO S+ 2026`、`mc10 trail x`、`MINO B`、`M05 Pro`、`mc-10`）；目录外的写法（`MC10 Vespa`）报错，金标只收目录里的代码。
   - `phone` 若被 Excel 改成 `4.91761E+12` 或 `4917612345678.0`，报"号码列被 Excel 当成数字改坏了"：从导入批次恢复该列，并在 Excel 里把号码列设成文本格式后再保存。
3. 再用真实模型跑（第 5 节）。报告第 2 节的"真实样本数"只统计 `data_origin=real`。

```bash
python -m eval.run --input data/labeled-v1.csv --prompt prompts/classify-v1.md --model mock --out data/format-check.md
```

### 4.2 双人标注对比

`labeling-guide.md` 第 8 节要求第二人独立重标不少于 30 条（或 20%），`segment` 与 `escalation_flag` 的一致率低于 90% 就先对齐口径再重标。用一致性命令算，不要手数：

```bash
python -m eval.agreement --a data/labeled-v1.csv --b data/labeled-v1-second.csv --out data/agreement.md --json data/agreement.json
python -m eval.agreement --a data/labeled-v1.csv --b data/labeled-v1-second.csv --columns segment,escalation_flag,b2c_intent --min-agreement 0.85
```

- 两份文件表头都必须与 `labeling-template.csv` 完全一致；按 `sample_id` 取交集（第二人只标子集也行），模板示例行（`data_origin=example`）不计。
- 默认对比 `segment`、`escalation_flag`、`b2b_type`、`b2c_intent`、`country_gold`、`escalation_reason`、`is_valid_lead`，`--columns` 可改，但 `segment` 与 `escalation_flag` 永远参与。比较前去首尾空白、不分大小写；布尔列把 `true / 1 / yes / 是` 与 `false / 0 / no / 否 / 空` 归一后再比。
- 每列给交集条数、相同条数、一致率与 Cohen's κ（κ 为 `null` 表示该列只有一个取值，算不出）。Markdown 报告第 3 节是分歧清单（样本、列、A 值、B 值、脱敏后的文本摘录），交给销售负责人裁决。
- 退出码：`0` 通过；`3` `segment` 或 `escalation_flag` 任一列一致率低于 `--min-agreement`（默认 0.90）；`2` 表头不对、交集为空或 `--columns` 含未知列。stdout 末行固定为 `common=<n> segment=<0.xx> escalation_flag=<0.xx> kappa_segment=<0.xx|null> result=OK|LOW`，脚本按退出码与这一行判断即可。

## 5. 评测真实模型

密钥与地址只从环境变量读取，不写进任何文件，也不要贴进聊天或工单。

### 5.1 OpenAI 兼容接口（任何提供 `/chat/completions` 的服务）

```bash
export OPENAI_BASE_URL="https://<你的服务地址>/v1"   # 缺省为 OpenAI 官方地址
export OPENAI_API_KEY="<密钥>"
python -m eval.run --input data/labeled-v1.csv --prompt prompts/classify-v1.md \
  --model openai:<模型名> --out reports/labeled-v1-<模型名>.md --predictions-out data/pred-<模型名>.jsonl
```

`--temperature`、`--max-tokens`、`--json-mode` 默认都不发送，因为部分服务商和推理类模型会拒绝这些参数；模型支持时建议加 `--temperature 0` 以便复现。

### 5.2 Claude 模型（官方 `anthropic` SDK）

```bash
export ANTHROPIC_API_KEY="<密钥>"                    # 或先执行 ant auth login，由 SDK 自动取凭据
# export ANTHROPIC_BASE_URL="https://<网关地址>"      # 仅在经由网关时需要
python -m eval.run --input data/labeled-v1.csv --prompt prompts/classify-v1.md \
  --model anthropic:claude-opus-5 --out reports/labeled-v1-claude-opus-5.md
```

| 要点 | 说明 |
|---|---|
| 模型名 | 示例用 `claude-opus-5`；也可以传 `claude-sonnet-5`、`claude-haiku-4-5` 等。用哪个由成本与质量权衡决定，评测结果就是依据 |
| 不发送采样参数 | 新一代 Claude 模型不接受 `temperature` / `top_p` / `top_k`，`--temperature` 对 Claude 无效 |
| 思考与力度 | 不显式设置 thinking，沿用模型默认；用 `--effort low|medium|high|xhigh|max` 调整深度与花费。分类任务可以先试 `low`。并非所有模型都接受该参数，不接受时去掉即可 |
| `max_tokens` | 默认 16000（思考与输出合计的上限，不是目标长度） |
| 提示缓存 | prompt 对所有样本相同，作为带 `cache_control` 的 system 块发送；报告第 8 节分列缓存写入与读取 token。prompt 太短达不到该模型的最小可缓存长度时不会缓存，属正常 |
| 拒答与兜底 | 先看 `stop_reason` 再读内容；被拒答的样本计为失败并单列。`--anthropic-fallbacks auto`（默认）只对官方建议开启的模型打开服务端兜底，被兜底模型回答的样本数在报告第 8 节；要严格只测指定模型时用 `off` |
| 不走 OpenAI 兼容层 | Claude 模型一律用 `anthropic:` 前缀，不要经 `openai:` 调用 |

### 5.3 成本估算

设置单价后报告第 8 节给出每 100 条成本（缓存写入按输入价 1.25 倍、读取按 0.1 倍计）：

```bash
export EVAL_PRICE_INPUT_PER_1M=5      # USD / 百万输入 token
export EVAL_PRICE_OUTPUT_PER_1M=25    # USD / 百万输出 token
```

参考单价（USD / 百万 token，输入 / 输出；为 2026-06-24 的缓存价，开跑前以官网价格页为准【待核实】）：`claude-opus-5` 5 / 25；`claude-sonnet-5` 2 / 10；`claude-haiku-4-5` 1 / 5。其他服务商的单价请查各自官网，不要凭印象填。

## 6. 指标口径

| 指标 | 口径 |
|---|---|
| B 端召回率（主指标） | 标注为 B2B 的样本中，被判为 B2B 的比例 |
| B 端精确率 | 被判为 B2B 的样本中，标注确为 B2B 的比例 |
| 国家准确率 | 有号码的样本；判定国家 = 模型抽取的客户自述国家，没有则取号码国家码；与 `country_gold` 比较 |
| 产品识别率 | 标注了产品的样本，识别出的产品代码集合与标注完全一致 |
| 升级率 | 经路由规则后被标记需要人工接管的比例，含 B 端字段收集完成后的正常交接 |
| JSON 解析成功率 | 模型输出能解析且通过 `AIExtraction` 字段校验的比例，分母 = 样本数 - 调用失败数；容忍代码围栏与前后缀文字，不容忍截断，也不容忍 `b2b_type`、`b2c_intent`、`escalation_reason` 的枚举外取值 |

- 调用失败（重试后仍是 429 / 5xx / 断连）没有模型输出，不计入 JSON 解析成功率的分母；这些样本仍按生产兜底计入 B 端召回率与升级率，报告第 9 节单列"调用失败 N 条"。全部调用都失败时该项为 n/a，按"无可统计样本"判不达标。
- `segment` 的枚举外取值（例如 `business`）按生产口径处理：共享模型把 B2B / B2C 以外的值一律归为 `unknown`，这是生产有意的宽容，所以计为解析成功；标注为 B2B 的样本照常计为 B 端漏判。

每条预测都会先过 `tromox_lead.apply_routing_rules`，与集成服务是同一个函数。解析失败或调用失败的样本按生产兜底处理（`segment=unknown` 且转人工），因此会拉低 B 端召回率，这是有意为之。

## 7. 同模型、同 prompt 纪律

1. 离线评测与生产必须使用**同一模型、同一版 prompt 文件**。报告第 1 节记录了 prompt 版本与文件哈希，上线时以该哈希对应的文件为准。
2. 改 prompt 不覆盖旧文件：复制为 `classify-v2.md` 再改，重跑评测，两份报告都保留。
3. 抽取规则与 JSON 块是共享区块：改 `shared/prompt_blocks/extraction-rules.md` 或字段定义后，运行 `python scripts/gen_schema_artifacts.py`，两个 prompt 会同步更新；随后必须重跑本工具。`tests/test_eval_cli.py` 会检查仓库里的样例报告是否与当前 prompt 一致，不一致即失败。
4. 路线 A（Botmaker 内置 AI Agent）的模型在平台内，无法离线直调；离线评测用来迭代规则与示例，平台内的实际表现以 `02-botmaker/trial-test-plan.md` 的 20 条样例为准。【待核实】内置模型能否通过同款接口在平台外复现。
5. 路线 B 的外部调用应复用 `eval/prompt.py` 的 `load_prompt` 与 `build_user_message`，保证生产发给模型的内容与评测逐字一致（来源短码先剥离，不把号码与号码国家发给模型）。

## 8. 已知限制

- 只评单轮：每条样本是一位客户的文本，没有按钮选择（`button_choice` 恒为 `none`）；多轮对话中才会出现的 `not_understood_twice` 不在评测范围，由端到端用例覆盖。
- `ai_confidence` 是模型自评，未经校准；0.6 的阈值要结合报告第 3、5 节的样本复盘调整。
- 顺序调用，不并发；150 到 200 条的规模足够。
- 成本为按 token 的估算，不含 Botmaker 平台侧加价与消息费，后者见 `../03-whatsapp/cost-model.md`。

## 9. 隐私

真实咨询含个人信息：只放在 `data/`（已被 git 忽略），不要提交、不要外发；`--predictions-out` 的原始输出同样放在 `data/`。报告里的文本摘录会自动遮蔽邮箱与长数字串；正文里的邮箱与 7 位以上数字串由导入器（第 4.0 节）在生成标注文件时替换为 `<email>` / `<number>`，姓名、地址等其余项仍要在标注前按 `labeling-guide.md` 第 3 节处理。
