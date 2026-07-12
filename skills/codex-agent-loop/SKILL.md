---
name: codex-agent-loop
description: "Use when a Codex task needs independent maker-checker review, evidence-backed verification, issue-specific fix prompts, repeated correction, resumable review state, bounded optimization, or an explicit /agent-loop request. Keep the primary Codex responsible for planning, changes, and delivery while one native audit subagent is reused across AUDIT, VERIFY, OPTIMIZE, and FINAL_VERIFY."
---

# Codex Agent Loop

主 Codex：PLAN / ACT / 修正 / 交付。  
独立 native 审查 agent：判定、复验、`fix_prompt`、OPTIMIZE 分流。  
**当前根任务内 multi-agent 工作流**；child 不是独立 CLI session。产出方不自判 PASS。

## 开卷（按阶段）

| 阶段 | 必读 |
| --- | --- |
| PLAN / USER_GATE | 本 SKILL + `references/contract-template.md` |
| 首次 AUDIT | + `protocol.md` §1–§4（工具契约 + spawn + AUDIT） |
| LOOP / Appeal | + `protocol.md` §5 |
| VERIFY | + `protocol.md` §6 |
| BASELINE / OPTIMIZE | + `protocol.md` §7 |
| FINAL / 恢复 / DELIVER | + `protocol.md` §8–§11 |

## 状态文件

| 文件 | 所有者 | 用途 |
| --- | --- | --- |
| `state/<slug>/state.md` | 主 Codex | 合约、证据、agent handle、恢复、基线 |
| `state/<slug>/review.md` | 审查 agent | AUDIT / VERIFY / OPTIMIZE / FINAL |
| `state/<slug>/appeal.md` | 主 Codex | 可选申诉 |
| `state/inbox.md` | 主 Codex | 可选跨任务未决 |

进 ACT 前：复制 contract-template → state，展示并确认。过程文件 ≠ 真实证据。

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
2. **ACT/OBSERVE**：主 Codex 亲读 diff/文件/日志/命令输出。  
3. **AUDIT**：唯一 reviewer，`fork_turns="none"`；写 review.md（protocol §4）。  
4. **LOOP**：原样执行 fix_prompt 或 appeal。  
5. **VERIFY**：同一 reviewer 独立重跑 checklist。  
6. **BASELINE/OPTIMIZE**：主 Codex 锁 hash；reviewer 四维 todo；`OPTIMIZE_NOW` 后 **AUDIT→VERIFY**；enrichment 先问用户。  
7. **FINAL_VERIFY/DELIVER**：仅 VERIFIED 可交付。

## 原生 Agent 要点

| 动作 | 工具 |
| --- | --- |
| 创建 reviewer | `spawn_agent`（只一次；记 canonical task name） |
| 下一阶段（idle） | `followup_task` |
| 运行中纠偏 | `send_message` |
| 等待 | `wait_agent`（通知≠证据） |
| 查询 | `list_agents` |
| 中断 | `interrupt_agent`（仍可 followup） |

直接调 agent 工具；勿包进 shell/`functions.exec`。勿每阶段新建 reviewer；勿用 `create_thread`/`fork_thread`/`codex exec resume`/`--last`/扫描 `~/.codex/sessions/` 管 child。  
共享工作区：主 Codex 写交付物；reviewer 写 review.md；禁并发同文件。`wait` 后**亲自读** review.md。详见 protocol §1–§3。

## 硬禁令

- 产出方不自判 PASS。  
- reviewer 只写 review.md；若只能返回块 → `primary_verbatim` + hash，主 Codex 不改写。  
- 勿假定 custom `sandbox_mode` 覆盖父任务 live 权限。  
- 六 gate + issue 级 fix_prompt（PROMPT_BLOCK 见 protocol §1）；第 2+ 轮先关旧 issue。  
- `CLARIFIED` 仅 reviewer 出完整 replacement。  
- 口头 PASS=FAIL；范围外 → notes/inbox。  
- 辅助 agent：一次性；不参与 AUDIT/VERIFY；禁重叠并发写。  
- handle/过程文件仅用户授权清理。

## 恢复与交付

读过程文件 → protocol §9。同根任务用 `audit_task` prefix 调 list_agents；不可达则升 generation + replacement，先关旧 issue。  
仅 `FINAL_VERIFY: VERIFIED` 交付。

精：`references/protocol.md`。
