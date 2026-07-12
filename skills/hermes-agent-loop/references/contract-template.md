# Hermes Agent Loop state.md 模板

> 复制到 `state/<task-slug>/state.md`。父 Hermes 维护本文件与 `review.md`；maker 只读合约与 prompts。

## Contract

- 意图：
- 完成判定：
- 非目标：
- 假设 / 澄清：
- 计划来源：
- 停止护栏：
- executor mode：CC（默认）| HERMES | SELF
- maker_model: <model> | (config 默认)
- checker_model: <model> | (父 Hermes 内联)
- 角色边界：父 Hermes=编排+checker 不改交付物；唯一 maker 改主交付物
- prompt 契约：每 issue 独立 fix_prompt → review.md + SHA-256 → 原样发送
- 辅助 Agent：允许 delegate_task | 禁用（候选/边界/预算）
- 必须加载的技能：

## Steps

1. [名] - [动作 + 完成标准]
   - handoff: [产物 / diff / 验证命令]

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
- executor_mode: CC | HERMES | SELF
- maker_model:
- checker_model:
- maker_transport: claude_print | hermes_chat | direct_write
- maker_session:
- maker_generation: 0
- maker_status: UNSPAWNED | RUNNING | COMPLETED | INTERRUPTED | UNREACHABLE
- done:
- tried:
- next:
- open:
- user-confirm: 无 |
- cost:

## Evidence

- changed:
- commands:
- maker_calls:
- delegate_calls:
- prompt_forwarding: [issue id / SHA-256 / target session]
- review: `state/<task-slug>/review.md`
- appeal: `state/<task-slug>/appeal.md`（按需）
- inbox: `state/inbox.md`（按需）

## Recovery

读现存 state/review/appeal/inbox → **phase 路由与 maker 恢复见 `references/protocol.md` §7**。

本端 transport 摘要：

- 仅用本文件精确 `maker_session`；禁 `--continue` / 扫描最近 session。
- CC maker：`claude -p --resume <id>`。Hermes maker：`hermes chat -Q -q … --resume <id>`，每次更新 stderr `session_id:`。
- 不可恢复：UNREACHABLE + 升 generation + replacement；临时故障不立即替换。
- 禁 `-z` 续轮；禁 `delegate_task` 当 persistent maker。

## Baseline

<!-- VERIFY 后追加；不改交付物 -->

- locked_at:
- deliverable_paths:
- checklist_passed:
- evidence_paths:
- baseline_fingerprint:
- rollback_entry:
- baseline_status: deliverable

## Deliver

<!-- FINAL_VERIFY 后；session/过程文件等用户授权清理 -->

- executor_mode:
- maker_session:
- maker_generation:
- completed:
- why:
- verified_by: `state/<task-slug>/review.md`
- risks_or_limits:
- next:
