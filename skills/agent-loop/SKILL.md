---
name: agent-loop
description: "Use when a concrete task has multiple steps, verifiable outcomes, reusable skills, independent quality gates, or unclear acceptance criteria that can be clarified. Also use when explicitly invoked as agent-loop."
---

# Agent Loop

通用 Agent 编排循环：主 agent 理解任务、列出需求、制定计划；1-N 个执行 subagent 完成任务；1 个反馈 subagent 审核产出、指出问题或提质空间，并针对问题写下一轮 prompt；执行 subagent 按 prompt 修正；最终由主 agent 验收任务是否完成。

Loop 不是反复贴 Prompt，而是让反馈驱动下一轮动作。

## 概念内核

- Loop = 意图 + 决策者 + 反馈 + 停止条件；没有反馈的循环只是自动化误差放大器。
- 可复用单位是 Skill，不是 Prompt；PLAN 阶段必须列出本轮要调用的 skill/reference。
- 状态必须落盘到 `state/`，让 Feedbacker 可审核反馈，也让主 agent 可验收和断点续跑。
- 预算和终止条件是生产护栏：最大轮数、无进展检测、token/时间/费用上限缺一不可。

## 优先级与组合规则

- **调用即显式触发**：用户点名本 skill，或任务命中触发条件，就视为明确进入 Loop，并授权使用当前宿主可用的 subagent / worker / thread / task 分派能力。
- **触发判定用 OR**：三步以上、可验证结果、可复用 skill、独立质量门槛、或"有具体产物但验收标准模糊"任一满足，即先进入 Loop。
- **Loop > Prompt**：只要任务命中本 skill 触发条件，必须先进入 Loop；不得只说"参考 loop 思想"后直接用一次性 prompt 开干。
- **Loop 是外层调度器**：其它 skill/reference 不是竞争入口，而是 PLAN/ACT/FEEDBACK/VERIFY 中被调用的能力单元。
- **Skill > Prompt**：某步骤已有匹配 skill 时，PLAN 必须列出它，Worker goal 必须要求先加载并遵循它；只有没有可复用 skill 时才写一次性 prompt。
- **Hard gate 兼容**：其它 skill 若有审批、设计、TDD、验证等硬门槛，Loop 不绕过；把这些门槛写进步骤 handoff 或 checklist。
- **验收模糊也进 Loop**：目标有具体产物但标准不清时，在 PLAN 中调用 brainstorming 或相关 skill 补齐标准，而不是跳过 Loop。
- **分派入口保持通用**：优先使用宿主提供的分派入口，例如 subagent、worker、thread、task、`delegate_task`、`spawn_agent`。若环境或权限不能分派，明说限制，并在本地模拟 Worker/Feedbacker；不得静默降级为普通执行。

## 流程全貌

```
PLAN（Orchestrator 输出计划 + handoff 条件）
  ↓
ACT（1-N 个 Worker subagent 执行 → 写入 state/ → mini-check → 通过才继续）
  ↓
FEEDBACK（Feedbacker 审核 state/ → 反馈问题或提质点 → 写修正 prompt / delta plan）
  ↓
ACT-FIX（Worker 按 Feedbacker prompt 修正 → 更新 state/）
  ↓
VERIFY（Orchestrator 对照 checklist 验收）
  ↓
PASS? → DELIVER
FAIL? → FEEDBACK → ACT-FIX（仅重跑失败步骤）
```

## 角色总览

| 角色 | agent 位置 | 分派入口 | 职责 |
|------|------|------|------|
| Orchestrator | 你（主 agent） | — | PLAN + VERIFY + DELIVER + 资源调配 |
| Worker(s) | 1-N 个执行 subagent | 宿主可用分派入口 | ACT：执行步骤，返回产出+证据 |
| Feedbacker | 1 个反馈 subagent | 宿主可用分派入口 | FEEDBACK：审核产出，反馈问题或提质空间，写下一轮 Worker prompt / delta plan |

**核心规则：分派入口不是角色身份。干活的 agent 不给自己写反馈 prompt；Feedbacker 不直接改产物；最终验收由主 agent 对照原始需求和 checklist 完成。**

## 终止条件

| 条件 | 触发动作 |
|------|---------|
| Orchestrator 验收 PASS | DELIVER |
| 累计 3 轮 | DELIVER + 标注未达标项 |
| 连续 2 轮提升 <10%（STAGNATE） | DELIVER |
| 达到 token/时间/费用预算 | DELIVER + 标注预算耗尽 |

## Reference 加载决策表

| 你要做什么 | 加载 |
|-----------|------|
| 制定/修订执行计划、设计 checklist | `references/plan.md` |
| 分派 Worker、执行 mini-check | `references/act.md` |
| Worker 完成后生成反馈/修正 prompt | `references/revise.md` |
| 主 agent 验收是否完成 | `references/check.md` |
| 主 agent 验收 FAIL，需反馈修正 | `references/revise.md` |
| 任务同时触发多个 skill、需处理 hard gate | `references/plan.md` + 对应 skill |
| 判断终止/继续、排查异常 | `references/termination.md` |

## 参考

| 文件 | 何时加载 |
|------|---------|
| [references/plan.md] | PLAN 阶段：制定计划、设计 checklist、设定 handoff |
| [references/act.md] | ACT 阶段：分派 Worker、mini-check、并行协调 |
| [references/revise.md] | FEEDBACK 阶段：分派 Feedbacker、生成修正 prompt |
| [references/check.md] | VERIFY 阶段：主 agent 对照 checklist 验收 |
| [references/termination.md] | 决策点：终止判断、token 代价、陷阱排查 |
