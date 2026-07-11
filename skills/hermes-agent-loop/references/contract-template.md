# Hermes Agent Loop state.md 模板

> 复制到 `state/<task-slug>/state.md`。父 Hermes 同时维护本文件与 `review.md`；maker 读取合约和 prompts，但不写审查结论。

## Contract

- 意图：[用户真正要达成的结果，一句话]
- 完成判定：[可验证的命令、产物路径或二元 checklist]
- 非目标：[本轮明确不做什么]
- 假设 / 澄清：[已确认假设；待确认事项放到 user-confirm]
- 计划来源：[已有计划 / writing-plans / 本文件 / 其它]
- 停止护栏：[最大修正轮、时间或成本、低收益停止条件]
- executor mode：[CC（默认）| HERMES（仅用户在 PLAN 明确要求时）]
- 角色边界：[父 Hermes 编排并担任 checker，但不修改交付物；唯一 persistent maker 负责主交付物变更与整合]
- prompt 契约：[父 Hermes 为每个 issue 生成独立 fix_prompt，写入 review.md、记录 SHA-256 后原样发送给 maker]
- 辅助 Agent：[允许父 Hermes 按任务需要使用 delegate_task | 禁用；写明候选子任务、写入边界、预算和回收条件]
- 必须加载的技能：[ACT 前必须完整读取的技能]

## Steps

1. [步骤名] - [动作 + 完成标准]
   - handoff: [产物路径 / diff / 验证命令]

## Checklist

- [ ] [二元标准] - evidence: [路径 / 命令输出 / 产物]

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
- executor_mode: CC | HERMES
- maker_transport: claude_print | hermes_chat
- maker_session: [空 | CC UUID | Hermes session ID]
- maker_generation: 0
- maker_status: UNSPAWNED | RUNNING | COMPLETED | INTERRUPTED | UNREACHABLE
- done: [已有证据的完成事项]
- tried: [尝试、失败原因、appeal、replacement 原因]
- next: [下一步可执行动作]
- open: [未解决 issue、阻塞、风险]
- user-confirm: [需要用户明确确认的事项；没有写“无”]
- cost: [耗时、maker 与辅助 agent 调用、修正轮、继续价值、停止原因]

## Evidence

- changed: [路径 / diff 摘要 / 产物]
- commands: [精确命令 + 原始输出或日志路径]
- maker_calls: [generation、首次调用或 resume、exit、输出位置]
- delegate_calls: [handoff、task handle、结果、父 Hermes 的独立验证]
- prompt_forwarding: [issue ID、review.md 中的原始 prompt、SHA-256、目标 maker session]
- review: `state/<task-slug>/review.md`
- appeal: `state/<task-slug>/appeal.md`（仅 maker 或用户提交反证时创建）
- inbox: `state/inbox.md`（仅有跨任务未决项时使用）

## Recovery

先读取本文件、`review.md`、`appeal.md` 和 `state/inbox.md` 中实际存在的文件。

### Maker session

- 只使用本文件中的精确 `maker_session`；不要使用 `--continue`、最近 session 或扫描 session 列表猜目标。
- CC maker：使用 `claude -p --resume <maker_session>`。
- Hermes maker：使用 `hermes chat -Q -q "<prompt>" --resume <maker_session>`；每次从 stderr 的精确 `session_id:` 行重新捕获并更新 ID。
- maker 不可恢复：标记 `UNREACHABLE`，保留旧 ID，递增 `maker_generation`，再创建 replacement maker。
- provider、认证或 quota 的临时故障不是立即 replacement 的理由。
- 禁止用 `-z` one-shot 路径恢复，也不要用 `delegate_task` 充当 persistent maker。

### Phase

- `user-confirm` 非空：先问用户。
- pending appeal：父 Hermes 作为 checker 根据反证裁决；`CLARIFIED` 时写完整 replacement prompt。
- 最新 AUDIT 为 `CONTINUE_FIX`：父 Hermes 按 execution order 原样发送 fix prompts 给 maker。
- 最新 AUDIT 为 `ESCALATE_REPLAN`：先向用户提交合约更新；确认前不改交付物。
- 最新 AUDIT 为 `PROCEED_TO_VERIFY`：父 Hermes 进入 VERIFY。
- 最新 VERIFY 为 `RETURN_TO_LOOP`：原样发送新 fix prompt。
- 最新 VERIFY 为 `VERIFIED` 且无 Baseline：进入 BASELINE_LOCK。
- Baseline 已写且 OPTIMIZE 未开始：父 Hermes 进入 OPTIMIZE。
- OPTIMIZE_NOW 已执行但未复验：父 Hermes 回到 AUDIT。
- 优化停止或无候选：进入 FINAL_VERIFY。
- 最新 FINAL_VERIFY 为 `VERIFIED`：进入 DELIVER。
- blocker、预算上限、appeal deadlock 或低价值继续：停止并汇报。

## Baseline

<!-- VERIFY 通过后由父 Hermes 追加；不得改变交付物。 -->

- locked_at:
- deliverable_paths:
- checklist_passed:
- evidence_paths:
- baseline_fingerprint: [file list + hash / patch hash / snapshot id]
- rollback_entry: [restore command / patch path / snapshot path]
- baseline_status: deliverable

## Deliver

<!-- FINAL_VERIFY 通过后追加。maker session 与过程文件等待用户授权清理。 -->

- executor_mode:
- maker_session:
- maker_generation:
- completed:
- why:
- verified_by: `state/<task-slug>/review.md`
- risks_or_limits:
- next:
