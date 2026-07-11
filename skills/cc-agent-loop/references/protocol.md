# CC Agent Loop Protocol

首次 AUDIT 前完整读取本文件。它定义 Claude Code persistent audit session、AUDIT / VERIFY / OPTIMIZE / FINAL_VERIFY、issue-specific fix prompts、appeal 与恢复路由。

## 目录

- [1. Audit Session 契约](#1-audit-session-契约)
- [2. 续轮与失效替换](#2-续轮与失效替换)
- [3. AUDIT](#3-audit)
- [4. LOOP 与 Appeal](#4-loop-与-appeal)
- [5. VERIFY](#5-verify)
- [6. BASELINE 与 OPTIMIZE](#6-baseline-与-optimize)
- [7. FINAL_VERIFY](#7-final_verify)
- [8. 恢复路由](#8-恢复路由)
- [9. 预算、辅助 Agent 与停止](#9-预算辅助-agent-与停止)
- [10. DELIVER](#10-deliver)

## 1. Audit Session 契约

主 CC 是 maker；audit CC 是独立 checker。整个任务只保留一个可恢复的 audit session。

在 `state.md` 记录：

```md
- audit_session: <预分配 UUID>
- audit_generation: 1
- audit_status: UNSPAWNED | RUNNING | COMPLETED | INTERRUPTED | UNREACHABLE
- audit_transport: direct_write | primary_verbatim
```

### 首次调用

生成合法 UUID 并在调用前写入 `state.md`：

```bash
AUDIT_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')

claude -p "你是独立 audit Agent。只审查，不修改交付物。
读取 state/<slug>/state.md、review.md、appeal.md（存在时）和本协议。
检查 PLAN；运行六个 gate；为每个 issue 生成独立 fix_prompt。
只创建或追加 state/<slug>/review.md。严格使用 AUDIT schema。" \
  --session-id "$AUDIT_ID" \
  --allowedTools "Read,Write,Grep,Glob,Bash(git diff *,git status *,git show *,rg *,find *,cat *,head *,tail *,shasum *,pytest *,npm test *,npx *,make *,cargo *,go test *,python -m *,ruff *,mypy *,eslint *,tsc *,prettier *)" \
  --permission-mode dontAsk \
  --max-turns 5 \
  --output-format json
```

- 可在已配置 custom agent 时加 `--agent reviewer`，但不得要求用户预先创建它，也不得自动修改全局配置。
- `--allowedTools` 在首次调用时锁定；后续 resume 继承它。audit 需要 `Write` 才能写 `review.md`，但 Claude Code 不支持 per-file write 限制，因此 prompt 必须明确禁止修改交付物。
- `--output-format json` 便于记录调用结果；权威 session handle 仍是预分配 UUID。
- 不要使用 `--no-session-persistence`、`--continue` 或“最近一次 session”。

完整 handoff 必须包含：绝对工作目录、过程目录、交付物路径、phase、允许写入的唯一过程文件、checklist、停止条件和本协议路径。

### 只读或写入失败兜底

如果 audit CC 无法写 `review.md`：

1. 要求它在 final response 中返回完整审查 block，不要只给摘要。
2. 主 CC 只能逐字转存，不得编辑、补判或重写。
3. 在 `state.md` 记录 `audit_transport: primary_verbatim`、response SHA-256 和来源 session。
4. 任一内容变更都使审查无效，必须让 audit CC 重新出具。

## 2. 续轮与失效替换

每个后续阶段恢复同一 session：

```bash
claude -p "<phase-specific prompt；重新读取 state.md、review.md 与本协议>" \
  --resume "$AUDIT_ID" \
  --max-turns 5 \
  --output-format json
```

- 不要在 resume 时使用 `--fork-session`；它会产生新 session，破坏同一 checker 的 issue closure 记忆。
- 不要重复传入更宽的工具集合并假设生效；首次 tool scope 是权威边界。
- resume 返回后，主 CC 必须亲自读取 `review.md` 和实际证据；audit final summary 本身不是 verdict。

### Session 不可恢复

只有显式 resume 失败且不是短暂 provider / auth / quota 故障时，才替换 audit session：

1. 在 `state.md` 记录旧 UUID、失败输出和 `UNREACHABLE`。
2. 递增 `audit_generation`，生成新 UUID。
3. 将 `state.md`、完整 `review.md`、pending appeal 和最后未决 issue 交给 replacement audit。
4. 要求 replacement 先核对旧 issue closure，再继续当前 phase。

禁止扫描本地 session 目录或用 `--continue` 猜恢复目标。

## 3. AUDIT

AUDIT prompt：

```text
进入 AUDIT Round <N>。
读取最新 state.md、review.md、appeal.md（如有）和实际交付物。
第二轮及以后先逐项关闭旧 issue，再检查 PLAN 与六个 gate。
只追加 review.md，不要修改交付物。
Decision 只能是 PROCEED_TO_VERIFY、CONTINUE_FIX、ESCALATE_REPLAN、STOP_WITH_BLOCKER。
每个 issue 必须有唯一 ID、证据、fix_instruction 和可直接执行的 fix_prompt。
同类根因连续出现两轮时使用 ESCALATE_REPLAN。
```

六个 gate：

- `contract`：goal、non-goals、assumptions、checklist、handoff、stage path 与 recovery 均明确可查。
- `completeness`：结果完整满足用户目标，没有漏项或未经确认的范围扩张。
- `correctness`：逻辑、边界条件、结构和必要简洁性可接受，没有已知错误。
- `reuse_existing`：优先复用标准库、平台能力、项目代码和已安装依赖，没有无理由重造。
- `budget`：记录时间、工具、agent 调用、继续价值和停止信号，投入与风险相称。
- `evidence_regression`：结论有可复查证据，且没有破坏已知行为或引入未解释回归。

AUDIT schema：

```md
## AUDIT Round N

DECISION: PROCEED_TO_VERIFY | CONTINUE_FIX | ESCALATE_REPLAN | STOP_WITH_BLOCKER
ISSUE_COUNT: <number>

STALL_DETECTION:
- recurring_issue: NONE | <prior issue id>
- similarity: N/A | IDENTICAL | SAME_ROOT_CAUSE | NEW_ISSUE
- rounds_recurring: 0 | <count>
- notes:

PLAN_CHECK:
- verdict: PASS | FAIL
- evidence:
- notes:

GATES:
- contract: PASS | FAIL
- completeness: PASS | FAIL
- correctness: PASS | FAIL
- reuse_existing: PASS | FAIL
- budget: PASS | FAIL
- evidence_regression: PASS | FAIL

ISSUES:
1. id:
   failure_type: logic_error | requirement_gap | missing_edge_case | regression | quality_issue | reinventing_existing | budget_issue | missing_skill | weak_validation | external_blocker
   severity: blocker | major | minor
   evidence:
   fix_instruction:
   fix_prompt_ref: <issue id>

FIX_PROMPTS:
### <issue id>
- target_role: primary_cc
- execution_order: <integer>
- prompt: |
    你正在修正 issue <id>，不要处理其它问题。
    目标对象：<精确文件、符号或产物>。
    问题证据：<路径、行号、命令输出或复现>。
    必改内容：<可验证的必要变化>。
    禁止变化：<范围、行为和文件边界>。
    验证命令：<精确命令与预期结果>。
    完成回报：<必须返回的 diff、输出和剩余风险>。

APPEALS:
- item:
  ruling: UPHELD | OVERRULED | CLARIFIED
  reason:
  replacement_fix_prompt: <CLARIFIED 时必填完整 prompt>

VERIFY_HANDOFF:
- checklist_items_ready:
- evidence_paths:
- unresolved:
```

`fix_prompt` 是 checker 到 maker 的稳定接口：

- 每个阻塞 issue 恰好一段 prompt，并通过 issue ID 关联。
- prompt 必须自包含、可直接执行；不得只写“修一下”“按上面处理”。
- 多个 prompt 必须给 execution order；若它们互相冲突，audit CC 必须先解决冲突。
- 主 CC 不得代写、合并、弱化或补全 prompt；只能原样执行或 appeal。

只有 `ISSUE_COUNT: 0`、PLAN PASS、六 gate 全 PASS、unresolved 为空且证据可复查时，才能 `PROCEED_TO_VERIFY`。

## 4. LOOP 与 Appeal

收到 `CONTINUE_FIX` 后：

1. 主 CC 按 `execution_order` 原样执行每段 `fix_prompt`。
2. 每段 prompt 只处理对应 issue；不得顺手扩大范围。
3. 执行后更新 OBSERVE 证据，再恢复同一 audit session。

无法接受 prompt 时写入 `appeal.md`：

```md
## [APPEAL] <issue id>
original_fix_prompt:
reason:
counter_evidence:
```

- `UPHELD`：原 prompt 不变。
- `OVERRULED`：移除 issue，不计修正轮。
- `CLARIFIED`：audit CC 必须给出替换后的完整 `replacement_fix_prompt`；旧 prompt 作废。

连续两轮只有 appeal、硬 blocker、预算上限或低价值继续时停止。相同 issue class 连续两轮复发时 `ESCALATE_REPLAN`；合约变化必须重新取得用户确认。

## 5. VERIFY

只有 AUDIT 为 `PROCEED_TO_VERIFY` 才能恢复同一 audit session 进入 VERIFY：

```text
进入 VERIFY。独立重跑 checklist 中每个验证命令。
不要依赖 OBSERVE 的结论；记录精确命令、实际输出或完整日志路径。
追加 VERIFY section；不要修改交付物。
```

```md
## VERIFY

VERDICT: VERIFIED | RETURN_TO_LOOP | STOP_WITH_BLOCKER

CHECKLIST:
1. item:
   verdict: PASS | FAIL
   verification_command: <exact command>
   actual_output: <raw output 或完整日志路径>
   evidence:

OPEN_ISSUES:
- id:
  failure_type:
  evidence:
  fix_instruction:
  fix_prompt: |
    <使用与 AUDIT 相同的可直接执行结构>

DELIVERABLE_SUMMARY:
- changed:
- why:
- risks_or_limits:
- user_should_know:
```

`VERIFIED` 进入 BASELINE_LOCK；`RETURN_TO_LOOP` 按新的 fix prompt 修正；`STOP_WITH_BLOCKER` 停止并报告。

## 6. BASELINE 与 OPTIMIZE

VERIFY 为 `VERIFIED` 后，主 CC 只追加 Baseline，不改变交付物。记录 deliverable paths、checklist、证据、文件或 patch hash 和回滚入口。

随后恢复同一 audit session：

```text
进入 OPTIMIZE Round <N>。停止重复 correctness 审查，开始寻找可量化优化。
预扫描 changed files 与同目录逻辑相邻文件。
先写 optimize_todo：四个维度各一行标 pending，并逐条登记 OBSERVE / AUDIT / 前序轮次中已发现但未处理的可优化候选，防止遗漏。
四个维度缺一不可；NO_CANDIDATE 必须给具体理由。
每维度扫完把 todo 对应行更新为 done | deferred | no_candidate；deferred 项写入 inbox。
不要修改交付物。
```

`scanned_files` 必须非空且含真实路径，否则整轮无效。

`optimize_todo` 在每个 OPTIMIZE Round 开头维护，FINAL_VERIFY 前必须全部 closed：

```md
## OPTIMIZE_TODO Round N
- [ ] functionality - status: pending | done | deferred | no_candidate
- [ ] conciseness - status: pending | done | deferred | no_candidate
- [ ] maintainability - status: pending | done | deferred | no_candidate
- [ ] enrichment - status: pending | done | deferred | no_candidate
- known_candidates:
  - from: <OBSERVE | AUDIT | prior round>
    desc:
    status: pending | done | deferred
```

```md
## OPTIMIZE Round N

PERSPECTIVE: optimization-seeking
scanned_files: [changed files + adjacent files]

### functionality — 优先复用已有、项目内或开源功能等价物；只比较功能实现，不复制 UI 视觉
- candidate: / expected_gain: / cost: / risk: / affects_baseline: / needs_user_approval:
- decision: OPTIMIZE_NOW | DEFER_TO_INBOX | STOP_OPTIMIZING | NO_CANDIDATE
- optimize_instruction:
- optimize_prompt: |
    <OPTIMIZE_NOW 时使用与 fix_prompt 同级别的目标、禁改、验证和回报结构>
- reason:

### conciseness — 不丢语义或行为地删除文字冗余、死代码、不必要间接层和过度抽象
- candidate: / expected_gain: / cost: / risk: / affects_baseline: / needs_user_approval:
- decision: OPTIMIZE_NOW | DEFER_TO_INBOX | STOP_OPTIMIZING | NO_CANDIDATE
- optimize_instruction: / optimize_prompt: / reason:

### maintainability — 检查命名、模块边界、依赖方向和重复逻辑
- candidate: / expected_gain: / cost: / risk: / affects_baseline: / needs_user_approval:
- decision: OPTIMIZE_NOW | DEFER_TO_INBOX | STOP_OPTIMIZING | NO_CANDIDATE
- optimize_instruction: / optimize_prompt: / reason:

### enrichment — 承接前三维遗漏、合约外增强和新增产品能力；始终先问用户
- candidate: / expected_gain: / cost: / risk: / affects_baseline: / needs_user_approval: ALWAYS
- decision: SUGGEST_TO_USER | NO_CANDIDATE
- suggestion: / reason:
```

- `OPTIMIZE_NOW`：真实优化；预期收益不少于 5%；低风险；无回归；无新依赖；无需确认；基线仍可检查；必须附直接可执行的 `optimize_prompt`。
- `DEFER_TO_INBOX`：有价值但缺少用户上下文、依赖决定或当前数据。
- `STOP_OPTIMIZING`：已充分扫描，剩余收益低于 5%。
- `NO_CANDIDATE`：诚实搜索后无合理候选，必须写具体理由。
- `enrichment`：只能 `SUGGEST_TO_USER` 或 `NO_CANDIDATE`。

执行 `OPTIMIZE_NOW` 后必须回到 AUDIT，再 VERIFY；四维全部无候选时，主 CC 检查理由是否充分。

## 7. FINAL_VERIFY

优化停止或已复验通过后，恢复同一 audit session：

```text
进入 FINAL_VERIFY。确认 baseline fingerprint、checklist、优化轮次与停止理由。
检查 loop_todo 除 DELIVER 外全部打勾，且 optimize_todo 全部 closed（done | deferred | no_candidate），无 pending；否则 RETURN_TO_BASELINE。
检查当前交付物未脱离已验证基线；追加 FINAL_VERIFY；不要修改交付物。
```

```md
## FINAL_VERIFY

VERDICT: VERIFIED | RETURN_TO_BASELINE | STOP_WITH_BLOCKER

BASELINE:
- integrity: PASS | FAIL
- evidence:

OPTIMIZATION:
- rounds:
- stop_reason:
- todo_closed: PASS | FAIL
- unresolved:

DELIVERABLE_SUMMARY:
- changed:
- why:
- risks_or_limits:
- user_should_know:
```

只有 `VERDICT: VERIFIED` 才能 DELIVER。

## 8. 恢复路由

恢复前读取实际存在的 `state.md`、`review.md`、`appeal.md` 和 `state/inbox.md`，再用显式 `audit_session` 恢复 checker。

- `user-confirm` 非空：先问用户。
- pending appeal：同一 audit session 裁决。
- 最新 AUDIT 为 `CONTINUE_FIX`：主 CC 按 fix prompts 进入 LOOP。
- 最新 AUDIT 为 `ESCALATE_REPLAN`：先向用户提交合约更新。
- 最新 AUDIT 为 `PROCEED_TO_VERIFY`：同一 audit session 进入 VERIFY。
- 最新 VERIFY 为 `RETURN_TO_LOOP`：按新 fix prompt 修正。
- 最新 VERIFY 为 `VERIFIED` 且无 Baseline：BASELINE_LOCK。
- Baseline 已写且 OPTIMIZE 未开始：OPTIMIZE。
- OPTIMIZE_NOW 已执行但未复验：AUDIT。
- 优化停止或无候选：FINAL_VERIFY。
- 最新 FINAL_VERIFY 为 `VERIFIED`：DELIVER。
- session 不可恢复：按 generation 生成 replacement audit。
- blocker、预算上限、appeal deadlock 或低价值继续：停止并报告。

每次切换阶段前更新 `state.md` 的 `stage` 并在 `loop_todo` 对应项打勾；`loop_todo` 与 `stage` 冲突时以 `stage` 为准并立即修正 `loop_todo`。`loop_todo` 只追踪线性主链（PLAN → DELIVER），LOOP / ESCALATE_REPLAN 是 AUDIT 的内部出口，不单列。DELIVER 前必须有完整 AUDIT → VERIFY → BASELINE_LOCK → OPTIMIZE → FINAL_VERIFY 路径，且 `loop_todo` 除 DELIVER 外全部打勾。

## 9. 预算、辅助 Agent 与停止

- 记录首次调用与每次 resume、修正轮、耗时、预算、继续价值和停止原因。
- audit 常规使用 `--max-turns 5`，VERIFY / FINAL_VERIFY 可用 3；若当前 CLI 不支持该参数，删除参数并以合约 stop guardrail 控制。
- 本技能授权主 CC 在任务能从并行或专长分工中实际受益时使用当前 host 的原生 Agent / Task 委派能力，不要求为每次普通委派另行确认；更高优先级指令、外部动作和不可逆操作仍照常受限。
- 只委派边界清楚、可独立、可验证的一次性任务；把 handoff、结果和主 CC 的独立验证写入 state。auxiliary agent 不参与 AUDIT / VERIFY、不替代 audit CC，其 self-report 不能直接作为证据。
- auxiliary agent 若修改隔离的子交付物，该输出按 maker-side 工作处理，必须在 OBSERVE 前完成整合并由 audit CC 纳入完整审查。
- 并行优先用于只读探索、测试和日志分析；避免并发写重叠文件。

## 10. DELIVER

主 CC 汇总 changed、why、checklist、关键证据、风险和下一步。不要清空 audit session 或删除过程文件；只有用户能授权清理。
