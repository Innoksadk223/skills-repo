---
name: agent-loop
description: "Use when a concrete task has multiple steps, verifiable outcomes, reusable skills, independent quality gates, or unclear acceptance criteria that can be clarified. Also use when explicitly invoked as agent-loop."
---

# Agent Loop

**不要给 Agent 写 Prompt，写 Loop——让 Loop 给 Agent 写 Prompt。**

Agent Loop 是通用 Agent 编排循环。它不是一个「生成计划」的工具——它的产出是**经过多轮 Worker 执行 + Feedbacker 反馈修正后的最终交付物**。主 agent 只做验收，不替 Worker 干活。

## 概念内核

- **Loop = cron + 决策者**。cron 负责调度，决策者（Feedbacker）负责每一轮判断下一步做什么、是否完成。
- **Worktree = `state/` 目录**。它是持久化工作区。Worker 产出写进 worktree，Feedbacker 读 worktree 给出反馈，**同一个 Worker agent 在内部多轮对话中**持续读取反馈、修正产出、更新 worktree——直到 Feedbacker 认为通过或达到终止条件。Worktree 是 Worker 和 Feedbacker 之间对话的"案卷"，不是换人时的交接文件。
- **可复用单位是 Skill，不是 Prompt**。PLAN 阶段必须列出本轮要调用的 skill/reference。
- **最终交付的是成果，不是计划和分析**。PLAN 是脚手架，`state/` 里的产出物才是交付对象。
- **验证比编排更重要**。Loop 的好坏取决于自我检查能力。没有反馈闭环的 Loop 只是自信地制造错误。

## 优先级与组合规则

- **调用即显式触发**：用户点名本 skill，或任务命中触发条件，即视为明确进入 Loop，并授权使用宿主提供的 subagent / worker 分派能力。
- **Loop > Prompt**：只要任务命中触发条件，必须先进入 Loop；不得「参考 loop 思想」后直接用一次性 prompt 开干。
- **Loop 是外层调度器**：其他 skill 不是竞争入口，而是 PLAN/ACT/FEEDBACK/VERIFY 中被调用的能力单元。agent-loop 不干涉其他 skill 的内部逻辑，只负责编排调度。
- **Skill > Prompt**：某步骤已有匹配 skill 时，PLAN 必须列出它，Worker goal 必须要求先加载并遵循它。
- **Hard gate 兼容**：其他 skill 若有审批、设计、TDD、验证等硬门槛，Loop 不绕过；把这些门槛写进 handoff 或 checklist。
- **验收模糊也进 Loop**：目标有具体产物但标准不清时，在 PLAN 中补齐标准，而非跳过 Loop。

## 分派模式

agent-loop 支持两种分派模式，由宿主能力自动判定。

### 自动分派

宿主支持程序化分派 subagent 时，Orchestrator 直接分派 Worker 和 Feedbacker，无需用户介入。流程全自动运行。

### 手动分派

宿主不支持程序化分派（如需要用户手动触发 agent）时，Orchestrator 不尝试自动分派——而是将每个 Worker/Feedbacker 的 goal 输出为独立的消息块：

```
--- 请分派 [Worker/Feedbacker] agent ---
goal: [完整的执行描述 + 输出路径 + handoff 条件]
toolsets: [最小必要集]
```

用户手动分派 agent 并将执行结果粘贴回来后，Orchestrator 继续下一步（mini-check → Feedbacker → ACT-FIX → VERIFY）。流程逻辑和终止条件不变——只是分派动作由用户代替程序完成。

## 流程全貌

```
PLAN（Orchestrator 输出计划 + checklist + handoff 条件）
  ↓
ACT（分派 1-N 个 Worker subagent 执行 → 写入 state/ → mini-check）
  ↓
FEEDBACK（分派 1 个 Feedbacker subagent 审核 state/ → 诊断根因 → 写针对性的修正 prompt）
  ↓
ACT-FIX（将 Feedbacker 的修正 prompt 发回同一个 Worker → Worker 读取反馈，在已有会话中继续修正 → 更新 state/）
  ↓
  ↑—— 如果 Feedbacker 判断仍需修正，重复 FEEDBACK → ACT-FIX
  ↓
VERIFY（Orchestrator 对照 checklist 验收 state/ 中的最终交付物）
  ↓
PASS? → DELIVER
FAIL? → FEEDBACK → ACT-FIX（继续修正）
```

**核心机制**：不是"每轮换一个新 Worker 实例读 worktree 从头开始"，而是**同一个 Worker agent 维持多轮对话**——它产出初稿，接收 Feedbacker 的针对性 prompt，在已经理解任务上下文的前提下直接修正。Worktree（`state/`）是对话中的共享案卷，Feedbacker 读它来给出判断，Worker 读它来了解反馈指向什么。

## 角色总览

| 角色 | 位置 | 职责 |
|------|------|------|
| Orchestrator | 主 agent | PLAN + VERIFY + DELIVER。不执行、不写修正 prompt |
| Worker(s) | 1-N 个 subagent | 多轮对话中持续工作。产出 → 收反馈 → 修正 → 更新 worktree |
| Feedbacker | 1 个 subagent | 读 worktree → 诊断根因 → **写针对 Worker 的修正 prompt** |

**Feedbacker 只有一个**——反馈必须一致、不矛盾。Worker 不限制数量，按依赖和预算决定。

Feedbacker 的输出不是分析报告给主 agent 看——**是发给 Worker 的修正指令**。主 agent 只负责把 Feedbacker 的 prompt 转发给 Worker，不修改、不转述。

## 终止条件

| 条件 | 触发动作 |
|------|---------|
| Orchestrator 验收 PASS | DELIVER |
| 累计 3 轮 FEEDBACK→ACT-FIX | DELIVER + 标注未达标项 |
| 连续 2 轮提升 <10%（STAGNATE） | DELIVER |
| 达到 token/时间/费用预算 | DELIVER + 标注预算耗尽 |

## Reference 加载决策表

| 你要做什么 | 加载 |
|-----------|------|
| 制定/修订执行计划、设计 checklist、声明 worktree 结构 | `references/plan.md` |
| 分派 Worker、执行 mini-check、处理反馈修正回合 | `references/act.md` |
| 分派 Feedbacker、生成针对 Worker 的修正 prompt | `references/revise.md` |
| 主 agent 对照 checklist 验收 worktree 中的交付物 | `references/check.md` |
| 终止判断、token 代价、陷阱排查 | `references/termination.md` |

## 参考

| 文件 | 何时加载 |
|------|---------|
| [references/plan.md] | PLAN 阶段：制定计划、设计 checklist、设定 worktree |
| [references/act.md] | ACT 阶段：分派 Worker、mini-check、反馈修正回合、worktree 读写 |
| [references/revise.md] | FEEDBACK 阶段：分派 Feedbacker、生成针对 Worker 的修正 prompt、写入 worktree |
| [references/check.md] | VERIFY 阶段：主 agent 验收 worktree 中的最终交付物 |
| [references/termination.md] | 决策点：终止判断、token 代价、陷阱排查 |
