---
name: pi-agent-loop
description: "Use when a Pi task needs orchestrated multi-agent convergence: the main Pi registers one confirmed Agent Team plan, manually advances Coder execution, independent Reviewer decisions, same-task fix attempts, optional read-only experts/optimizer, final verification, and explicit human acceptance. Also use for /agent-loop, multi-round implementation, or context-aware resumable team work."
---

# Pi Agent Loop

主 Pi 是唯一 **Leader/Planner/Coordinator**，负责需求、计划、角色选择、显式调度、意见解释、范围裁决和人类验收，不承担主要编码。runtime TeamState 是实时结构化事实源，只执行授权、依赖、成员状态和路径冲突约束，不做业务决策或自动调度。

基础角色：

- **Coder/Executor**：实现 TaskPacket；只写 owned paths；只能提交 `SUBMITTED/BLOCKED`。
- **Reviewer**：独立、只读；唯一能通过 ReviewRound 写 `VERIFIED/FIX_REQUIRED`，并负责 FINAL_VERIFY。
- **可选专家**：debugger/product/optimizer 是只读 ExpertRound；不取 ownership、不改 verdict。复杂根因才启用 debugger；optimizer 在实现已 VERIFIED 后检查候选。

成员不直接通信、不递归调用 `agent_team`。协作请求只在 settled JSON envelope 中交 Leader。

## 渐进开卷

| 阶段 | 必读 |
| --- | --- |
| PLAN / USER_GATE | 本文 + `references/contract-template.md` |
| 角色 prompt / DISPATCH | + `references/protocol.md` §1-§3 |
| REVIEW / FIX | + protocol §4 |
| EXPERT / OPTIMIZER | + protocol §5 |
| FINAL / 恢复 / HUMAN_ACCEPT | + protocol §6-§8 |

常规决策先用 compact `agent_team status`；只有需要完整 roster/DAG/TaskPacket 才 `status full:true`。不读取无关全局计划、历史正文或旧共享状态文件。

## 一次计划门

PLAN 明确 goal、non-goals、assumptions、固定 roster、唯一 reviewer、ExecutionTask DAG、concrete owned paths、TaskPacket 与 acceptance。调用一次 `agent_team plan` 进入 USER_GATE；确认前不派工。

同一计划后续轮次只传 task/review/expert ID。新增成员/任务或改变成员配置、ownership、acceptance 时，携带实时 `expectedRevision` 重新提交完整 plan 并再次 USER_GATE。状态迁移、同一 task 的 fix attempt 不 amendment。

## 手动循环

```text
PLAN -> USER_GATE -> run/parallel READY task
     -> SUBMITTED -> ReviewRound
     -> VERIFIED | FIX_REQUIRED
                    FIX_REQUIRED -> same task attempt+1 -> ReviewRound ...
     -> optional ExpertRound/Optimizer -> FINAL_VERIFY -> HUMAN_ACCEPT
```

1. Leader 显式 `run(taskId)` 或 `parallel(taskIds)`；runtime 在 prompt 前重新校验实时状态。
2. Coder settled 后，合法 envelope 只进入 `SUBMITTED/BLOCKED`；损坏报告进入 `REPORT_INVALID`。
3. Leader 对一批 SUBMITTED task 显式创建 ReviewRound。Reviewer逐项给 `VERIFIED/FIX_REQUIRED`。
4. FIX_REQUIRED 的 `fix_prompt` 原样交回原 task；下一次 run 是新 attempt，不创建修复 task，不释放 ownership。
5. 所有必需 task VERIFIED 后，按计划显式运行需要的 read-only ExpertRound。Optimizer 若无候选，记录摘要后进入 FINAL；若候选会改变已验证交付物，Leader评估价值并通过 plan amendment 注册新 optimization task，再回执行/审查循环。
6. Reviewer 独立 FINAL_VERIFY。`FINAL_VERIFY: VERIFIED` 只代表 Agent 证据完整。
7. Leader提交完成标准、证据、限制和手工入口，等待用户 HUMAN_ACCEPT；仅 ACCEPTED 才交付。

runtime 永不自动派下一节点。Leader也不自判 PASS，不改写 Reviewer 的 fix_prompt。

## 状态与锁

ExecutionTask 状态：`PENDING/READY/RUNNING/SUBMITTED/AUDITING/FIX_REQUIRED/BLOCKED/REPORT_INVALID/VERIFIED/CANCELED`。ownership 从 RUNNING 持有到 VERIFIED/CANCELED；审查、修复和恢复期间均不释放。依赖只在前置 VERIFIED 后 READY。

ReviewRound、ExpertRound 独立记录当前摘要、证据、请求与引用。TeamState 不保存完整历史正文，不建立 events/snapshot/mailbox/任务板第二状态机。

## 报告与恢复

每个成员最终正文后必须附单行 JSON envelope，格式见 protocol §3。缺失/损坏/越界时不从正文猜测，不自动重试；保留 child Session 正文与 ownership，通知 Leader选择显式恢复。

后台 completion 先持久化再发 compact delta；不轮询。`wait` 仅用于显式收集完整结果。

成员启动时启用 Pi 原生 auto-compaction；不设自定义阈值，不在 settled 后主动调用 compact。原生压缩或会话失败表现为 `ERROR/INTERRUPTED`，不自动重放；Leader按 TeamState/taskId/leader plan 和成员输出决定是否轮换接续，必要摘要由 Leader自行记录。

## 硬边界

- Reviewer 是唯一 VERIFIED/FIX_REQUIRED/FINAL_VERIFY 判定者；Coder self-report 不算验证。
- Reviewer/debugger/product/optimizer 不改交付物；optimizer 不直接落地候选。
- 同一并行批次成员互异、依赖已满足、owned paths 无相等或父子冲突。
- 新成员不得绕过 plan amendment；成员不得获得 `agent_team`。
- 两轮同根因无实质进展、外部/权限/预算/安全阻塞或合约变化时停问用户。
- 验证动作（测试、构建、typecheck、lint、doctor、浏览器、真实模型/压缩冒烟）已获用户全局授权，无需逐次确认；执行真实模型冒烟前向用户说明预期费用。仍需确认的：不可逆删除、新成员授权、plan amendment、修改 Pi 核心/全局配置、合约外范围。
- HUMAN_ACCEPT 不以 Agent 判定替代；用户的合约外反馈先新 USER_GATE。
