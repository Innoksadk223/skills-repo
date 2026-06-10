# Agent Loop 设计决策记录

2026-06-10 grill-me 会话产出。后续有追加决策。

## 初版决策（Q1-Q8）

### Q1: 适用场景
代码 + 研究/写作 + 复杂多步骤任务（≥3 环节）。

### Q2: 验收方式
**初版选 C**（结构化 checklist 自检）。但后续发现同一 agent 自评存在系统性宽松偏差 → **追加决策**：独立 Evaluator agent（delegate_task spawn）做验收，Orchestrator 不碰打分。

### Q3: 问题诊断和 prompt 重写
**初版选 A**（合并，主 agent 兼任）。后续因同样原因（自评偏差 + 角色混淆）→ **追加决策**：独立 Troubleshooter agent（delegate_task spawn）做诊断和修正。

### Q4: Worker 并行策略
动态判断。依赖串行、无依赖并行（batch delegate_task ≤3）。

### Q5: 规划深度
动态，但必须输出主要步骤 + 边界条件。

### Q6: 终止条件
3 轮硬上限 + 连续 2 轮提升 < 10% 提前终止。

### Q7: 资源调整
模型选择、并发数、toolsets、上下文注入量——全部动态。

### Q8: 实现路径
**初版**：单 agent 内嵌 loop（技能定义流程纪律，agent 自己执行+验收）。
**追加 v2**：四角色分离（Orchestrator / Worker / Evaluator / Troubleshooter），全部通过 delegate_task 隔离。
**追加 v3**：skill description 改为框架无关通用描述。

---

## v3 架构决策（2026-06-10 追加）

**核心理由**：同一 agent 既执行又验收 → 天然宽松。消除自评偏差的唯一方法是角色隔离。

| 角色 | delegate? | 职责 | 防止 |
|------|:---:|------|------|
| Orchestrator | — | PLAN + DELIVER | — |
| Worker | ✅ | ACT 执行 | 自评 |
| Evaluator | ✅ | CHECK 打分 | 宽松偏差 |
| Troubleshooter | ✅ | 诊断+修正 | 执行者修复自己的错 |

代价：每轮 +2 次 LLM 调用（Evaluator + Troubleshooter）。收益：消除自评偏差。
