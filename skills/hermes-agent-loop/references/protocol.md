# Hermes Agent Loop Protocol

按阶段读取对应节（见 SKILL 开卷表）。定义 checker 边界、prompts、AUDIT/VERIFY/OPTIMIZE/FINAL、appeal、恢复。CLI transport 见 executor-mode references。

## 目录

1. 角色与状态 · 2. AUDIT · 3. LOOP/Appeal · 4. VERIFY · 5. BASELINE/OPTIMIZE · 6. FINAL_VERIFY · 7. 恢复 · 8. 预算/辅助 · 9. DELIVER

## 1. 角色与状态契约

- **父 Hermes**：编排 + checker。写 state/review；**不改交付物**。
- **maker**：仅 ACT / LOOP / OPTIMIZE_NOW；不写 verdict、不自判 PASS。
- **delegate**：一次性辅助；不参与 AUDIT/VERIFY；子交付物 OBSERVE 前整合。

`state.md` 记录：

```md
- executor_mode: CC | HERMES | SELF
- maker_transport: claude_print | hermes_chat | direct_write
- maker_session: <id|n/a>
- maker_generation: 1
- maker_status: UNSPAWNED | RUNNING | COMPLETED | INTERRUPTED | UNREACHABLE
```

固定架构：父 Hermes + 一 maker。辅助委派不改变 maker-checker 归属。

### 字段集（复用，勿在下文重复展开）

**PROMPT_BLOCK**（fix / optimize 共用骨架）：

```text
目标对象：…
问题证据：…
必改内容：…
禁止变化：…
验证命令：…
完成回报：…
```

**ISSUE_FIELDS**：`id` / `failure_type` / `severity` / `evidence` / `fix_instruction` / `fix_prompt_ref`

`failure_type`: logic_error | requirement_gap | missing_edge_case | regression | quality_issue | reinventing_existing | budget_issue | missing_skill | weak_validation | external_blocker  
`severity`: blocker | major | minor

**OPTIMIZE_DIM_FIELDS**（functionality / conciseness / maintainability）：

```text
candidate / expected_gain / cost / risk / affects_baseline / needs_user_approval
decision: OPTIMIZE_NOW | DEFER_TO_INBOX | STOP_OPTIMIZING | NO_CANDIDATE
optimize_instruction / optimize_prompt(用 PROMPT_BLOCK) / reason
```

**enrichment** 字段：`candidate…` 同前；`needs_user_approval: ALWAYS`；`decision: SUGGEST_TO_USER | NO_CANDIDATE`；`suggestion` / `reason`（**禁止 OPTIMIZE_NOW**）。

## 2. AUDIT

OBSERVE 并亲自读真实证据后：

```text
进入 AUDIT Round <N>。
读 state.md、review.md、appeal.md（如有）、本协议对应节、实际交付物。
第 2+ 轮：先关闭旧 issue，再 PLAN + 六 gate。
只追加 review.md。Decision∈ PROCEED_TO_VERIFY|CONTINUE_FIX|ESCALATE_REPLAN|STOP_WITH_BLOCKER。
每 issue：唯一 ID + 证据 + fix_instruction + 可发送 fix_prompt（PROMPT_BLOCK）。
同根因连两轮 → ESCALATE_REPLAN。
```

六 gate：

| gate | 口径 |
| --- | --- |
| contract | goal/non-goals/assumptions/checklist/handoff/mode/stage/recovery 可查 |
| completeness | 目标完整，无未确认扩 scope |
| correctness | 逻辑/边界/结构可接受 |
| reuse_existing | 优先复用既有能力，无无理由重造 |
| budget | 时间/工具/maker·delegate/继续价值记录充分 |
| evidence_regression | 证据可复查，无未解释回归 |

```md
## AUDIT Round N
DECISION: PROCEED_TO_VERIFY | CONTINUE_FIX | ESCALATE_REPLAN | STOP_WITH_BLOCKER
ISSUE_COUNT: <n>
STALL_DETECTION:
- recurring_issue: NONE | <id>
- similarity: N/A | IDENTICAL | SAME_ROOT_CAUSE | NEW_ISSUE
- rounds_recurring: 0 | <n>
- notes:
PLAN_CHECK: verdict PASS|FAIL / evidence / notes
GATES: 六项各 PASS|FAIL
ISSUES:
1. <ISSUE_FIELDS>
FIX_PROMPTS:
### <issue id>
- target_role: maker
- execution_order: <int>
- prompt: |
    你是 maker，修正 issue <id>；勿处理其它问题。过程目录：…。
    <PROMPT_BLOCK>
APPEALS: item / ruling UPHELD|OVERRULED|CLARIFIED / reason / replacement_fix_prompt(CLARIFIED 必填完整)
VERIFY_HANDOFF: checklist_items_ready / evidence_paths / unresolved
```

规则：一 issue 一段 prompt；多 prompt 给 execution_order；**先写 review.md + SHA-256 再原样发送**。  
`PROCEED_TO_VERIFY` 当且仅当：ISSUE_COUNT=0 且 PLAN+六 gate PASS 且 unresolved 空且证据可复查。

## 3. LOOP、Prompt 转发与 Appeal

`CONTINUE_FIX`：

1. 从 review.md 读完整 prompt，记 SHA-256。  
2. 按 execution_order 原样 → maker。  
3. maker 仅处理对应 issue。  
4. 父 Hermes 读真实 diff/输出，更新 OBSERVE。  
5. 先核对旧 issue closure，再全六 gate；maker 不判 closure。

appeal.md：

```md
## [APPEAL] <issue id>
original_fix_prompt:
submitted_by: maker | user
reason:
counter_evidence:
```

裁决：`UPHELD` | `OVERRULED`（不计修正轮）| `CLARIFIED`（完整 replacement；旧 prompt 作废）。  
连两轮仅 appeal / 硬 blocker / 预算 / 低价值 → 停。同 class 两轮复发 → ESCALATE_REPLAN；合约变必须重新确认。

## 4. VERIFY

仅 `PROCEED_TO_VERIFY` 后：

```text
进入 VERIFY。独立重跑 checklist 每条命令。
不依赖 OBSERVE/maker 结论；记精确命令与输出或日志路径。只追加 VERIFY。
```

```md
## VERIFY
VERDICT: VERIFIED | RETURN_TO_LOOP | STOP_WITH_BLOCKER
CHECKLIST:
1. item / verdict PASS|FAIL / verification_command / actual_output / evidence
OPEN_ISSUES:（RETURN 时填 ISSUE_FIELDS + fix_prompt=PROMPT_BLOCK）
DELIVERABLE_SUMMARY: changed / why / risks_or_limits / user_should_know
```

`VERIFIED`→BASELINE_LOCK；`RETURN_TO_LOOP`→原样新 fix_prompt；`STOP_WITH_BLOCKER`→停。

## 5. BASELINE 与 OPTIMIZE

VERIFY=`VERIFIED` 后只追加 Baseline（paths、checklist、证据、hash、回滚入口），不改交付物。

```text
进入 OPTIMIZE Round <N>。切换 optimization-seeking。
预扫 changed + 同目录相邻文件；scanned_files 必须非空真实路径。
先写 optimize_todo（四维 pending + known_candidates）。
NO_CANDIDATE 须具体理由；deferred → inbox。不改交付物。
```

```md
## OPTIMIZE_TODO Round N
- [ ] functionality - status: pending|done|deferred|no_candidate
- [ ] conciseness - status: pending|done|deferred|no_candidate
- [ ] maintainability - status: pending|done|deferred|no_candidate
- [ ] enrichment - status: pending|done|deferred|no_candidate
- known_candidates:
  - from: OBSERVE|AUDIT|prior / desc / status pending|done|deferred

## OPTIMIZE Round N
PERSPECTIVE: optimization-seeking
scanned_files: [paths]
### functionality — 优先复用已有/项目内/开源功能等价物；只比功能不抄 UI
<OPTIMIZE_DIM_FIELDS>
### conciseness — 不丢语义删冗余/死代码/多余间接层
<OPTIMIZE_DIM_FIELDS>
### maintainability — 命名/边界/依赖方向/重复逻辑
<OPTIMIZE_DIM_FIELDS>
### enrichment — 合约外增强；始终先问用户
<enrichment 字段>
```

决策：

- `OPTIMIZE_NOW`：真优化非 correctness fix；gain≥5%；低风险；无回归；无新依赖；无需确认；基线可查；附 optimize_prompt。  
- `DEFER_TO_INBOX`：有价值但缺用户/依赖/数据。  
- `STOP_OPTIMIZING`：充分扫描，剩余 <5%。  
- `NO_CANDIDATE`：诚实搜索后无候选 + 具体理由。  
- enrichment：仅 SUGGEST_TO_USER | NO_CANDIDATE。

**`OPTIMIZE_NOW` → 写 review + SHA → 原样给 maker → 回到 AUDIT → VERIFY。**  
无改交付物的停止 → FINAL_VERIFY（勿伪称已 AUDIT）。

## 6. FINAL_VERIFY

```text
进入 FINAL_VERIFY。确认 baseline fingerprint、checklist、优化轮次、停止理由。
loop_todo 除 DELIVER 全勾；optimize_todo 全 closed（done|deferred|no_candidate）。
交付物未脱离已验证基线。只追加 FINAL_VERIFY。
```

```md
## FINAL_VERIFY
VERDICT: VERIFIED | RETURN_TO_BASELINE | STOP_WITH_BLOCKER
BASELINE: integrity PASS|FAIL / evidence
OPTIMIZATION: rounds / stop_reason / todo_closed PASS|FAIL / unresolved
DELIVERABLE_SUMMARY: changed / why / risks_or_limits / user_should_know
```

仅 `VERDICT: VERIFIED` → DELIVER。

## 7. 恢复路由

读现存 state/review/appeal/inbox。

**Maker**：可恢复则续 phase；不可恢复（非临时故障）→ UNREACHABLE、升 generation、replacement 带合约+diff+prompts；勿猜最近 session；checker 进度只从过程文件恢复。

**Phase**（按优先级）：

1. user-confirm 非空 → 问用户  
2. pending appeal → checker 裁决  
3. AUDIT=CONTINUE_FIX → 原样 fix_prompt → maker  
4. AUDIT=ESCALATE_REPLAN → 合约更新先给用户  
5. AUDIT=PROCEED_TO_VERIFY → VERIFY  
6. VERIFY=RETURN_TO_LOOP → 新 prompt  
7. VERIFY=VERIFIED 无 Baseline → BASELINE_LOCK  
8. Baseline 在且 OPTIMIZE 未开 → OPTIMIZE  
9. OPTIMIZE_NOW 已跑未复验 → AUDIT  
10. 优化停/无候选 → FINAL_VERIFY  
11. FINAL_VERIFY=VERIFIED → DELIVER  
12. blocker/预算/appeal deadlock/低价值 → 停

切阶段：更新 `stage` + 勾 `loop_todo`；冲突以 stage 为准。`loop_todo` 只记主链。DELIVER 前须完整 AUDIT→VERIFY→BASELINE→OPTIMIZE→FINAL 路径（OPTIMIZE_NOW 分支含 re-AUDIT）。

## 8. 预算、辅助 Agent 与停止

- 记 maker 首次/resume、修正轮、耗时、delegate、继续价值、停止原因。  
- 允许有益时 `delegate_task`；禁替代 maker/checker、禁未验证 self-report、禁与 maker 并发重叠写。  
- 有界 turn：mode reference + 合约 stop guardrail。

## 9. DELIVER

汇总 changed / why / checklist / 关键证据 / 风险 / 下一步。  
**不清空 session、不删过程文件；仅用户授权清理。**
