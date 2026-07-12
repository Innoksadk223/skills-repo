---
name: hermes-agent-loop
description: "Use when a Hermes-orchestrated task needs maker-checker review, evidence-backed verification, issue-specific fix prompts, repeated correction, resumable maker state, bounded optimization, or an explicit /agent-loop request. Keep the parent Hermes responsible for orchestration and checking while one persistent CC or Hermes maker session changes deliverables; allow bounded delegate_task auxiliaries when the task benefits."
---

# Hermes Agent Loop

父 Hermes：PLAN→DELIVER 编排与审查，**不改交付物**。唯一 maker：ACT/LOOP/OPTIMIZE_NOW。`delegate_task` 一次性、不替代角色。

## 模式

| 模式 | Maker | Checker |
| --- | --- | --- |
| CC（默认） | `claude -p` 持久 | 父 Hermes |
| Hermes（PLAN 要求） | `hermes chat` 持久 | 父 Hermes |
| Self（低风险文档/skill） | 父 Hermes 直写 | 后置命令证据；或独立 Hermes checker |

## 开卷

| 阶段 | 必读 |
| --- | --- |
| PLAN/USER_GATE | 本 SKILL + `contract-template.md` |
| ACT | + `*-executor-mode.md`（self 可跳） |
| AUDIT/LOOP | + `protocol.md` §1–3 |
| VERIFY | + §4 |
| BASELINE/OPTIMIZE | + §5 |
| FINAL/恢复 | + §6–9 |

## 状态

| 文件 | 用途 |
| --- | --- |
| `state/<slug>/state.md` | 合约/证据/session |
| `state/<slug>/review.md` | verdict/prompts |
| `appeal.md` / `state/inbox.md` | 反证 / 跨任务 |

ACT 前：复制 template → state，用户确认。

## 工作流

```text
PLAN → USER_GATE → ACT → OBSERVE → AUDIT
  CONTINUE_FIX|ESCALATE → … | PROCEED → VERIFY → BASELINE → OPTIMIZE
  OPTIMIZE_NOW → AUDIT → VERIFY … | 无改动 → FINAL_VERIFY → DELIVER
```

`loop_todo` 防漏；冲突以 `stage` 为准。主链 PLAN→DELIVER。

- ACT/OBSERVE：亲读证据，不采信自述  
- AUDIT：六 gate + fix_prompt（§2）  
- LOOP：review 记 SHA 后原样转发  
- VERIFY：独立重跑 checklist  
- OPTIMIZE：四维；`OPTIMIZE_NOW` 后必 AUDIT→VERIFY  
- DELIVER：仅 FINAL VERIFIED  

## 硬禁令

- 不自审交付物；checker 不改交付物；禁口头 PASS  
- issue：ID+证据+instruction+`fix_prompt`(目标/证据/必改/禁改/验证/回报)  
- 禁传输弱化/合并 prompt；`CLARIFIED`=完整 replacement  
- 同 class 两轮→ESCALATE；合约变更→USER_GATE  
- enrichment 只 SUGGEST_TO_USER；范围外→inbox  
- 禁 `--continue`/猜 session；Hermes maker 禁 `-z` 续；禁 delegate 当 maker  
- session/过程文件仅用户清  

## Transport / 恢复

- CC：`--session-id`→`--resume`（`cc-executor-mode.md`）  
- Hermes：`hermes chat -Q -q` + stderr `session_id:`（`hermes-executor-mode.md`）  
- 恢复：过程文件 + protocol §7  
