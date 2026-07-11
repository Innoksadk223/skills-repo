# CC Agent Loop state.md 模板

> 复制到 `state/<task-slug>/state.md`。主 CC 维护本文件；audit CC 读取它，并把 verdict 与 prompts 写入 `review.md`。

## Contract

- 意图：[用户真正要达成的结果，一句话]
- 完成判定：[可验证的命令、产物路径或二元 checklist]
- 非目标：[本轮明确不做什么]
- 假设 / 澄清：[已确认假设；待确认事项放到 user-confirm]
- 计划来源：[Plan mode / writing-plans / 本文件 / 其它]
- 停止护栏：[最大修正轮、时间或成本、低收益停止条件]
- 审查 Agent 作用域：[一个独立 persistent CC session；只写 review.md；跨阶段复用]
- prompt 契约：[每个 issue 由 audit CC 生成独立 fix_prompt；主 CC 原样执行或 appeal]
- 辅助 Agent：[允许按任务需要派出 | 禁用；写明候选子任务、写入边界、预算和回收条件]
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
- audit_session: [空 | 预分配的合法 UUID]
- audit_generation: 0
- audit_status: UNSPAWNED | RUNNING | COMPLETED | INTERRUPTED | UNREACHABLE
- audit_transport: [空 | direct_write | primary_verbatim]
- audit_response_sha256: [空 | primary_verbatim 内容 hash]
- done: [已有证据的完成事项]
- tried: [尝试、失败原因、appeal、replacement 原因]
- next: [下一步可执行动作]
- open: [未解决 issue、阻塞、风险]
- user-confirm: [需要用户明确确认的事项；没有写“无”]
- cost: [耗时、audit / auxiliary 调用、修正轮、继续价值、停止原因]

## Evidence

- changed: [路径 / diff 摘要 / 产物]
- commands: [精确命令 + 原始输出或日志路径]
- audit_calls: [首次调用 / resume 的 UUID、phase、exit 与输出位置]
- auxiliary_calls: [handoff、agent handle / session、结果、主 CC 的独立验证]
- review: `state/<task-slug>/review.md`
- appeal: `state/<task-slug>/appeal.md`（仅需要时创建）
- inbox: `state/inbox.md`（仅有跨任务未决项时使用）

## Recovery

先读取本文件、`review.md`、`appeal.md` 和 `state/inbox.md` 中实际存在的文件。

### Audit session

- 对 `audit_session` 使用 `claude -p --resume <uuid>`；不要使用 `--continue` 或扫描最近 session。
- session 可恢复：继续同一 UUID；不要 `--fork-session`。
- session 明确不可恢复：标记 `UNREACHABLE`，保留旧 UUID，递增 `audit_generation`，生成 replacement audit；让它先核对旧 issue closure。
- provider、认证或 quota 临时故障不是立即 replacement 的理由。

### Phase

- `user-confirm` 非空：先问用户。
- pending appeal：同一 audit session 裁决。
- 最新 AUDIT 为 `CONTINUE_FIX`：主 CC 按 execution order 原样执行 fix prompts。
- 最新 AUDIT 为 `ESCALATE_REPLAN`：先向用户提交合约更新。
- 最新 AUDIT 为 `PROCEED_TO_VERIFY`：同一 audit session 进入 VERIFY。
- 最新 VERIFY 为 `RETURN_TO_LOOP`：按新 fix prompt 修正。
- 最新 VERIFY 为 `VERIFIED` 且无 Baseline：BASELINE_LOCK。
- Baseline 已写且 OPTIMIZE 未开始：同一 audit session 进入 OPTIMIZE。
- OPTIMIZE_NOW 已执行但未复验：回到 AUDIT。
- 优化停止或无候选：FINAL_VERIFY。
- 最新 FINAL_VERIFY 为 `VERIFIED`：DELIVER。
- blocker、预算上限、appeal deadlock 或低价值继续：停止并汇报。

## Baseline

<!-- VERIFY 通过后由主 CC 追加；不得改变交付物。 -->

- locked_at:
- deliverable_paths:
- checklist_passed:
- evidence_paths:
- baseline_fingerprint: [file list + hash / patch hash / snapshot id]
- rollback_entry: [restore command / patch path / snapshot path]
- baseline_status: deliverable

## Deliver

<!-- FINAL_VERIFY 通过后追加。session 与过程文件等待用户授权清理。 -->

- audit_session:
- audit_generation:
- completed:
- why:
- verified_by: `state/<task-slug>/review.md`
- risks_or_limits:
- next:
