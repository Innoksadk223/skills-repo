---
name: social-science-paper-review
description: Strict peer review and revision guidance for social-science manuscripts, articles, preprints, theses, working papers, and journal submissions. Use when asked to review, critique, audit, or improve social-science papers in sociology, political science, economics-adjacent empirical work, communication, education, psychology, management, public policy, anthropology, or related fields; especially when the user wants reviewer-style judgments plus concrete author-facing revision advice.
---

# Social Science Paper Review

## 调度流程

1. **M1** — 确认论文类型、审阅场景和证据材料 → `state/M1_review_brief.json`
2. **M2** — 提取核心论点、理论贡献和证据链 → `state/M2_claim_map.json`
3. **M3** — 按研究设计审查方法、材料、识别和可信度 → `state/M3_method_audit.json`
4. **M4** — 评估文献定位、贡献边界、伦理和外推 → `state/M4_positioning_audit.json`
5. **M5** — 输出严格审稿意见和修改指导 → `state/M5_review_report.md`

## 决策树

- 如果用户只给摘要或片段，先说明审阅置信度受限，再执行 M1-M5 的轻量版。
- 如果论文是定量研究，M3 重点审查测量、样本、识别策略、模型设定、稳健性和效应解释。
- 如果论文是定性研究，M3 重点审查案例选择、材料来源、编码/解释过程、反例处理、厚描和证据透明度。
- 如果论文是混合方法，M3 同时审查两类证据，并检查两者是否真正互相支撑。
- 如果论文是综述或理论论文，M3 降权，M4 加权审查文献覆盖、分类框架、概念创新和论证完整性。
- 如果用户要“帮我修改”，M5 必须同时给出审稿结论和作者修改路线，不只列问题。

## 模块清单

| 模块 | 文件 | 输入 | 输出 |
|------|------|------|------|
| M1 | [M1_review_brief.md](references/M1_review_brief.md) | 用户请求、论文全文/摘要/链接 | `state/M1_review_brief.json` |
| M2 | [M2_claim_map.md](references/M2_claim_map.md) | M1、论文文本 | `state/M2_claim_map.json` |
| M3 | [M3_method_audit.md](references/M3_method_audit.md) | M1、M2、论文方法和结果 | `state/M3_method_audit.json` |
| M4 | [M4_positioning_audit.md](references/M4_positioning_audit.md) | M1-M3、文献和讨论部分 | `state/M4_positioning_audit.json` |
| M5 | [M5_review_report.md](references/M5_review_report.md) | M1-M4 | `state/M5_review_report.md` |

## 审阅原则

- 先判断“论文想解决什么问题”，再判断“证据是否支撑这个问题”；不要只做文字润色。
- 审查文章是否有一条清晰主线：研究问题、理论/概念、方法、证据、讨论和结论必须形成连续论证链。
- 把“致命问题”“大修问题”“小修问题”分开；每个重大问题都要给出可执行修改方案。
- 社科论文优先审查理论-概念-测量-证据-结论的一致性。
- 审查引用是否被作者解释并转化为自己的论证；不要把引用堆砌误判为文献综述充分。
- 基础表达问题也要记录：错字、衍字、病句、句式不通畅，以及连接词/承接词过多或过少导致的阅读问题。
- 不用作者身份、机构、题目热门程度替代论文质量判断。
- 不把个人偏好的理论立场当作拒稿理由；只评价论证是否清楚、证据是否足够、替代解释是否处理。
- 涉及真实人群、敏感群体、田野材料或政策影响时，必须检查伦理、匿名化、偏见和伤害风险。

## 可选参考

需要核对报告规范时读取 [standards-and-sources.md](references/standards-and-sources.md)。不要把这些清单机械套用成打分表；根据论文类型选用相关项。
