---
name: cc-agent-loop
description: "Use when a Claude Code task needs independent maker-checker review, evidence-backed verification, repeated correction, resumable audit state, issue-specific fix prompts, bounded optimization, or an explicit /agent-loop request. Keep the primary Claude Code session responsible for planning, changes, and delivery while one independent persistent audit session is reused across AUDIT, VERIFY, OPTIMIZE, and FINAL_VERIFY."
---

# CC Agent Loop

主 CC：PLAN / ACT / 修正 / 交付。  
独立 persistent audit CC：判定、复验、issue 级 `fix_prompt`、OPTIMIZE 分流。**勿自审交付物；audit 不改交付物。**

## 开卷（按阶段）

| 阶段 | 必读 |
| --- | --- |
| PLAN / USER_GATE | 本 SKILL + `references/contract-template.md` |
| 首次 AUDIT | + `protocol.md` §1–§3（session 契约 + AUDIT） |
| LOOP / Appeal | + `protocol.md` §4 |
| VERIFY | + `protocol.md` §5 |
| BASELINE / OPTIMIZE | + `protocol.md` §6 |
| FINAL / 恢复 / DELIVER | + `protocol.md` §7–§10 |

## 状态文件

| 文件 | 所有者 | 用途 |
| --- | --- | --- |
| `state/<slug>/state.md` | 主 CC | 合约、证据、audit session、恢复、基线 |
| `state/<slug>/review.md` | audit CC | AUDIT/prompts/VERIFY/OPTIMIZE/FINAL |
| `state/<slug>/appeal.md` | 主 CC | 可选申诉 |
| `state/inbox.md` | 主 CC | 可选跨任务未决 |

进 ACT 前：复制 contract-template → `state/<slug>/state.md`，展示 goal/non-goals/assumptions/stop/checklist，取得显式确认。过程文件不替代真实证据。

## 工作流

```text
PLAN → USER_GATE → ACT → OBSERVE → AUDIT
                                    │ CONTINUE_FIX / ESCALATE_REPLAN
                                    └→ VERIFY → BASELINE_LOCK → OPTIMIZE
                                         OPTIMIZE_NOW → AUDIT → VERIFY …
                                         无改动停止 → FINAL_VERIFY → DELIVER
```

`loop_todo` 防漏；冲突以 `stage` 为准。

1. **PLAN/USER_GATE**：锁合约；未确认不 ACT。  
2. **ACT/OBSERVE**：主 CC 亲记缓存 diff/文件/日志/验证输出。  
3. **AUDIT**：独立 `claude -p` session；PLAN + 六 gate（protocol §3）。  
4. **LOOP**：主 CC **原样**执行或 appeal，不改写 prompt。  
5. **VERIFY**：同一 audit 独立重跑 checklist。  
6. **BASELINE/OPTIMIZE**：锁 hash；四维 todo；仅低风险 gain≥5% 的 `OPTIMIZE_NOW` 自动执行；**改交付物后必须 AUDIT→VERIFY**。  
7. **FINAL_VERIFY/DELIVER**：仅 VERIFIED 可交付。

## Audit Session 要点

| 动作 | 调用 |
| --- | --- |
| 首次 | `claude -p --session-id <uuid>`（预分配并写入 state） |
| 后续 | `claude -p --resume <uuid>` |
| 失效 | 新 UUID + replacement；先关旧 issue |

禁：`--continue` / 猜最近 session / `--no-session-persistence` / resume 时 `--fork-session`。  
首次锁定 `--allowedTools`。audit 只写 `review.md`。详见 protocol §1–§2。

## 硬禁令

- 主 CC 不自判 PASS；audit 不改交付物。  
- 阻塞 issue：ID+证据+fix_instruction+fix_prompt（目标/证据/必改/禁改/验证/回报）。  
- `CLARIFIED` 仅 audit 出完整 replacement。  
- 第 2+ 轮先关旧 issue 再六 gate；口头 PASS=FAIL。  
- 范围外 → notes/inbox；enrichment 先问用户。  
- 测试/lint/build：ACT 记输出，VERIFY 由 audit 独立重跑。  
- 辅助 agent：一次性可验证；不参与 AUDIT/VERIFY；禁重叠并发写。  
- 过程文件/session 仅用户授权清理。

## 恢复与交付

读现存过程文件 → protocol §8。user-confirm / 合约变更 / 外部授权 / 同类两轮无进展 → 停问用户。  
仅 `FINAL_VERIFY: VERIFIED` 交付；总结 changed/why/证据/风险/下一步。

精：`references/protocol.md`。
