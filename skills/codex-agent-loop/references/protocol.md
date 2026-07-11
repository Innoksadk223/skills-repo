# Codex Agent Loop Protocol

进入首次 AUDIT 前完整读取本文件。它定义 Codex 原生 agent 调用、AUDIT / VERIFY / OPTIMIZE / FINAL_VERIFY 格式、appeal 与恢复路由。

## 目录

- [1. 原生 Agent 工具契约](#1-原生-agent-工具契约)
- [2. 首次生成 Reviewer](#2-首次生成-reviewer)
- [3. 复用、等待与纠偏](#3-复用等待与纠偏)
- [4. AUDIT](#4-audit)
- [5. LOOP 与 Appeal](#5-loop-与-appeal)
- [6. VERIFY](#6-verify)
- [7. BASELINE 与 OPTIMIZE](#7-baseline-与-optimize)
- [8. FINAL_VERIFY](#8-final_verify)
- [9. 恢复路由](#9-恢复路由)
- [10. 预算、辅助 Agent 与停止](#10-预算辅助-agent-与停止)
- [11. DELIVER](#11-deliver)

## 1. 原生 Agent 工具契约

直接调用当前 host 暴露的 multi-agent 工具；工具可能显示为裸名称，也可能带 `collaboration.` namespace。不要把这些调用包进 shell 或 `functions.exec`。

| 工具 | 语义 | 不要误用 |
| --- | --- | --- |
| `spawn_agent` | 创建新的 child agent；以返回的 canonical task name 为必有 handle，agent ID 仅在 host 实际返回时选记 | 不要每阶段重新创建 reviewer |
| `followup_task` | 给无进行中 turn 的 agent 发起下一 turn；运行中则在安全边界递交 | 不要用它制造第二个 reviewer |
| `send_message` | 给正在运行的 agent 补充消息，不主动启动 idle agent | idle agent 进入新阶段时不要只发消息 |
| `wait_agent` | 等待 mailbox 更新或用户输入 | 返回值只是通知，不是 verdict |
| `list_agents` | 查询当前根任务树中的 agent 与状态 | 不要扫描 `~/.codex/sessions/` 猜 handle |
| `interrupt_agent` | 中断当前 agent turn，agent 仍可继续复用 | 不要把中断当作删除 agent |

所有 agent 共享工作区，写入会立即互相可见。让主 Codex 独占交付物写入，让 reviewer 独占 `review.md` 写入；不要并发写同一文件。

在 `state.md` 记录：

```md
- audit_task: <spawn_agent 返回的 canonical task name；必填>
- audit_agent_id: <host 实际返回时记录；否则 UNAVAILABLE>
- audit_generation: 1
- audit_status: <原样记录 list_agents 的 host status；另允许 UNSPAWNED | INTERRUPTED | UNREACHABLE>
- audit_transport: direct_write | primary_verbatim
```

不要记录推测的 CLI session ID。根任务恢复和 child agent 续轮是两层不同的生命周期。

## 2. 首次生成 Reviewer

只在 OBSERVE 证据已落盘后生成 reviewer。使用唯一、短小、仅含小写字母数字和下划线的 `task_name`，并设置 `fork_turns="none"`，避免把主对话的判断直接复制给裁判。

```text
spawn_agent({
  "task_name": "audit_<slug>",
  "fork_turns": "none",
  "message": "<完整审查 handoff>"
})
```

完整 handoff 必须包含当前工作目录、process dir、交付物路径、当前 phase、允许写入的唯一文件和停止条件。使用以下模板：

```text
你是独立审查 agent。只审查，不修改交付物，也不要生成其它 agent。

工作目录：<absolute cwd>
过程目录：state/<slug>/
交付物：<明确文件列表>
当前阶段：AUDIT Round <N>

必须读取：
1. state/<slug>/state.md
2. state/<slug>/review.md（如存在）
3. state/<slug>/appeal.md（如存在）
4. state/inbox.md（如与本任务相关）
5. <codex-agent-loop>/references/protocol.md

先检查 PLAN 质量；第二轮及以后先关闭旧 issue，再运行六个 gate：
contract / completeness / correctness / reuse_existing / budget / evidence_regression。
为每个 issue 生成独立、可直接发送给主 Codex 的 fix_prompt。
不要采信主 agent 的总结；亲自读取 diff、文件、命令输出和日志。
只允许创建或追加 state/<slug>/review.md，不要修改 state.md 或任何交付物。
若实际权限不能写 review.md，不要绕过 sandbox；在 final 中返回完整、可原样落盘的 AUDIT block。
严格使用 protocol.md 的 AUDIT 格式和 decision。
```

生成后立即把 canonical task name 和 `audit_generation: 1` 写入 `state.md`。只有 host 实际返回独立 ID 时才记录 `audit_agent_id`；否则明确写 `UNAVAILABLE`，不得阻塞后续阶段。不要从 UI 文案或本地目录反推标识符。

### 只读 Reviewer 的转存兜底

若 reviewer 不能直接写 `review.md`：

1. 要求它在 final 中返回完整审查 block，不要只返回摘要。
2. 主 Codex 只能逐字转存，不得编辑、补判或重写。
3. 在 `state.md` 记录 `audit_transport: primary_verbatim`、内容 SHA-256 和来源 agent。
4. 任一内容变更都使审查无效，必须让 reviewer 重新出具。

不要声称 `sandbox_mode="read-only"` 的 custom agent 能直接写 `review.md`。也不要声称 custom agent 默认一定覆盖父任务的 live runtime override；以当前实际权限为准。

## 3. 复用、等待与纠偏

每个新阶段都复用同一 reviewer。

### Agent 无进行中 turn：触发下一阶段

```text
followup_task({
  "target": "<audit_task；仅当 host 接受时可用实际返回的 audit_agent_id>",
  "message": "进入 <PHASE>。重新读取 state.md、review.md 和 protocol.md；按对应格式追加结果。不要修改交付物。"
})
```

### Agent 正在运行：补充信息

```text
send_message({
  "target": "<audit_task；仅当 host 接受时可用实际返回的 audit_agent_id>",
  "message": "<只补充新证据、纠正路径或收紧范围>"
})
```

`send_message` 不会启动 idle agent。需要新 turn 时使用 `followup_task`。

### 等待与读取结果

```text
wait_agent({"timeout_ms": 60000})
list_agents({"path_prefix": "<audit task path prefix>"})
```

使用不超过 60 秒的有界等待；长任务期间持续向用户更新。`wait_agent` 只报告 mailbox 状态，返回后必须亲自读取 `review.md` 或 reviewer 的完整 final block。

### 中断

```text
interrupt_agent({"target": "<audit_task；仅当 host 接受时可用实际返回的 audit_agent_id>"})
```

只在 agent 明显跑偏、阶段需撤销或用户覆盖任务时中断。中断后记录原因；需要继续时仍对同一 target 使用 `followup_task`。

不要用 `create_thread`、`fork_thread`、`codex exec resume`、`--last` 或 `~/.codex/sessions/` 管理本流程的 child reviewer。那些能力属于用户任务或根 Codex thread 的生命周期，不是原生 child-agent handle。

## 4. AUDIT

AUDIT prompt：

```text
进入 AUDIT Round <N>。
读取最新 state.md、review.md、appeal.md（如有）和实际交付物。
先关闭旧 issue，再检查 PLAN 和六个 gate。
把一个完整 AUDIT section 追加到 review.md；不要修改其它文件。
Decision 只能是 PROCEED_TO_VERIFY、CONTINUE_FIX、ESCALATE_REPLAN 或 STOP_WITH_BLOCKER。
每个 issue 必须有唯一 ID、证据、fix_instruction 和可直接执行的 fix_prompt。
若同类根因连续出现两轮，使用 ESCALATE_REPLAN。
```

六个 gate 使用以下判定口径：

- `contract`：goal、non-goals、assumptions、checklist、handoff 与 recovery 均明确且可检查。
- `completeness`：结果完整满足用户目标，没有漏项或未经确认的范围扩张。
- `correctness`：逻辑、边界条件、结构和必要简洁性可接受，没有已知错误。
- `reuse_existing`：优先复用标准库、平台能力、项目现有代码与已安装依赖，没有无理由重造。
- `budget`：记录时间、工具、agent 调用、继续价值和停止信号，投入与风险相称。
- `evidence_regression`：每项结论有可复查证据，且没有破坏已知行为或引入未解释回归。

AUDIT section：

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
- target_role: primary_codex
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

`fix_prompt` 是 reviewer 到主 Codex 的稳定接口：每个阻塞 issue 恰好一段 prompt；多段 prompt 必须给 execution order；主 Codex 不得代写、合并、弱化或补全，只能原样执行或 appeal。

只有同时满足以下条件才能 `PROCEED_TO_VERIFY`：

- `ISSUE_COUNT: 0`
- PLAN_CHECK 为 PASS
- 六个 gate 全为 PASS
- unresolved 为空
- 证据可由路径或命令复查

## 5. LOOP 与 Appeal

收到 `CONTINUE_FIX` 后，主 Codex 按 `execution_order` 原样执行每段 `fix_prompt`，再更新 OBSERVE 证据。不要让 reviewer 实施修正，也不要顺手扩大范围。

无法接受 issue 时，把以下内容写入 `appeal.md`：

```md
## [APPEAL] <issue id>
original_fix_prompt:
reason:
counter_evidence:
```

对同一 reviewer 使用 `followup_task` 请求裁决：

- `UPHELD`：原 prompt 不变。
- `OVERRULED`：移除该 issue，不计修正轮。
- `CLARIFIED`：reviewer 必须给出完整 `replacement_fix_prompt`；旧 prompt 作废。

遇到硬上限、外部 blocker、低收益继续或连续两轮只有 appeal 而无实质进展时停止。相同 issue class 连续两轮复发时返回 `ESCALATE_REPLAN`；主 Codex 必须先向用户提交合约更新。

## 6. VERIFY

只有 AUDIT 为 `PROCEED_TO_VERIFY` 才能进入 VERIFY。对 idle reviewer 使用 `followup_task`：

```text
进入 VERIFY。
独立重跑 checklist 中每个验证命令，不要依赖 OBSERVE 的结论。
记录实际命令和原始输出或完整输出路径。
把 VERIFY section 追加到 review.md；不要修改交付物。
```

VERIFY section：

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
- failure_type:
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

## 7. BASELINE 与 OPTIMIZE

VERIFY 为 `VERIFIED` 后，主 Codex 只追加 Baseline，不改变交付物。记录 deliverable paths、checklist、证据、文件 hash 或 patch hash、回滚入口。

随后让同一 reviewer 切换为优化视角：

```text
进入 OPTIMIZE Round <N>。
停止重复正确性审查，开始寻找可量化优化。
先扫描 changed files 和同目录逻辑相邻文件。
使用四维 OPTIMIZE_TRIAGE 格式追加到 review.md。
先写 optimize_todo：四个维度各一行标 pending，并逐条登记 OBSERVE / AUDIT / 前序轮次中已发现但未处理的可优化候选，防止遗漏。
四个维度缺一不可；NO_CANDIDATE 必须给一行具体理由。
每维度扫完把 todo 对应行更新为 done | deferred | no_candidate；deferred 项写入 inbox。
不要修改交付物。
```

`scanned_files` 必须非空并包含真实路径；空列表、placeholder 或缺失都使整轮 triage 无效。

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

### functionality — 搜索并优先复用已有、项目内或开源的功能等价物；只比较功能实现，不复制 UI / 前端视觉
- candidate:
- expected_gain:
- cost:
- risk:
- affects_baseline:
- needs_user_approval:
- decision: OPTIMIZE_NOW | DEFER_TO_INBOX | STOP_OPTIMIZING | NO_CANDIDATE
- optimize_instruction:
- optimize_prompt: |
    <OPTIMIZE_NOW 时使用与 fix_prompt 同级别的目标、禁改、验证和回报结构>
- reason:

### conciseness — 在不丢失语义或行为的前提下，删除文字冗余、死代码、不必要间接层和过度抽象
- candidate:
- expected_gain:
- cost:
- risk:
- affects_baseline:
- needs_user_approval:
- decision: OPTIMIZE_NOW | DEFER_TO_INBOX | STOP_OPTIMIZING | NO_CANDIDATE
- optimize_instruction:
- optimize_prompt:
- reason:

### maintainability — 检查命名、文件与模块边界、依赖方向和重复逻辑，使局部修改可理解且安全
- candidate:
- expected_gain:
- cost:
- risk:
- affects_baseline:
- needs_user_approval:
- decision: OPTIMIZE_NOW | DEFER_TO_INBOX | STOP_OPTIMIZING | NO_CANDIDATE
- optimize_instruction:
- optimize_prompt:
- reason:

### enrichment — 承接前三维遗漏、合约外增强和新增产品能力；始终先向用户建议，禁止自动执行
- candidate:
- expected_gain:
- cost:
- risk:
- affects_baseline:
- needs_user_approval: ALWAYS
- decision: SUGGEST_TO_USER | NO_CANDIDATE
- suggestion:
- reason:
```

决策规则：

- `OPTIMIZE_NOW`：真实优化而非 correctness fix；预期收益不少于 5%；低风险；无回归；不增加依赖；无需用户确认；基线仍可检查；必须附可直接执行的 `optimize_prompt`。
- `DEFER_TO_INBOX`：有价值，但缺少用户上下文、依赖决定或当前扫描拿不到的数据。
- `STOP_OPTIMIZING`：该维度已充分扫描，剩余收益低于 5%。
- `NO_CANDIDATE`：诚实搜索后没有合理候选，必须写具体理由。
- `enrichment`：只能 `SUGGEST_TO_USER` 或 `NO_CANDIDATE`，绝不自动执行。

归类示例：发现可替代当前实现的已有功能等价物，放入 `functionality`；提出新增批注、主题切换或其它产品能力，放入 `enrichment` 并使用 `SUGGEST_TO_USER`。

四个维度全部 `NO_CANDIDATE` 时，主 Codex 必须检查理由是否充分；理由空泛则让 reviewer 重新扫描。主 Codex 原样执行 `OPTIMIZE_NOW` 的 prompt 后，仍用同一 reviewer 重新 AUDIT 和 VERIFY。

## 8. FINAL_VERIFY

优化停止、不可执行或已复验通过后，对同一 reviewer 使用 `followup_task`：

```text
进入 FINAL_VERIFY。
确认 baseline fingerprint、checklist、优化轮次和停止理由。
检查 loop_todo 除 DELIVER 外全部打勾，且 optimize_todo 全部 closed（done | deferred | no_candidate），无 pending；否则 RETURN_TO_BASELINE。
检查当前交付物未脱离已验证基线；追加 FINAL_VERIFY section。
不要修改交付物。
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

只有 `VERDICT: VERIFIED` 才能进入 DELIVER。

## 9. 恢复路由

恢复前读取实际存在的 `state.md`、`review.md`、`appeal.md` 和 `state/inbox.md`。

### 先恢复 Agent handle

1. 对 `audit_task` 的 canonical prefix 调用 `list_agents`。
2. 找到同一 agent：
   - RUNNING：等待，必要时 `send_message`。
   - 无进行中 turn（host 可能表示为 IDLE、DONE 或 COMPLETED）：按当前 phase 使用 `followup_task`。
   - INTERRUPTED：记录原因后用 `followup_task` 继续或升级。
3. 找不到、当前根任务已更换或 handle 不可达：
   - 把旧 handle 标为 `UNREACHABLE`，保留历史。
   - 递增 `audit_generation`。
   - 用 `fork_turns="none"` 生成 `audit_<slug>_g<N>` replacement reviewer。
   - handoff 中明确 predecessor、全部过程文件和最后未决 issue。
   - 要求 replacement 先核对旧 issue closure，再继续当前 phase。

状态文件是跨根任务恢复的权威接口；不要试图用 `codex exec resume` 或扫描 session 目录恢复 child agent。

### 再按阶段路由

- `user-confirm` 非空：先问用户。
- pending appeal：让同一 reviewer 裁决。
- `next` 指向未完成修正：主 Codex 进入 ACT。
- 最新 AUDIT 为 `CONTINUE_FIX`：主 Codex 进入 LOOP。
- 最新 AUDIT 为 `ESCALATE_REPLAN`：提交合约更新给用户；确认前不改交付物。
- 最新 AUDIT 为 `PROCEED_TO_VERIFY`：同一 reviewer 进入 VERIFY。
- 最新 VERIFY 为 `RETURN_TO_LOOP`：主 Codex 修正。
- 最新 VERIFY 为 `VERIFIED` 且无 Baseline：进入 BASELINE_LOCK。
- Baseline 已存在且优化未开始：进入 OPTIMIZE。
- OPTIMIZE_NOW 已执行但未复验：回到 AUDIT。
- 优化停止或无候选：进入 FINAL_VERIFY。
- 最新 FINAL_VERIFY 为 `VERIFIED`：进入 DELIVER。
- blocker、硬上限、appeal deadlock 或低价值继续：停止并报告。

每次切换阶段前更新 `state.md` 的 `stage` 并在 `loop_todo` 对应项打勾；`loop_todo` 与 `stage` 冲突时以 `stage` 为准并立即修正 `loop_todo`。`loop_todo` 只追踪线性主链（PLAN → DELIVER），LOOP / ESCALATE_REPLAN 是 AUDIT 的内部出口，不单列。DELIVER 前必须有完整 AUDIT → VERIFY → BASELINE_LOCK → OPTIMIZE → FINAL_VERIFY 路径，且 `loop_todo` 除 DELIVER 外全部打勾。

## 10. 预算、辅助 Agent 与停止

- 整个任务只保留一个可达 reviewer；replacement 只用于 handle 真正失效。
- 把 agent 调用次数、修正轮、耗时、继续价值和停止原因写入 `state.md`。
- 使用有界等待并更新用户，不用长时间阻塞调用掩盖无进展。
- 本技能授权主 Codex 在任务能从并行或专长分工中实际受益时派出 auxiliary agent，不要求为每次普通委派另行确认；更高优先级指令、外部动作和不可逆操作仍照常受限。
- 只委派可独立、边界清楚、可验证的一次性工作；使用不同 task name，把 handoff、结果和验证写入 state。auxiliary agent 不参与 AUDIT / VERIFY、不替代 reviewer，其 self-report 不能直接作为证据。
- auxiliary agent 若修改隔离的子交付物，该输出按 maker-side 工作处理，必须在 OBSERVE 前完成整合并由 reviewer 纳入完整审查。
- 避免多个 agent 并发修改重叠文件；并行优先用于只读探索、测试、日志分析和资料核验。

## 11. DELIVER

主 Codex 从 `state.md` 和 `review.md` 汇总 changed、why、checklist、关键命令、风险和下一步。不要自行清空 agent handle 或删除过程文件；只有用户能授权清理。
