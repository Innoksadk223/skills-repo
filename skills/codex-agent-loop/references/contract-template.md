# Codex Agent Loop state.md 模板

> 复制到 `state/<task-slug>/state.md`。主 Codex 维护本文件；审查 agent 读取它，但把审查结论写入 `review.md`。

## Contract

- 意图：[用户真正要达成的结果，一句话]
- 完成判定：[可验证的结束条件：命令、产物路径或二元 checklist]
- 非目标：[本轮明确不做什么]
- 假设 / 澄清：[已确认假设；待确认事项放到 user-confirm]
- 计划来源：[Plan mode / writing-plans / 本文件 / 其它]
- 停止护栏：[最大修正轮、时间或成本、低收益停止条件]
- 审查 Agent 作用域：[一个原生 child agent；fork_turns=none；只写 review.md；跨阶段复用]
- prompt 契约：[每个 issue 由 reviewer 生成独立 fix_prompt；主 Codex 原样执行或 appeal]
- 辅助 Agent：[允许按任务需要派出 | 禁用；写明候选子任务、写入边界、预算和回收条件]
- 必须加载的技能：[ACT 前必须完整读取的技能]

## Steps

1. [步骤名] - [做什么 + 完成标准]
   - handoff: [产物路径 / diff / 验证命令]

## Checklist

- [ ] [二元标准] - evidence: [文件路径 / 命令输出 / 产物路径]

## Progress

- round: 0
- stage: PLAN | USER_GATE | ACT | OBSERVE | AUDIT | LOOP | ESCALATE_REPLAN | VERIFY | BASELINE_LOCK | OPTIMIZE | FINAL_VERIFY | DELIVER
- loop_todo:
  - [ ] PLAN
  - [ ] USER_GATE
  - [ ] ACT
  - [ ] OBSERVE
  - [ ] AUDIT
  - [ ] VERIFY
  - [ ] BASELINE_LOCK
  - [ ] OPTIMIZE
  - [ ] FINAL_VERIFY
  - [ ] DELIVER
- audit_task: [空 | spawn_agent 返回的 canonical task name；必填且作为默认 target]
- audit_agent_id: [UNAVAILABLE | host 实际返回的独立 agent ID]
- audit_generation: 0
- audit_status: [UNSPAWNED | 原样记录 list_agents 返回的 host status | INTERRUPTED | UNREACHABLE]
- audit_transport: [空 | direct_write | primary_verbatim + SHA-256]
- done: [已有证据的完成事项]
- tried: [尝试、失败原因、appeal 结果、replacement 原因]
- next: [下一步可执行动作]
- open: [未解决 issue、阻塞、风险]
- user-confirm: [需要用户明确确认的取舍或外部动作；没有写“无”]
- cost: [耗时、工具与 agent 调用、修正轮、继续价值、停止原因]

## Evidence

- changed: [文件路径 / diff 摘要 / 产物路径]
- commands: [精确命令 + 原始输出或日志路径]
- agent_calls: [spawn / followup / message / wait / interrupt 的目标与结果]
- prompt_forwarding: [issue ID、review.md 中的原始 prompt、SHA-256、执行顺序]
- review: `state/<task-slug>/review.md`
- appeal: `state/<task-slug>/appeal.md`（仅需要时创建）
- inbox: `state/inbox.md`（仅有跨任务未决项时使用）

## Recovery

先读取本文件、`review.md`、`appeal.md` 和 `state/inbox.md` 中实际存在的文件。

### Agent handle

- 只用 `audit_task` 的 canonical prefix 调用 `list_agents`，不要扫描 `~/.codex/sessions/`；`audit_agent_id` 未返回时写 `UNAVAILABLE`，不得猜测或阻塞续跑。
- handle 可达且 RUNNING：等待或用 `send_message` 补充证据。
- handle 可达且无进行中 turn（如 IDLE / DONE / COMPLETED）：用 `followup_task` 进入下一阶段。
- handle 已 INTERRUPTED：记录原因，再决定续跑或升级。
- handle 不可达：标记 `UNREACHABLE`，保留旧记录，递增 `audit_generation`，用 `fork_turns="none"` 生成 replacement reviewer；让它从过程文件恢复并先关闭旧 issue。

### Phase

- `user-confirm` 非空：先问用户。
- pending appeal：同一 reviewer 裁决。
- `next` 是未完成修正或最新 AUDIT 为 `CONTINUE_FIX`：主 Codex 进入 ACT / LOOP。
- 最新 AUDIT 为 `ESCALATE_REPLAN`：先向用户提交合约更新；确认前不改交付物。
- 最新 AUDIT 为 `PROCEED_TO_VERIFY`：同一 reviewer 进入 VERIFY。
- 最新 VERIFY 为 `RETURN_TO_LOOP`：主 Codex 修正。
- 最新 VERIFY 为 `VERIFIED` 且无 Baseline：进入 BASELINE_LOCK。
- Baseline 已写且 OPTIMIZE 未开始：同一 reviewer 进入 OPTIMIZE。
- OPTIMIZE_NOW 已执行但未复验：回到 AUDIT。
- 优化停止或无候选：进入 FINAL_VERIFY。
- 最新 FINAL_VERIFY 为 `VERIFIED`：进入 DELIVER。
- blocker、硬上限、appeal deadlock 或低价值继续：停止并汇报。

## Baseline

<!-- VERIFY 通过后由主 Codex 追加；不得改变交付物。 -->

- locked_at:
- deliverable_paths:
- checklist_passed:
- evidence_paths:
- baseline_fingerprint: [file list + hash / patch hash / snapshot id]
- rollback_entry: [restore command / patch path / snapshot path]
- baseline_status: deliverable

## Deliver

<!-- FINAL_VERIFY 通过后追加。agent handle 与过程文件等待用户授权清理。 -->

- audit_agent_id:
- audit_task:
- audit_generation:
- completed:
- why:
- verified_by: `state/<task-slug>/review.md`
- risks_or_limits:
- next:
