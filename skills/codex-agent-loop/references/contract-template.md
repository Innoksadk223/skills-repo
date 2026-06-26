# Codex Agent Loop state.md 模板

> 复制到 `state/[task-slug]/state.md`。主 Codex 唯一必写状态文件；审查 Codex 只读它，不在其中写审查结论。

## Contract

- 意图：[用户真正要达成的结果，一句话]
- 完成判定：[可验证的结束条件，如命令、产物路径、检查清单]
- 非目标：[本轮不做什么，防止范围扩张]
- 假设 / 澄清：[已知假设；需要用户确认的事项写到 User Confirm]
- 计划来源：[Plan mode / writing-plans / 本文件]
- 停止护栏：[最大修正轮数、预算、低收益停止条件]
- 审查 Agent 作用域：[独立 Codex 审查进程；启动时写入 `audit_session`，任务结束时清除]
- 必须加载的技能：[ACT 阶段前必须加载的技能列表]

## Steps

1. [步骤名] - [做什么 + 做到什么程度]
   - handoff: [产物路径 / diff 摘要 / 验证命令]

## Checklist

- [ ] [二元标准] - evidence: [文件路径 / 命令输出 / 产物路径]

## Progress

- round: [N]
- stage: PLAN | USER_GATE | ACT | AUDIT | LOOP | ESCALATE_REPLAN | VERIFY | BASELINE_LOCK | OPTIMIZE_LOOP | FINAL_VERIFY | DELIVER
- audit_session: [空 | Codex session ID；AUDIT 启动时写入，DELIVER 时清除]
- codex_session: [空 | 主 Codex session ID；ACT 启动时写入，DELIVER 时清除；用于执行中断恢复]
- done: [已经完成且有证据的事项]
- tried: [尝试过的方案 / 失败原因 / 上诉结果]
- next: [下一步动作或停止后的建议]
- open: [未解决问题 / 阻塞 / 风险]
- user-confirm: [需要用户确认的取舍或外部动作；没有写"无"]
- cost: [耗时 / 工具或 agent 调用 / 是否值得继续 / 停止原因]

## Evidence

- changed: [文件路径 / diff 摘要 / 产物路径]
- commands: [命令及关键输出]
- review: `state/[task-slug]/review.md`
- inbox: `state/inbox.md`（仅有未决事项时创建）

## Recovery

- `user-confirm` 非空：先问用户。
- `review.md` 有 pending appeal：恢复同一审查 Codex 裁决。
- `next` 指向未完成修正：继续 ACT，必要时先更新 Contract。
- `review.md` 最后 AUDIT 为 `ESCALATE_REPLAN`：主 Codex 更新 Contract（重新分解步骤、调整范围），然后重新进入 ACT。连续两次 `ESCALATE_REPLAN` 无进展：升级到 USER_GATE。
- `review.md` 最后 AUDIT 为 `PROCEED_TO_VERIFY`：同一审查 Codex 进入 VERIFY。
- `review.md` 最后 VERIFY 为 `VERIFIED` 且本文件无 Baseline：进入 BASELINE_LOCK。
- Baseline 已写且优化未终止：进入 OPTIMIZE_LOOP。
- `review.md` 最后 FINAL_VERIFY 为 `VERIFIED`：进入 DELIVER。
- blocker、硬上限、上诉死锁或低收益：停止并汇报。

## Baseline

<!-- VERIFY 通过后由主 Agent 追加；不得改变交付物 -->

- locked_at:
- deliverable_paths:
- checklist_passed:
- evidence_paths:
- baseline_fingerprint: [file list + hash / saved patch hash / snapshot id]
- rollback_entry: [restore command / saved patch path / snapshot path]
- baseline_status: deliverable

## Deliver

<!-- FINAL_VERIFY 通过后由主 Agent 追加摘要，清除 `audit_session`，随后清理过程文件 -->

- audit_session: [清除]
- completed:
- why:
- verified_by: `state/[task-slug]/review.md`
- risks_or_limits:
- next:
