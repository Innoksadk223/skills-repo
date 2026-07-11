---
name: cc-agent-loop
description: "Use when a Claude Code task needs independent maker-checker review, evidence-backed verification, repeated correction, resumable audit state, issue-specific fix prompts, bounded optimization, or an explicit /agent-loop request. Keep the primary Claude Code session responsible for planning, changes, and delivery while one independent persistent audit session is reused across AUDIT, VERIFY, OPTIMIZE, and FINAL_VERIFY."
---

# CC Agent Loop

把执行与裁判分开。主 Claude Code 负责 PLAN、ACT、修正和交付；独立 audit CC session 负责判定、复验、为每个 issue 编写可直接执行的 `fix_prompt`，并控制优化分流。

## 加载与状态

先复用已有 Plan mode、`writing-plans` 或其它可执行计划。没有可用计划时先写最小合约。

1. 修改交付物前，把 `references/contract-template.md` 复制到 `state/<slug>/state.md`。
2. 向用户展示 goal、non-goals、assumptions、stop guardrails 和 checklist；必须取得显式确认。
3. 首次 AUDIT 前完整读取 `references/protocol.md`；后续阶段继续复用同一 audit session。

| 文件 | 所有者 | 用途 |
| --- | --- | --- |
| `state/<slug>/state.md` | 主 CC | 合约、进度、证据、audit session、恢复、基线、交付摘要 |
| `state/<slug>/review.md` | audit CC | AUDIT、fix prompts、appeal、VERIFY、OPTIMIZE、FINAL_VERIFY |
| `state/<slug>/appeal.md` | 主 CC | 可选的证据化申诉 |
| `state/inbox.md` | 主 CC | 可选的跨任务未决项 |

过程文件只负责路由，不能替代真实 diff、命令输出、日志或产物。

## 工作流

```text
PLAN → USER_GATE → ACT → OBSERVE → AUDIT
                                      │
                    CONTINUE_FIX ─────┤
                    ESCALATE_REPLAN ──┤
                    PROCEED_TO_VERIFY ▼
                                   VERIFY
                                      ▼
                               BASELINE_LOCK
                                      ▼
                  OPTIMIZE → AUDIT(re-verify)
                                      ▼
                              FINAL_VERIFY → DELIVER
```

每个环节完成后在 `state.md` 的 `loop_todo` 对应项打勾；`loop_todo` 是 `stage` 的可视化防漏，冲突时以 `stage` 为准。

1. **PLAN / USER_GATE**：锁定可检查的合约、handoff、预算和停止条件；未获用户明确确认不得 ACT。
2. **ACT / OBSERVE**：主 CC 只做已确认范围，并亲自记录实际文件、diff、日志和验证命令原始输出。
3. **AUDIT**：首次创建一个独立 `claude -p` audit session；先查 PLAN，再运行六 gate。
4. **LOOP**：audit CC 为每个 issue 产出独立 `fix_prompt`；主 CC 必须原样执行或 appeal，不得代写、弱化或合并掉约束。
5. **VERIFY**：同一 audit session 独立重跑 checklist 的验证命令。
6. **BASELINE_LOCK / OPTIMIZE**：主 CC 锁定 hash 与回滚入口；audit CC 先写 `optimize_todo`（四维度 + 已知候选逐条登记），再做四维扫描并逐项关闭 todo。只自动执行低风险、无新依赖、无需确认且收益不少于 5% 的 `OPTIMIZE_NOW`。
7. **FINAL_VERIFY / DELIVER**：同一 audit session 确认基线与停止理由；主 CC 再交付。

## Claude Code Session 生命周期

| 动作 | 调用 | 规则 |
| --- | --- | --- |
| 首次 AUDIT | `claude -p --session-id <uuid>` | 预分配 UUID，记录 `audit_session` 和 generation |
| 后续阶段 | `claude -p --resume <uuid>` | 始终恢复同一 audit session |
| 失效恢复 | 新 UUID + replacement audit | 仅原 session 确认不可恢复时替换；先关闭旧 issue |

- 使用显式 UUID；不要用 `--continue`、最近 session 或扫描本地 session 目录猜目标。
- 不要使用 `--no-session-persistence`；不要在 resume 时使用 `--fork-session`。
- 首次调用锁定完整 `--allowedTools`；resume 不得假设可以扩大工具权限。
- audit CC 只写 `review.md`。Claude Code 没有 per-file write sandbox；以 tool scope、prompt 和事后 diff 共同约束。

## 审查硬规则

- 保持 maker-checker split：主 CC 不得给自己的交付物判 PASS，audit CC 不得修改交付物。
- 每个阻塞 issue 必须有唯一 ID、证据、`fix_instruction` 和一段可直接执行的 `fix_prompt`；prompt 必含目标对象、问题证据、必改内容、禁止变化、验证命令和完成回报。
- `CLARIFIED` 必须由 audit CC 输出替换后的完整 prompt；主 CC 不得自行澄清。
- 第二轮及以后先关闭旧 issue，再重跑全部六 gate。
- 口头 PASS 视为 FAIL；每个结论必须指向文件、diff、命令输出、日志或产物。
- 把范围外建议放进 notes 或 `state/inbox.md`，不得伪装成阻塞项。
- 需要测试、lint、typecheck 或 build 时，ACT 记录输出，VERIFY 由 audit CC 独立重跑。
- 本技能允许主 CC 根据任务需要派出 auxiliary agent；只委派独立、有限、可验证的一次性任务，不让它参与 AUDIT / VERIFY、替代 audit CC 或并发修改重叠文件。

## 恢复与交付

先读 `state.md`、`review.md`、`appeal.md` 和 `state/inbox.md` 中实际存在的文件，再按 `references/protocol.md` 路由。

- `user-confirm` 非空、合约需变更、外部动作需授权或同类问题连续两轮无进展：停止并询问用户。
- audit session 可恢复：继续同一 UUID；不可恢复：记录 `UNREACHABLE`、递增 generation，创建 replacement audit。
- 不删除旧 verdict、fix prompt、session ID 或过程文件；只有用户能授权清理。
- 只有 `FINAL_VERIFY: VERIFIED` 才能交付；总结 changed、why、关键证据、风险和下一步。

精确 CLI 模板、六 gate、`fix_prompt` schema、appeal、优化和恢复分支见 `references/protocol.md`。
