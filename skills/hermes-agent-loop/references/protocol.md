# Hermes Agent Loop Protocol

首次 ACT / AUDIT 前完整读取本文件。它定义父 Hermes checker 与 persistent maker 的边界、issue-specific prompts、AUDIT / VERIFY / OPTIMIZE / FINAL_VERIFY、appeal、辅助委派和恢复路由。CLI transport 由对应 executor-mode reference 定义。

## 目录

- [1. 角色与状态契约](#1-角色与状态契约)
- [2. AUDIT](#2-audit)
- [3. LOOP、Prompt 转发与 Appeal](#3-loopprompt-转发与-appeal)
- [4. VERIFY](#4-verify)
- [5. BASELINE 与 OPTIMIZE](#5-baseline-与-optimize)
- [6. FINAL_VERIFY](#6-final_verify)
- [7. 恢复路由](#7-恢复路由)
- [8. 预算、辅助 Agent 与停止](#8-预算辅助-agent-与停止)
- [9. DELIVER](#9-deliver)

## 1. 角色与状态契约

- **父 Hermes / orchestrator + checker**：负责 PLAN、USER_GATE、证据读取、阶段路由、AUDIT、appeal 裁决、VERIFY、prompts、OPTIMIZE、FINAL_VERIFY、Baseline 和 DELIVER；不得修改交付物。
- **maker**：CC executor mode 中是 persistent CC session；Hermes executor mode 中是 persistent Hermes worker session。只负责 ACT、LOOP 和 OPTIMIZE_NOW；不得写 verdict 或给自己判 PASS。
- **delegate agent**：父 Hermes 按任务需要派出的一次性辅助角色；不属于固定 maker/checker，不参与 AUDIT / VERIFY。若它修改隔离的子交付物，该输出按 maker-side 工作处理。

父 Hermes 独占 `state.md` 和 `review.md` 的审查写入；maker 读取合约与 prompts，只修改交付物。若 maker 需要报告无法执行或反证，只返回证据，由父 Hermes 写入 `appeal.md`。

在 `state.md` 记录：

```md
- executor_mode: CC | HERMES
- maker_transport: claude_print | hermes_chat
- maker_session: <CC UUID 或 Hermes session ID>
- maker_generation: 1
- maker_status: UNSPAWNED | RUNNING | COMPLETED | INTERRUPTED | UNREACHABLE
```

固定架构始终是父 Hermes + 一个 maker，共两个 agent。辅助委派的数量由合约预算和任务拆分决定，不改变 maker-checker 归属。

## 2. AUDIT

父 Hermes 完成 OBSERVE、亲自读取真实证据后进入 AUDIT：

```text
进入 AUDIT Round <N>。
读取最新 state.md、review.md、appeal.md（如有）、本协议和实际交付物。
第二轮及以后先逐项关闭旧 issue，再检查 PLAN 与六个 gate。
把完整 AUDIT section 追加到 review.md；不要修改交付物。
Decision 只能是 PROCEED_TO_VERIFY、CONTINUE_FIX、ESCALATE_REPLAN、STOP_WITH_BLOCKER。
每个 issue 必须有唯一 ID、证据、fix_instruction 和可直接发送给 maker 的 fix_prompt。
同类根因连续出现两轮时使用 ESCALATE_REPLAN。
```

六个 gate：

- `contract`：goal、non-goals、assumptions、checklist、handoff、mode、stage path 与 recovery 均明确可查。
- `completeness`：结果完整满足用户目标，没有漏项或未经确认的范围扩张。
- `correctness`：逻辑、边界条件、结构和必要简洁性可接受，没有已知错误。
- `reuse_existing`：优先复用标准库、平台能力、项目代码和已安装依赖，没有无理由重造。
- `budget`：记录时间、工具、maker / delegate 调用、继续价值和停止信号。
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
- target_role: maker
- execution_order: <integer>
- prompt: |
    你是 maker，正在修正 issue <id>；不要处理其它问题。
    过程目录：<state path>。
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

`fix_prompt` 是父 Hermes checker 到 maker 的稳定接口：

- 每个阻塞 issue 恰好一段 prompt，并通过 ID 关联。
- prompt 必须自包含且可直接发送；不能依赖未写入过程文件的隐藏上下文。
- 多段 prompt 必须给 execution order；冲突由父 Hermes 在发出前解决。
- 父 Hermes 必须先把 prompt 写入 `review.md` 并记录 SHA-256，再原样发送；不得在传输时改写、合并、弱化或补全。

只有 `ISSUE_COUNT: 0`、PLAN PASS、六 gate 全 PASS、unresolved 为空且证据可复查时，才能 `PROCEED_TO_VERIFY`。

## 3. LOOP、Prompt 转发与 Appeal

收到 `CONTINUE_FIX` 后：

1. 父 Hermes 从 `review.md` 读取自己作为 checker 写出的完整 prompt，计算并记录 SHA-256。
2. 按 `execution_order` 将每段 prompt 原样发送到当前 `maker_session`。
3. maker 每次只处理对应 issue，不得扩张范围。
4. 父 Hermes 读取真实 diff 与命令输出，更新 OBSERVE。
5. 父 Hermes 先核对旧 issue closure，再重跑全部六 gate；不得让 maker 判定 closure。

maker 或用户认为 prompt 不可执行、证据错误或范围不当，可以提供反证。父 Hermes 将其写入 `appeal.md`：

```md
## [APPEAL] <issue id>
original_fix_prompt:
submitted_by: maker | user
reason:
counter_evidence:
```

父 Hermes 作为 checker 依据实际证据裁决：

- `UPHELD`：原 prompt 不变。
- `OVERRULED`：移除 issue，不计修正轮。
- `CLARIFIED`：写出完整 `replacement_fix_prompt`；旧 prompt 作废。

连续两轮只有 appeal、硬 blocker、预算上限或低价值继续时停止。相同 issue class 连续两轮复发时 `ESCALATE_REPLAN`；合约变化必须重新获得用户确认。

## 4. VERIFY

只有 AUDIT 为 `PROCEED_TO_VERIFY`，父 Hermes 才能进入 VERIFY：

```text
进入 VERIFY。独立重跑 checklist 中每个验证命令。
不要依赖 OBSERVE 或 maker 的结论；记录精确命令、实际输出或完整日志路径。
追加 VERIFY；不要修改交付物。
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
    <使用与 AUDIT 相同的直接执行结构>

DELIVERABLE_SUMMARY:
- changed:
- why:
- risks_or_limits:
- user_should_know:
```

`VERIFIED` 进入 BASELINE_LOCK；`RETURN_TO_LOOP` 原样发送新的 fix prompt；`STOP_WITH_BLOCKER` 停止并报告。

## 5. BASELINE 与 OPTIMIZE

VERIFY 为 `VERIFIED` 后，父 Hermes 只追加 Baseline，不改变交付物。记录 paths、checklist、证据、文件或 patch hash 和回滚入口。

随后进入 OPTIMIZE：

```text
进入 OPTIMIZE Round <N>。停止重复 correctness 审查，寻找可量化优化。
预扫描 changed files 与同目录逻辑相邻文件。
先写 optimize_todo：四个维度各一行标 pending，并逐条登记 OBSERVE / AUDIT / 前序轮次中已发现但未处理的可优化候选，防止遗漏。
四个维度缺一不可；NO_CANDIDATE 必须给具体理由。
每维度扫完把 todo 对应行更新为 done | deferred | no_candidate；deferred 项写入 inbox。
不要修改交付物。
```

`scanned_files` 必须非空且含真实路径。

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
    <OPTIMIZE_NOW 时使用与 fix_prompt 相同的目标、禁改、验证和回报结构>
- reason:

### conciseness — 不丢语义或行为地删除冗余、死代码、不必要间接层和过度抽象
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

- `OPTIMIZE_NOW`：真实优化；预期收益不少于 5%；低风险；无回归；无新依赖；无需确认；基线可检查；必须附可直接发送的 `optimize_prompt`。
- `DEFER_TO_INBOX`：有价值但缺用户上下文、依赖决定或当前数据。
- `STOP_OPTIMIZING`：已充分扫描，剩余收益低于 5%。
- `NO_CANDIDATE`：诚实搜索后无合理候选，必须有具体理由。
- `enrichment`：只能 `SUGGEST_TO_USER` 或 `NO_CANDIDATE`。

父 Hermes 先把 `OPTIMIZE_NOW` prompt 写入 `review.md` 并记录 SHA-256，再原样发送给 maker；执行后回到 AUDIT，再 VERIFY。

## 6. FINAL_VERIFY

优化停止或已复验通过后，父 Hermes 进入 FINAL_VERIFY：

```text
进入 FINAL_VERIFY。确认 baseline fingerprint、checklist、优化轮次和停止理由。
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

## 7. 恢复路由

恢复前读取实际存在的 `state.md`、`review.md`、`appeal.md` 和 `state/inbox.md`。过程文件恢复父 Hermes 的 checker 进度；只有 maker 需要显式 session 恢复。

### Maker 恢复

- maker 可恢复：按当前 phase 续跑同一 `maker_session`。
- maker 不可恢复：保留旧 ID，标记 `UNREACHABLE`，递增 `maker_generation`；将合约、真实 diff、已执行 prompts 和未决工作交给 replacement maker。
- provider、认证、quota 临时故障不是立即 replacement 的理由。
- 不要使用“最近 session”作为权威目标；精确 transport 见 mode reference。
- 不要创建独立 checker session；父 Hermes 从 `review.md` 继续审查。

### Phase 路由

- `user-confirm` 非空：先问用户。
- pending appeal：父 Hermes 根据反证裁决。
- 最新 AUDIT 为 `CONTINUE_FIX`：原样发送 fix prompts 给 maker。
- 最新 AUDIT 为 `ESCALATE_REPLAN`：先向用户提交合约更新。
- 最新 AUDIT 为 `PROCEED_TO_VERIFY`：父 Hermes 进入 VERIFY。
- 最新 VERIFY 为 `RETURN_TO_LOOP`：原样发送新 prompt。
- 最新 VERIFY 为 `VERIFIED` 且无 Baseline：BASELINE_LOCK。
- Baseline 已写且 OPTIMIZE 未开始：父 Hermes 进入 OPTIMIZE。
- OPTIMIZE_NOW 已执行但未复验：父 Hermes 回到 AUDIT。
- 优化停止或无候选：FINAL_VERIFY。
- 最新 FINAL_VERIFY 为 `VERIFIED`：DELIVER。
- blocker、预算上限、appeal deadlock 或低价值继续：停止并报告。

每次切换阶段前更新 `stage` 并在 `loop_todo` 对应项打勾；`loop_todo` 与 `stage` 冲突时以 `stage` 为准并立即修正 `loop_todo`。`loop_todo` 只追踪线性主链（PLAN → DELIVER），LOOP / ESCALATE_REPLAN 是 AUDIT 的内部出口，不单列。DELIVER 前必须有完整 AUDIT → VERIFY → BASELINE_LOCK → OPTIMIZE → FINAL_VERIFY 路径，且 `loop_todo` 除 DELIVER 外全部打勾。

## 8. 预算、辅助 Agent 与停止

- 记录 maker 的首次调用、每次 resume、修正轮、耗时、delegate 调用、继续价值和停止原因。
- 本技能授权父 Hermes 在任务能从并行或专长分工中实际受益时使用 `delegate_task`，不要求为每次普通委派另行确认；更高优先级指令、外部动作和不可逆操作仍照常受限。
- 只委派边界清楚、可独立、可验证的一次性任务；delegate agent 不替代 persistent maker 或 checker，不参与 AUDIT / VERIFY，其 self-report 不能直接作为证据。
- 把 auxiliary handoff、结果和父 Hermes 的独立验证写入 `state.md`；禁止 delegate agent 与 maker 并发修改重叠文件。若 delegate agent 写入隔离的子交付物，必须在 OBSERVE 前完成整合并纳入完整审查。
- 使用有界 maker turn cap；具体参数由 mode reference 与合约 stop guardrail 共同决定。

## 9. DELIVER

父 Hermes 汇总 changed、why、checklist、关键证据、风险和下一步。不要清空 maker session 或删除过程文件；只有用户能授权清理。
