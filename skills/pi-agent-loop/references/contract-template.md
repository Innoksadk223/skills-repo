# Pi Agent Loop state.md 模板

> 复制到 `state/<task-slug>/state.md`。主 Pi 维护本文件；audit 写 `review.md`。

## Contract

- 意图：
- 完成判定：
- 非目标：
- 假设 / 澄清：
- 计划来源：
- 停止护栏：
- audit 子 Agent：独立、同任务复用、途径自定；只写 review.md；不可用则重新派发
- prompt 契约：audit 出 fix_prompt；主 Pi 原样执行或 appeal
- 辅助 Agent：允许 | 禁用（候选/边界/预算）
- 必须加载的技能：

## Steps

1. [名] - [动作 + 完成标准]
   - handoff:

## Checklist

- [ ] [二元标准] - evidence:

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
- audit: 可用 | 需重新派发（保留 review.md 历史）
- done:
- tried:
- next:
- open:
- user-confirm: 无 |
- cost:

## Evidence

- changed:
- commands:
- audit_calls:
- auxiliary_calls:
- review: `state/<task-slug>/review.md`
- appeal: `state/<task-slug>/appeal.md`（按需）
- inbox: `state/inbox.md`（按需）

## Recovery

读现存过程文件 -> **stage 与恢复路由见 `references/protocol.md` §7**。

本端摘要：

- audit 子 Agent 不可用/上下文丢失 -> 重新派发；交 state/完整 review/appeal/未决 issue，先关旧 issue。
- 临时故障不立即替换；保留 review.md 历史。

## Baseline

<!-- VERIFY 后；不改交付物 -->

- locked_at:
- deliverable_paths:
- checklist_passed:
- evidence_paths:
- baseline_fingerprint:
- rollback_entry:
- baseline_status: deliverable

## Deliver

<!-- FINAL 后；session/过程文件等用户授权清理 -->

- completed:
- why:
- verified_by: `state/<task-slug>/review.md`
- risks_or_limits:
- next:
