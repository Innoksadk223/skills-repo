# CC Agent Loop state.md 模板

> 复制到 `state/<task-slug>/state.md`。主 CC 维护本文件；audit 写 `review.md`。

## Contract

- 意图：
- 完成判定：
- 非目标：
- 假设 / 澄清：
- 计划来源：
- 停止护栏：
- 审查 Agent 作用域：一个独立 persistent CC session；只写 review.md；跨阶段复用
- prompt 契约：audit 出 fix_prompt；主 CC 原样执行或 appeal
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
- audit_session:
- audit_generation: 0
- audit_status: UNSPAWNED | RUNNING | COMPLETED | INTERRUPTED | UNREACHABLE
- audit_transport: | direct_write | primary_verbatim
- audit_response_sha256:
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

读现存过程文件 → **phase 与 session 路由见 `references/protocol.md` §8**。

本端摘要：

- resume 精确 UUID；禁 `--continue` / 猜最近 session / `--fork-session`。
- 不可恢复：UNREACHABLE + 升 generation + replacement；先关旧 issue。
- 临时故障不立即替换。

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

- audit_session:
- audit_generation:
- completed:
- why:
- verified_by: `state/<task-slug>/review.md`
- risks_or_limits:
- next:
