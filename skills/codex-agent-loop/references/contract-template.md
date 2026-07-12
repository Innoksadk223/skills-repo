# Codex Agent Loop state.md 模板

> 复制到 `state/<task-slug>/state.md`。主 Codex 维护本文件；审查 agent 写 `review.md`。

## Contract

- 意图：
- 完成判定：
- 非目标：
- 假设 / 澄清：
- 计划来源：
- 停止护栏：
- 审查 Agent 作用域：一个 native reviewer；只写 review.md；fork_turns=none 首次；跨阶段复用
- prompt 契约：reviewer 出 fix_prompt；主 Codex 原样执行或 appeal
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
- audit_task:
- audit_agent_id: UNAVAILABLE |
- audit_generation: 0
- audit_status:
- audit_transport: | direct_write | primary_verbatim
- done:
- tried:
- next:
- open:
- user-confirm: 无 |
- cost:

## Evidence

- changed:
- commands:
- agent_calls:
- auxiliary_calls:
- review: `state/<task-slug>/review.md`
- appeal: `state/<task-slug>/appeal.md`（按需）
- inbox: `state/inbox.md`（按需）

## Recovery

读现存过程文件 → **handle 与 phase 路由见 `references/protocol.md` §9**。

本端摘要：

- 用 `audit_task` prefix 调 `list_agents`；禁扫 `~/.codex/sessions/`。
- idle → `followup_task`；RUNNING → 等待/`send_message`。
- 不可达：UNREACHABLE + 升 generation + replacement（`fork_turns=none`）；先关旧 issue。

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

<!-- FINAL 后；handle/过程文件等用户授权清理 -->

- audit_task:
- audit_agent_id:
- audit_generation:
- completed:
- why:
- verified_by: `state/<task-slug>/review.md`
- risks_or_limits:
- next:
