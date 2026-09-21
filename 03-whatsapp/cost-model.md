# 第三方费用成本模型：公式与口径

> 用途：说明 `cost_model.py` 怎么算、每个输入从哪来、结果怎么读；是全仓库第三方费用数字的唯一源头。读者：集成工程师、张宝文。
> 结果表见 `cost-model-results.md`（脚本生成）；客户文档只引用其中第 5 节的取整值。

## 1. 为什么要单独建模

2026-10-01 起，24 小时客服窗口内的自由回复按条计费，AI 回复和销售人工回复都算（SOURCES S-M1）。MVP 上线必然在此之后，所以"每个对话发几条消息"直接变成钱。模型把计费规则做成**参数**，规则有变只改输入，不改代码。

## 2. 文件

| 文件 | 作用 | 是否手改 |
|---|---|---|
| `cost-model-inputs.csv` | 低/中/高三档的全部输入，含状态列（假设 / 【待核实】 / 【待客户确认】 / 已复核） | 是 |
| `cost-model-rates.csv` | 各市场对话占比与费率；无官方数字的市场用代理值 | 是 |
| `cost_model.py` | 计算脚本 | 改逻辑时 |
| `cost-model-results.md` | 结果表、敏感性分析、供引用的取整数字 | 否（生成） |
| `cost-model-summary.json` | 同上，机器可读；`scripts/check_repo.py` 用它核对客户文档 | 否（生成） |
| `cost-model.xlsx` | 静态数值导出，方便转发；不含活公式 | 否（生成） |

运行：

```bash
python 03-whatsapp/cost_model.py          # 重新生成
python 03-whatsapp/cost_model.py --check  # 输出过期则退出码 1
```

## 3. 公式

记号：`N` 月对话数，`b` B 端占比，`r̄` 加权平均费率。

1. 月对话数：`N = daily_inquiries × 30`；B 端 `N_b = N × b`，C 端 `N_c = N − N_b`。
2. AI 发出的消息：`M_ai = N_b × ai_msgs_per_conv_b2b + N_c × ai_msgs_per_conv_b2c`。
3. 人工发出的消息（销售经 Botmaker 用公司号回复）：`M_h = N_b × human_msgs_per_conv_b2b + N_c × human_handoff_share_b2c × human_msgs_per_conv_b2c`。
4. 窗口内消息总数：`M = M_ai + M_h`。
5. 免费入口抵扣：`M_fep = M × ctwa_share`（经 Click-to-WhatsApp 广告或 Facebook 主页按钮进入的对话，72 小时内免费，SOURCES S-M1）。
6. 月度免费额度抵扣：`M_free = min(M − M_fep, free_service_msgs_per_month)`（【待核实】，SOURCES S-M3）。
7. 计费条数：`M_bill = M − M_fep − M_free`。
8. 加权平均费率：`r̄ = Σ 市场占比 × 该市场费率`；客服消息费率与该市场 utility 费率相同（SOURCES S-M1）。
9. Meta 客服消息费：`M_bill × r̄ × (1 + bsp_markup_service)`。
10. 再触达模板费：`N_b × template_followup_share_b2b × templates_per_followup × r̄ × (1 + bsp_markup_template)`。
11. Botmaker 套餐：在 Standard / Scale / Pro 中取"月费 + 超量 × 0.025 USD"最低者（SOURCES S-B3）。
12. Botmaker AI token 费：`M_ai × ai_tokens_per_ai_msg ÷ 1,000,000 × botmaker_ai_usd_per_1m_tokens`（路线 A、B 都有，因为对话与 FAQ 始终由内置 AI Agent 承担）。
13. 外部模型费（仅路线 B 增量）：`N × route_b_calls_per_conv × (输入 token × 输入单价 + 输出 token × 输出单价) ÷ 1,000,000`。
14. 合计：路线 A = 9 + 10 + 11 + 12 + 托管；路线 B = 路线 A + 13。人民币 = 美元 × `usd_to_cny`。

## 4. 口径与假设

- **"对话"的定义**：Botmaker 套餐里的 conversation 未见官方定义，超量条款写的是 "per additional user"；模型按"一个月内一个客户算一个对话"处理。【待核实】
- **套餐升档**：按公开单价，"Standard + 超量"在任何对话量下都不比升档贵；升 Scale / Pro 的理由是坐席数（10 / 20 / 50），不是对话量。超量是否允许长期不升档。【待核实】
- **代理费率**：法、意、西和"其他市场"没有取得官方数字，用已复核市场的算术平均代替（西欧组取德、荷、英；全部组取所有已复核市场）。这只保证量级正确。拿到 Meta 费率卡后，把数字填进 `cost-model-rates.csv` 的 `rate_usd` 列即可替换代理值。【待核实】
- **免费额度先按总量抵扣**：实际按时间先后抵扣，不分国家；模型按比例近似，对月合计影响可忽略。
- **Coexistence 下销售用手机 App 回复的消息免费**（SOURCES S-M6）；敏感性分析里单列了这一情景。
- **不含**：广告投放费、号码月租、销售人力、我们的服务费。
- **汇率**：7.10 为假设，按开票当月实际汇率更新。

## 5. 怎么读结果

1. 消息费与 AI token 费都和"每对话条数"成正比：每对话多 2 条 AI 消息，中档每月约多 78 USD。话术"一条说清、多用按钮"是成本约束，不只是体验要求。
2. 德国等高费率市场占比越高越贵；客户给出真实国家分布后重跑，结果可能变化一倍以上。
3. 引导投放走 Click-to-WhatsApp 是最直接的降本手段：占比从 20% 提到 50%，中档每月约省 77 USD。
4. 路线 B 的外部模型费在任何档位都很小，A/B 决策应看抽取稳定性，不看这项成本。

## 6. 待确认项

全部输入的状态见两份 CSV 的 status 列；汇总在仓库的待决问题清单里。客户给出日均咨询量、国家分布、是否投 CTWA 三个数后，必须重跑并同步更新报价单的第三方费用表。
