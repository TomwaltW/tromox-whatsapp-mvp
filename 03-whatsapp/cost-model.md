# 第三方费用成本模型：公式与口径

> 用途：说明 `cost_model.py` 怎么算、每个输入从哪来、结果怎么读；是全仓库第三方费用数字的唯一源头。读者：集成工程师、张宝文。
> 结果表见 `cost-model-results.md`（脚本生成）；客户文档只引用其中第 5 节的取整值。

## 1. 为什么要单独建模

2026-10-01 起，24 小时客服窗口内的自由回复按条计费，AI 回复和销售人工回复都算（SOURCES S-M1）。MVP 上线必然在此之后，所以"每个对话发几条消息"直接变成钱。模型把计费规则做成**参数**，规则有变只改输入，不改代码。

## 2. 文件

| 文件 | 作用 | 是否手改 |
|---|---|---|
| `cost-model-inputs.csv` | 低/中/高三档的全部输入，含状态列（假设 / 【待核实】 / 【待客户确认】 / 已复核） | 是 |
| `cost-model-rates.csv` | 各市场对话占比与费率（Meta 官方费率卡）；国家构成未知的"其他市场"用代理值 | 是 |
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
6. 月度免费额度抵扣：`M_free = min(M − M_fep, free_service_msgs_per_month)`（每号码每月 1,000 条，Meta 官方已确认，SOURCES S-M3）。免费入口窗口内的消息不占额度是由官方计费类型推断的【待核实】；MVP 只用 1 个号码。
7. 计费条数：`M_bill = M − M_fep − M_free`。
8. 加权平均费率：`r̄ = Σ 市场占比 × 该市场费率`；客服消息费率与该市场 utility 费率相同（SOURCES S-M1）。
9. Meta 客服消息费：`M_bill × r̄ × (1 + bsp_markup_service)`。
10. 再触达模板费：`N_b × template_followup_share_b2b × templates_per_followup × r̄ × (1 + bsp_markup_template)`。
11. Botmaker 套餐：在 Standard / Scale / Pro 中取"月费 + 超量 × 该档超量单价"最低者，超量单价按定价页取 0.07 / 0.06 / 0.05 USD（SOURCES S-B3；FAQ 写 0.025，两页矛盾【待核实】）。
12. Botmaker AI token 费：`M_ai × ai_tokens_per_ai_msg ÷ 1,000,000 × botmaker_ai_usd_per_1m_tokens`（路线 A、B 都有，因为对话与 FAQ 始终由内置 AI Agent 承担）。
13. 外部模型费（仅路线 B 增量）：`N × route_b_calls_per_conv × (输入 token × 输入单价 + 输出 token × 输出单价) ÷ 1,000,000`。
14. 合计：路线 A = 9 + 10 + 11 + 12 + 托管；路线 B = 路线 A + 13。人民币 = 美元 × `usd_to_cny`。

## 4. 口径与假设

- **"对话"的定义**：Botmaker 服务条款按 DAILY USER 计数，即 24 小时内收发过消息的外部用户（SOURCES S-B3）；同一客户隔天再来会再算一次。模型按"一个新咨询算一个对话"处理，客户多日往返时会低估。【待核实】
- **套餐升档**：按定价页的分档超量单价，月对话数超过约 4,430 时 Scale 比"Standard + 超量"便宜，超过约 9,170 时 Pro 比 Scale 便宜；坐席数（10 / 20 / 50）也可能决定档位。超量是否允许长期不升档【待核实】。
- **费率**：各市场单价取自 Meta 官方费率卡（SOURCES S-M4，10/1 起服务消息单价等于 utility 单价）。只有国家构成未知的"其他市场"仍用代理值：全部有官方费率市场的算术平均，含德、荷等高价市场，偏保守。拿到真实国家分布后按实际国家填 `cost-model-rates.csv`（区域组单价见 S-M4，如西欧其他 0.0171、亚太其他 0.0113）。【待客户确认】
- **免费额度先按总量抵扣**：实际按时间先后抵扣，不分国家；模型按比例近似，对月合计影响可忽略。
- **Coexistence 下销售用手机 App 回复的消息免费**（SOURCES S-M6）；敏感性分析里单列了这一情景。
- **不含**：广告投放费、号码月租、销售人力、我们的服务费；Botmaker webhook 附加功能费（额外计费、单价未公开【待核实】，SOURCES S-B5），报价单里单列为"未公开"。
- **汇率**：7.10 为假设，按开票当月实际汇率更新。

## 5. 怎么读结果

1. 消息费与 AI token 费都和"每对话条数"成正比：每对话多 2 条 AI 消息，中档每月约多 78 USD。话术"一条说清、多用按钮"是成本约束，不只是体验要求。
2. 德国等高费率市场占比越高越贵；客户给出真实国家分布后重跑，结果可能变化一倍以上。
3. 引导投放走 Click-to-WhatsApp 是最直接的降本手段：占比从 20% 提到 50%，中档每月约省 77 USD。
4. 路线 B 的外部模型费在任何档位都很小，A/B 决策应看抽取稳定性，不看这项成本。

## 6. 待确认项

全部输入的状态见两份 CSV 的 status 列；汇总在仓库的待决问题清单里。客户给出日均咨询量、国家分布、是否投 CTWA 三个数后，必须重跑并同步更新报价单的第三方费用表。
