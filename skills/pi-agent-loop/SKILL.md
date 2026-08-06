---
name: pi-agent-loop
description: "Use when a Pi task needs independent maker-checker review, evidence-backed verification, repeated correction, resumable audit state, issue-specific fix prompts, bounded optimization, or an explicit /agent-loop request. Keep the primary Pi session responsible for planning, changes, and delivery while one independent audit sub-agent is reused across AUDIT, VERIFY, OPTIMIZE, and FINAL_VERIFY."
---

# Pi Agent Loop

主 Pi：PLAN / ACT / 修正 / 交付。  
独立 audit 子 Agent：判定、复验、issue 级 `fix_prompt`、OPTIMIZE 分流。**勿自审交付物；audit 不改交付物。**

## 开卷（按阶段）

| 阶段 | 必读 |
| --- | --- |
| PLAN / USER_GATE | 本 SKILL + `references/contract-template.md` |
| 首次 AUDIT | + `protocol.md` §1–§2（契约 + AUDIT） |
| LOOP / Appeal | + `protocol.md` §3 |
| VERIFY | + `protocol.md` §4 |
| BASELINE / OPTIMIZE | + `protocol.md` §5 |
| FINAL / 恢复 / DELIVER | + `protocol.md` §6–§9 |

## 状态文件

| 文件 | 所有者 | 用途 |
| --- | --- | --- |
| `state/<slug>/state.md` | 主 Pi | 合约、证据、audit 状态、恢复、基线 |
| `state/<slug>/review.md` | audit | AUDIT/prompts/VERIFY/OPTIMIZE/FINAL |
| `state/<slug>/appeal.md` | 主 Pi | 可选申诉 |
| `state/inbox.md` | 主 Pi | 可选跨任务未决 |

进 ACT 前：复制 contract-template -> `state/<slug>/state.md`，展示 goal/non-goals/assumptions/stop/checklist，取得显式确认。过程文件不替代真实证据。

## 工作流

```text
PLAN -> USER_GATE -> ACT -> OBSERVE -> AUDIT
                                    │ CONTINUE_FIX / ESCALATE_REPLAN
                                    └-> VERIFY -> BASELINE_LOCK -> OPTIMIZE(必走)
                                         OPTIMIZE_NOW -> AUDIT -> VERIFY …
                                         无候选停止 -> FINAL_VERIFY -> DELIVER
```

`loop_todo` 防漏；冲突以 `stage` 为准。

1. **PLAN/USER_GATE**：锁合约；未确认不 ACT。  
2. **ACT/OBSERVE**：主 Pi 亲记缓存 diff/文件/日志/验证输出。  
3. **AUDIT**：独立 audit 子 Agent（同任务复用）；PLAN + 六 gate（protocol §2）。  
4. **LOOP**：主 Pi **原样**执行或 appeal，不改写 prompt。  
5. **VERIFY**：同一 audit 独立重跑 checklist。  
6. **BASELINE/OPTIMIZE**：锁 hash；四维 todo；仅低风险 gain≥5% 的 `OPTIMIZE_NOW` 自动执行；**默认启动，禁跳过**；改交付物后必须 AUDIT->VERIFY。  
7. **FINAL_VERIFY/DELIVER**：仅 VERIFIED 可交付。

## Audit 子 Agent

AUDIT / VERIFY / OPTIMIZE / FINAL_VERIFY 由独立 audit 子 Agent 执行：同任务复用、只写 `review.md`、不改交付物；不可用或上下文丢失时重新派发（保留 review.md 历史，先关旧 issue）。调用途径由主 Pi 执行时自定（原生 subagent / agent_team / 其它），本技能不规定具体机制。详见 protocol §1。

## 硬禁令

- 主 Pi 不自判 PASS；audit 不改交付物。  
- 阻塞 issue：ID+证据+fix_instruction+fix_prompt（目标/证据/必改/禁改/验证/回报）。  
- `CLARIFIED` 仅 audit 出完整 replacement。  
- 第 2+ 轮先关旧 issue 再六 gate；口头 PASS=FAIL。  
- 范围外 -> notes/inbox；enrichment 先问用户。  
- 测试/lint/build：ACT 记输出，VERIFY 由 audit 独立重跑。  
- **禁跳过 OPTIMIZE**：VERIFY 通过后必须进入 BASELINE_LOCK -> OPTIMIZE；无候选以 NO_CANDIDATE 停止不算跳过。  
- 辅助 agent：一次性可验证；不参与 AUDIT/VERIFY；禁重叠并发写。  
- 过程文件仅用户授权清理。

## 恢复与交付

读现存过程文件 -> protocol §7。user-confirm / 合约变更 / 外部授权 / 同类两轮无进展 -> 停问用户。  
仅 `FINAL_VERIFY: VERIFIED` 交付；总结 changed/why/证据/风险/下一步。

精：`references/protocol.md`。
