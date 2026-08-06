# Pi Agent Loop Protocol

按阶段读取对应节（见 SKILL 开卷表）。定义 audit 子 Agent 契约、AUDIT/VERIFY/OPTIMIZE/FINAL、fix_prompt、appeal、恢复。

## 目录

1. Audit 子 Agent 契约 · 2. AUDIT · 3. LOOP/Appeal · 4. VERIFY · 5. BASELINE/OPTIMIZE · 6. FINAL_VERIFY · 7. 恢复 · 8. 预算/辅助 · 9. DELIVER

## 1. Audit 子 Agent 契约

主 Pi = maker；audit Pi = checker。任务内仅一个 audit 子 Agent，跨 AUDIT/VERIFY/OPTIMIZE/FINAL_VERIFY 复用；判定与复验均出自同一 audit，主 Pi 不自判。

- 独立：不参与 ACT；不改交付物；只写 `state/<slug>/review.md`。
- 途径自定：调用机制由主 Pi 执行时自定（原生 subagent / agent_team / 其它），本协议不规定具体途径。
- 不可用：子 Agent 不可用或上下文丢失 -> 重新派发，交 state/完整 review/appeal/未决 issue；先关旧 issue。临时故障不立即替换。
- 换 audit 前先关旧 issue 并说明理由；同一任务内不得并行多个 audit。

### 字段集（复用）

**PROMPT_BLOCK**：目标对象 / 问题证据 / 必改内容 / 禁止变化 / 验证命令 / 完成回报

**ISSUE_FIELDS**：id / failure_type / severity / evidence / fix_instruction / fix_prompt_ref

`failure_type`: logic_error | requirement_gap | missing_edge_case | regression | quality_issue | reinventing_existing | budget_issue | missing_skill | weak_validation | external_blocker  
`severity`: blocker | major | minor

**OPTIMIZE_DIM_FIELDS**（functionality|conciseness|maintainability）：candidate / expected_gain / cost / risk / affects_baseline / needs_user_approval / decision(OPTIMIZE_NOW|DEFER_TO_INBOX|STOP_OPTIMIZING|NO_CANDIDATE) / optimize_instruction / optimize_prompt(PROMPT_BLOCK) / reason

**enrichment**：同上字段基线；`needs_user_approval: ALWAYS`；`decision: SUGGEST_TO_USER|NO_CANDIDATE`；suggestion/reason（禁 OPTIMIZE_NOW）

## 2. AUDIT

```text
进入 AUDIT Round <N>。读 state/review/appeal/交付物。
第 2+ 轮先关旧 issue，再 PLAN+六 gate。只追加 review.md。
Decision∈ PROCEED_TO_VERIFY|CONTINUE_FIX|ESCALATE_REPLAN|STOP_WITH_BLOCKER。
同根因两轮 -> ESCALATE_REPLAN。
```

六 gate：contract / completeness / correctness / reuse_existing / budget / evidence_regression（口径同家族：可查、完整、正确、复用、预算相称、证据无回归）。

```md
## AUDIT Round N
DECISION: …
ISSUE_COUNT:
STALL_DETECTION: recurring_issue / similarity(N/A|IDENTICAL|SAME_ROOT_CAUSE|NEW_ISSUE) / rounds_recurring / notes
PLAN_CHECK: PASS|FAIL / evidence / notes
GATES: 六项 PASS|FAIL
ISSUES: <ISSUE_FIELDS>
FIX_PROMPTS:
### <id>
- target_role: primary_pi
- execution_order: <int>
- prompt: |
    你正在修正 issue <id>，勿处理其它问题。
    <PROMPT_BLOCK>
APPEALS: UPHELD|OVERRULED|CLARIFIED + replacement(CLARIFIED 完整)
VERIFY_HANDOFF: checklist_items_ready / evidence_paths / unresolved
```

一 issue 一段；主 Pi 不得代写/合并/弱化 prompt。  
PROCEED 条件：ISSUE_COUNT=0 且 PLAN+六 gate PASS 且 unresolved 空且证据可复查。

## 3. LOOP 与 Appeal

1. 按 execution_order 原样执行 fix_prompt。  
2. 不扩 scope。  
3. 更新 OBSERVE -> resume 同一 audit。

```md
## [APPEAL] <issue id>
original_fix_prompt:
reason:
counter_evidence:
```

UPHELD / OVERRULED（不计轮）/ CLARIFIED（完整 replacement）。  
连两轮仅 appeal / blocker / 预算 / 低价值 -> 停。同类两轮 -> ESCALATE_REPLAN + 重新确认合约。

## 4. VERIFY

仅 PROCEED 后 resume audit：

```text
进入 VERIFY。独立重跑 checklist。不依赖 OBSERVE。记命令与输出。只追加 VERIFY。
```

```md
## VERIFY
VERDICT: VERIFIED | RETURN_TO_LOOP | STOP_WITH_BLOCKER
CHECKLIST: item / PASS|FAIL / verification_command / actual_output / evidence
OPEN_ISSUES: + fix_prompt=PROMPT_BLOCK
DELIVERABLE_SUMMARY: changed / why / risks_or_limits / user_should_know
```

VERIFIED->BASELINE；RETURN->新 fix；STOP->停。

## 5. BASELINE 与 OPTIMIZE

主 Pi 只追加 Baseline（paths/checklist/证据/hash/回滚）。然后 resume audit：

```text
进入 OPTIMIZE Round <N>。optimization-seeking。
预扫 changed+相邻；scanned_files 非空真实路径否则整轮无效。
先 optimize_todo 四维+known_candidates。NO_CANDIDATE 写理由。deferred->inbox。不改交付物。
```

**OPTIMIZE 默认启动**：VERIFY 通过后必须进入 BASELINE_LOCK -> OPTIMIZE，禁以「无需优化」为由跳过；无候选时 `NO_CANDIDATE`（写理由）或 `STOP_OPTIMIZING` 正常停止，不算跳过。

```md
## OPTIMIZE_TODO Round N
- [ ] functionality|conciseness|maintainability|enrichment - status pending|done|deferred|no_candidate
- known_candidates: from / desc / status

## OPTIMIZE Round N
PERSPECTIVE: optimization-seeking
scanned_files: [paths]
### functionality - 复用已有功能等价物；不抄 UI
<OPTIMIZE_DIM_FIELDS>
### conciseness - 删冗余/死代码/多余间接层
<OPTIMIZE_DIM_FIELDS>
### maintainability - 命名/边界/依赖/重复
<OPTIMIZE_DIM_FIELDS>
### enrichment - 合约外增强；先问用户
<enrichment>
```

OPTIMIZE_NOW：gain≥5%；低风险；无回归；无新依赖；无需确认；附 optimize_prompt。  
enrichment 仅 SUGGEST_TO_USER|NO_CANDIDATE。  
**OPTIMIZE_NOW 后 -> AUDIT -> VERIFY。** 无改动停止 -> FINAL_VERIFY。

## 6. FINAL_VERIFY

```text
确认 baseline、优化轮次、停止理由；loop_todo（除 DELIVER）全勾；optimize_todo 全 closed。未脱离基线。
```

```md
## FINAL_VERIFY
VERDICT: VERIFIED | RETURN_TO_BASELINE | STOP_WITH_BLOCKER
BASELINE / OPTIMIZATION / DELIVERABLE_SUMMARY
```

仅 VERIFIED->DELIVER。

## 7. 恢复路由

读现存过程文件（state.md/review.md/appeal.md）-> 确认 stage 与 audit 子 Agent 可用性 -> 不可用则重新派发（保留 review.md 历史，先关旧 issue）-> 继续当前阶段。

1. user-confirm -> 问用户  
2. appeal -> 同一 audit 裁决  
3. CONTINUE_FIX -> 主 Pi LOOP  
4. ESCALATE_REPLAN -> 用户确认合约  
5. PROCEED -> VERIFY  
6. RETURN_TO_LOOP -> 新 fix  
7. VERIFIED 无 Baseline -> BASELINE  
8. Baseline 未 OPTIMIZE -> OPTIMIZE（必走）  
9. OPTIMIZE_NOW 未复验 -> AUDIT  
10. 优化停 -> FINAL_VERIFY  
11. FINAL VERIFIED -> DELIVER  
12. audit 不可用 -> 重新派发  
13. blocker/预算/deadlock -> 停

切阶段更新 stage+loop_todo；冲突以 stage 为准。DELIVER 前须 AUDIT->VERIFY->BASELINE->OPTIMIZE->FINAL（含 OPTIMIZE_NOW 再审）。

## 8. 预算、辅助与停止

- 记首次/resume/修正轮/耗时/停止原因。audit 常规预算 ≤5 轮（tool 调用），VERIFY/FINAL ≤3 轮；由 audit prompt 内护栏强制（「超限即停并报告」）。
- 允许原生 subagent/辅助工具；不替代 audit；self-report≠证据；禁重叠并发写；子交付物 OBSERVE 前整合。

## 9. DELIVER

汇总 changed/why/checklist/证据/风险/下一步。  
**不清空 audit、不删过程文件；仅用户授权清理。**
