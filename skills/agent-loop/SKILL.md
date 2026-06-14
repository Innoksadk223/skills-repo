---
name: agent-loop
description: "Use when a concrete task has multiple steps, verifiable outcomes, reusable skills, independent quality gates, or unclear acceptance criteria that can be clarified. Also use when explicitly invoked as agent-loop."
---
# Agent Loop
**不要给 Agent 写 Prompt，写 Loop——让 Loop 给 Agent 写 Prompt。**
Agent Loop 是通用 Agent 编排循环——产出是经过多轮 Worker 执行 + Feedbacker 反馈修正后的最终交付物。主 agent 只做验收，不替 Worker 干活。
## 概念内核
- **Loop = cron + 决策者**。cron 调度，Feedbacker 判断每轮下一步。可以引入辅助脚本 / webhook 来实现自动化调度以推进循环。
- **Worktree = `state/` 目录**。Worker 产出写入 worktree，Feedbacker 读取并反馈；同一 Worker 会话持续修正直到通过。
- **Skill > Prompt**。可复用单位是 Skill，PLAN 必须列出本轮 skill/reference。
## 优先级与组合规则
- **调用即显式触发**：用户点名本 skill 或任务命中条件，即进入 Loop。
- **Loop > Prompt**：命中条件即先进入 Loop，不得用一次性 prompt 绕过。
- **Loop 是外层调度器**：其他 skill 是 PLAN/ACT/FEEDBACK/VERIFY 中被调用的能力单元。
- **Skill > Prompt**：有匹配 skill 时 PLAN 必须列出，Worker goal 必须加载。
- **Hard gate 兼容**：其他 skill 的审批/设计/TDD/验证硬门槛写进 handoff 或 checklist，不绕过。
- **可续写优先**：修正轮优先复用原 Worker 会话；不支持时走 state replay（详见 `references/act.md`）。
## 流程全貌
```
SOCRATIC INTAKE（Orchestrator 先通过苏格拉底式提问明确目标、约束、停止条件，并写入本地）
  ↓
PLAN（Orchestrator 输出计划 + checklist + handoff 条件）
  ↓
ACT（分派 1-N 个 Worker subagent 执行 → 写入 state/ → mini-check）
  ↓
FEEDBACK（分派 1 个可持续对话（stateful）的 Feedbacker subagent 审核 state/ → 针对性写修正 prompt）
  ↓
ACT-FIX（将 Feedbacker 的修正 prompt 发回原 Worker 会话；若不支持续写则走 state replay 流程 → 更新 state/）
  ↓
  ↑—— 如果 Feedbacker 判断仍需修正，向此可持续对话的 Feedbacker 发送新产出让其继续反馈 → ACT-FIX
  ↓
VERIFY（Orchestrator 最终比对需求和成果进行验收）
  ↓
PASS 且是最终成果 → DELIVER
PASS 但交付物本身指出可操作改进项 → 自动进入 FEEDBACK → ACT-FIX（不询问用户）
FAIL → FEEDBACK → ACT-FIX（继续修正）
```
## 角色总览
- **Orchestrator**（主 agent）：PLAN + VERIFY + DELIVER。先想后做，不替 Worker 执行。
- **Worker(s)**：→ 详见 `references/act.md` 的 Worker 角色定义与执行流程。
- **Feedbacker**（1 个）：→ 详见 `references/feedback.md` 的 Feedbacker 角色定义。只派出一个可持续对话（stateful）的实例。
## 终止条件
→ 详见 `references/termination.md`（含陷阱排查表）。
## Reference 加载决策表
| 你要做什么 | 加载 |
|-----------|------|
| 制定计划、checklist、worktree 结构 | `references/plan.md` |
| 分派 Worker、执行、修正回合 | `references/act.md` |
| 判定宿主 worker 能力 | `references/hosts/<host>.md` |
| 分派 Feedbacker、生成修正 prompt | `references/feedback.md` |
| 对照 checklist 验收交付物 | `references/verify.md` |
| 终止判断、代价、陷阱 | `references/termination.md` |
| 无法分派时的本地模拟 | `references/fallback-local.md` |
| 通过/终止后的交付 | `references/deliver.md` |
