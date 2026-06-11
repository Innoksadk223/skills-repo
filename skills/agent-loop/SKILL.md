---
name: agent-loop
description: Use when undertaking tasks with three or more distinct steps, verifiable outcomes, reusable skills, or independent quality gates; including code changes, bug fixes, research reports, structured writing, and complex workflows. Do not use for single-step tasks, open-ended exploration, or work without measurable acceptance criteria.
---

# Agent Loop

四角色分离的迭代循环：Orchestrator 写意图和停止行为，1-N 个 Worker subagent 执行，Evaluator 反馈，Troubleshooter 修正。Loop 不是反复贴 Prompt，而是让反馈驱动下一轮动作。

## 概念内核

- Loop = 意图 + 决策者 + 反馈 + 停止条件；没有反馈的循环只是自动化误差放大器。
- 可复用单位是 Skill，不是 Prompt；PLAN 阶段必须列出本轮要调用的 skill/reference。
- 状态必须落盘到 `state/`，让 Evaluator 可独立核验，也让失败后能断点续跑。
- 预算和终止条件是生产护栏：最大轮数、无进展检测、token/时间/费用上限缺一不可。

## 流程全貌

```
PLAN（Orchestrator 输出计划 + handoff 条件）
  ↓
ACT（1-N 个 Worker subagent 执行 → 写入 state/ → mini-check → 通过才继续）
  ↓
CHECK（Evaluator 独立读取 state/ 逐项打分）
  ↓
PASS? → DELIVER
FAIL? → REVISE（Troubleshooter 诊断）→ 回到 ACT（仅重跑失败步骤）
```

## 角色总览

| 角色 | agent 位置 | 分派入口 | 职责 |
|------|------|------|------|
| Orchestrator | 你（主 agent） | — | PLAN + DELIVER + 资源调配 |
| Worker(s) | 1-N 个执行 subagent | `delegate_task` / `spawn_agent` | ACT：执行步骤，返回产出+证据 |
| Evaluator | 1 个独立验收 subagent | `delegate_task` / `spawn_agent` | CHECK：对照 checklist 逐项打分 |
| Troubleshooter | 0-1 个独立诊断 subagent | `delegate_task` / `spawn_agent` | REVISE：诊断 FAIL + 输出修正方案 |

**核心规则：`delegate_task` / `spawn_agent` 是分派入口，不是角色身份。干活的 agent 不能给自己打分；每个 subagent 在同一轮只担任一个角色。**

## 终止条件

| 条件 | 触发动作 |
|------|---------|
| Evaluator 判定 PASS | DELIVER |
| 累计 3 轮 | DELIVER + 标注未达标项 |
| 连续 2 轮提升 <10%（STAGNATE） | DELIVER |
| 达到 token/时间/费用预算 | DELIVER + 标注预算耗尽 |

## Reference 加载决策表

| 你要做什么 | 加载 |
|-----------|------|
| 制定/修订执行计划、设计 checklist | `references/plan.md` |
| 分派 Worker、执行 mini-check | `references/act.md` |
| 启动 Evaluator 验收 | `references/check.md` |
| Evaluator 判定 FAIL，需诊断修正 | `references/revise.md` |
| 判断终止/继续、排查异常 | `references/termination.md` |

## 参考

| 文件 | 何时加载 |
|------|---------|
| [references/plan.md] | PLAN 阶段：制定计划、设计 checklist、设定 handoff |
| [references/act.md] | ACT 阶段：分派 Worker、mini-check、并行协调 |
| [references/check.md] | CHECK 阶段：分派 Evaluator、解读评估结果 |
| [references/revise.md] | REVISE 阶段：分派 Troubleshooter、应用修正 |
| [references/termination.md] | 决策点：终止判断、token 代价、陷阱排查 |
