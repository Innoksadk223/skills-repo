# CC Agent Loop Protocol

按阶段读取对应节（见 SKILL 开卷表）。定义 persistent audit session、AUDIT/VERIFY/OPTIMIZE/FINAL、fix_prompt、appeal、恢复。

## 目录

1. Audit Session 契约 · 2. 续轮/替换 · 3. AUDIT · 4. LOOP/Appeal · 5. VERIFY · 6. BASELINE/OPTIMIZE · 7. FINAL_VERIFY · 8. 恢复 · 9. 预算/辅助 · 10. DELIVER

## 1. Audit Session 契约

主 CC = maker；audit CC = checker。任务内仅一个可恢复 audit session。

```md
- audit_session: <预分配 UUID>
- audit_generation: 1
- audit_status: UNSPAWNED | RUNNING | COMPLETED | INTERRUPTED | UNREACHABLE
- audit_transport: direct_write | primary_verbatim
```

### 字段集（复用）

**PROMPT_BLOCK**：目标对象 / 问题证据 / 必改内容 / 禁止变化 / 验证命令 / 完成回报  

**ISSUE_FIELDS**：id / failure_type / severity / evidence / fix_instruction / fix_prompt_ref  

`failure_type`: logic_error | requirement_gap | missing_edge_case | regression | quality_issue | reinventing_existing | budget_issue | missing_skill | weak_validation | external_blocker  
`severity`: blocker | major | minor

**OPTIMIZE_DIM_FIELDS**（functionality|conciseness|maintainability）：candidate / expected_gain / cost / risk / affects_baseline / needs_user_approval / decision(OPTIMIZE_NOW|DEFER_TO_INBOX|STOP_OPTIMIZING|NO_CANDIDATE) / optimize_instruction / optimize_prompt(PROMPT_BLOCK) / reason  

**enrichment**：同上字段基线；`needs_user_approval: ALWAYS`；`decision: SUGGEST_TO_USER|NO_CANDIDATE`；suggestion/reason（禁 OPTIMIZE_NOW）

### 首次调用

```bash
AUDIT_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
# 先写入 state.md 的 audit_session

claude -p "你是独立 audit Agent。只审查，不改交付物。
读取 state/<slug>/state.md、review.md、appeal.md（如有）与 protocol 对应节。
检查 PLAN；六 gate；每 issue 独立 fix_prompt（PROMPT_BLOCK）。
只写 state/<slug>/review.md。严格 AUDIT schema。" \
  --session-id "$AUDIT_ID" \
  --allowedTools "Read,Write,Grep,Glob,Bash(git diff *,git status *,git show *,rg *,find *,cat *,head *,tail *,shasum *,pytest *,npm test *,npx *,make *,cargo *,go test *,python -m *,ruff *,mypy *,eslint *,tsc *,prettier *)" \
  --permission-mode dontAsk \
  --max-turns 5 \
  --output-format json
```

- 可选 `--agent reviewer`（不要求用户预创建，不改全局配置）。  
- 首次锁定 `--allowedTools`；需要 Write 写 review.md，但无 per-file sandbox → prompt 禁改交付物。  
- 权威 handle = 预分配 UUID。禁 `--no-session-persistence` / `--continue` / 最近 session。  
- handoff：绝对 cwd、过程目录、交付物、phase、唯一可写过程文件、checklist、停止条件、协议路径。

### 写入失败兜底

1. final 返回完整审查 block（非摘要）。  
2. 主 CC 逐字转存，不编辑。  
3. state 记 `audit_transport: primary_verbatim` + SHA-256 + 来源。  
4. 任何篡改 → 审查无效，audit 重出。

## 2. 续轮与失效替换

```bash
claude -p "<phase prompt；重读 state/review + protocol 对应节>" \
  --resume "$AUDIT_ID" --max-turns 5 --output-format json
```

- 禁 resume `--fork-session`。勿假定更宽 tools 生效。  
- 返回后主 CC 亲读 review.md + 真实证据；summary ≠ verdict。

**不可恢复**（非临时故障）：记旧 UUID+输出+UNREACHABLE → 升 generation + 新 UUID → 交 state/完整 review/appeal/未决 issue → replacement 先关旧 issue。禁扫本地 session 目录。

## 3. AUDIT

```text
进入 AUDIT Round <N>。读 state/review/appeal/交付物。
第 2+ 轮先关旧 issue，再 PLAN+六 gate。只追加 review.md。
Decision∈ PROCEED_TO_VERIFY|CONTINUE_FIX|ESCALATE_REPLAN|STOP_WITH_BLOCKER。
同根因两轮 → ESCALATE_REPLAN。
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
- target_role: primary_cc
- execution_order: <int>
- prompt: |
    你正在修正 issue <id>，勿处理其它问题。
    <PROMPT_BLOCK>
APPEALS: UPHELD|OVERRULED|CLARIFIED + replacement(CLARIFIED 完整)
VERIFY_HANDOFF: checklist_items_ready / evidence_paths / unresolved
```

一 issue 一段；主 CC 不得代写/合并/弱化 prompt。  
PROCEED 条件：ISSUE_COUNT=0 且 PLAN+六 gate PASS 且 unresolved 空且证据可复查。

## 4. LOOP 与 Appeal

1. 按 execution_order 原样执行 fix_prompt。  
2. 不扩 scope。  
3. 更新 OBSERVE → resume 同一 audit。

```md
## [APPEAL] <issue id>
original_fix_prompt:
reason:
counter_evidence:
```

UPHELD / OVERRULED（不计轮）/ CLARIFIED（完整 replacement）。  
连两轮仅 appeal / blocker / 预算 / 低价值 → 停。同类两轮 → ESCALATE_REPLAN + 重新确认合约。

## 5. VERIFY

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

VERIFIED→BASELINE；RETURN→新 fix；STOP→停。

## 6. BASELINE 与 OPTIMIZE

主 CC 只追加 Baseline（paths/checklist/证据/hash/回滚）。然后 resume audit：

```text
进入 OPTIMIZE Round <N>。optimization-seeking。
预扫 changed+相邻；scanned_files 非空真实路径否则整轮无效。
先 optimize_todo 四维+known_candidates。NO_CANDIDATE 写理由。deferred→inbox。不改交付物。
```

```md
## OPTIMIZE_TODO Round N
- [ ] functionality|conciseness|maintainability|enrichment - status pending|done|deferred|no_candidate
- known_candidates: from / desc / status

## OPTIMIZE Round N
PERSPECTIVE: optimization-seeking
scanned_files: [paths]
### functionality — 复用已有功能等价物；不抄 UI
<OPTIMIZE_DIM_FIELDS>
### conciseness — 删冗余/死代码/多余间接层
<OPTIMIZE_DIM_FIELDS>
### maintainability — 命名/边界/依赖/重复
<OPTIMIZE_DIM_FIELDS>
### enrichment — 合约外增强；先问用户
<enrichment>
```

OPTIMIZE_NOW：gain≥5%；低风险；无回归；无新依赖；无需确认；附 optimize_prompt。  
enrichment 仅 SUGGEST_TO_USER|NO_CANDIDATE。  
**OPTIMIZE_NOW 后 → AUDIT → VERIFY。** 无改动停止 → FINAL_VERIFY。

## 7. FINAL_VERIFY

```text
确认 baseline、优化轮次、停止理由；loop_todo（除 DELIVER）全勾；optimize_todo 全 closed。未脱离基线。
```

```md
## FINAL_VERIFY
VERDICT: VERIFIED | RETURN_TO_BASELINE | STOP_WITH_BLOCKER
BASELINE / OPTIMIZATION / DELIVERABLE_SUMMARY
```

仅 VERIFIED→DELIVER。

## 8. 恢复路由

读过程文件 → resume 精确 audit_session。

1. user-confirm → 问用户  
2. appeal → 同一 audit 裁决  
3. CONTINUE_FIX → 主 CC LOOP  
4. ESCALATE_REPLAN → 用户确认合约  
5. PROCEED → VERIFY  
6. RETURN_TO_LOOP → 新 fix  
7. VERIFIED 无 Baseline → BASELINE  
8. Baseline 在未 OPTIMIZE → OPTIMIZE  
9. OPTIMIZE_NOW 未复验 → AUDIT  
10. 优化停 → FINAL_VERIFY  
11. FINAL VERIFIED → DELIVER  
12. session 不可恢复 → replacement  
13. blocker/预算/deadlock → 停

切阶段更新 stage+loop_todo；冲突以 stage 为准。DELIVER 前须 AUDIT→VERIFY→BASELINE→OPTIMIZE→FINAL（含 OPTIMIZE_NOW 再审）。

## 9. 预算、辅助与停止

- 记首次/resume/修正轮/耗时/停止原因。audit 常规 max-turns 5，VERIFY/FINAL 可用 3（CLI 不支持则删参数，用合约护栏）。  
- 允许原生 Agent/Task 辅助；不替代 audit；self-report≠证据；禁重叠并发写；子交付物 OBSERVE 前整合。

## 10. DELIVER

汇总 changed/why/checklist/证据/风险/下一步。  
**不清空 audit session、不删过程文件；仅用户授权清理。**
