# PLAN -> ACT -> AUDIT -> LOOP -> VERIFY 完整执行规范

> `SKILL.md` 保留核心规则。需要完整执行规范、审查 prompt 或降级细节时加载本文档。

## 1. PLAN

**谁做**：主 Agent

PLAN 是进入 ACT 的硬门槛，不是开场说明。用户要求跳过追问时，也必须把假设、风险和验收标准写进 `state/<slug>/loop_contract.md`。

### 输出

```md
## Plan

### Loop Contract
- 意图：
- 完成判定：
- 非目标：
- 假设/澄清：
- 停止护栏：最大修正 3 轮 / 改进<10%收敛 / 预算边界
- task-slug：
- Worktree: state/<slug>/
- Progress: state/<slug>/progress.md
- Shared auditor id: state/session_auditor_id.txt
- Task auditor pointer: state/<slug>/auditor_id.txt

### 执行步骤
1. [步骤名] - 做什么 + 做到什么程度 -> handoff: [文件路径/验证命令]

### 验收 Checklist
- [ ] 标准 - 可量化、二元、附证据要求

### 需加载的技能
- [skill] - [用途]
```

同时创建 `progress.md`，至少包含：done / tried / next / open / user-confirm / cost。`cost` 必须记录本轮耗时、调用的 agent/工具、是否值得继续、停止原因（如适用）。

### Plan Delta

第二轮起，只写变更部分。凡是需求、范围、步骤、验收项或 handoff 条件变化，先更新契约或写 Plan Delta，再执行。

```md
## Plan Delta
- 保持不变：
- 变更：
- 更新 Checklist：
- 变更原因：
```

## 2. ACT

**谁做**：主 Agent

- 首轮读 `loop_contract.md` 和 `progress.md`，执行步骤，满足 handoff 条件。
- 后续轮读 `feedback.md`、`final_verify.md` 的 `OPEN_ISSUES`（如有）和 `progress.md`，逐条执行修正指令。
- 执行前加载相关 skill，不用纯 prompt 猜测。
- 产出落盘，并在每轮结束后更新 `progress.md` 的 done/tried/next/open/user-confirm/cost。
- 不能自动继续的事项写入 `state/inbox.md`。

### 等待审查期间

审查 Agent 正在 AUDIT 时，主 Agent 可维护状态，但不得改变已提交审查的正式产物。

允许：更新 `progress.md`、补写 `inbox.md`、整理 handoff 证据、记录成本与阻塞、检查共享审查 Agent ID。

禁止：修改已提交审查的产物、新增未进契约的功能或自动化、预判审查结论、覆写 `feedback.md`。

## 3. RESUME

恢复 loop 时先读：

- `state/session_auditor_id.txt`
- `state/<slug>/auditor_id.txt`
- `state/<slug>/progress.md`
- `state/inbox.md`
- 上轮 `feedback.md`
- `final_verify.md`（如有）

路由：

- `user-confirm` 非空 -> 先问用户
- 有上诉待处理 -> 恢复同一审查 Agent 处理上诉
- `next` 指向未完成修正 -> 继续 ACT
- 上轮 `DECISION: PROCEED_TO_VERIFY` -> 恢复同一审查 Agent 进入 VERIFY
- `final_verify.md` 为 `VERDICT: VERIFIED` -> DELIVER
- `final_verify.md` 为 `VERDICT: RETURN_TO_LOOP` -> 读取 `OPEN_ISSUES` 后 LOOP
- `cost` 或停止原因显示低收益、硬上限、上诉死锁或阻塞 -> 停止并汇报

## 4. AUDIT

**谁做**：审查子 Agent

审查 Agent 必须跨轮、跨同系列任务存活。共享 ID 写入 `state/session_auditor_id.txt`；`state/<slug>/auditor_id.txt` 只是当前任务指针。只有无可续接共享 Agent、工作目录变化、任务系列不相关、用户明确要求重置时，才允许新建。

### 五门审查

1. **contract**：PLAN、Checklist、handoff、非目标、假设和审查输入包是否可检查；薄弱 PLAN 是 `weak_validation`。
2. **completeness**：是否满足用户目标，是否遗漏重点或越界扩张。
3. **correctness**：逻辑、边界、质量、可维护性和精简性是否影响完成判定；能删而不损失目标、重点和可验证性的内容，标为 `quality_issue`。
4. **budget**：是否记录并遵守时间、工具/agent 调用、token/成本、继续价值和停止信号；超预算、可降级或应停问用户时，标为 `budget_issue`。
5. **evidence_regression**：是否有文件路径、diff、命令输出或产物证据，是否破坏既有行为。

### 二轮后审查

从第二轮 AUDIT 开始，必须先验旧账、再查新账：

- 旧账：逐条确认上一轮 `ISSUES`、`OPEN_ISSUES`、上诉裁决和 Plan Delta 是否闭环。
- 新账：重新执行完整五门审查，检查修复是否引入新问题、回归、范围扩张、预算超支或证据断裂。
- 裁决：只有旧账全关、新账为零、五门全 PASS，才允许 `PROCEED_TO_VERIFY`。

只写“上轮问题已修复”但没有新一轮五门审查结果，判为 `weak_validation`。

### 审查 Prompt 模板

```text
你是独立审查员，跨轮存活，只审查不动手修改。

立场：默认不信任。主 Agent 的产出在证明正确前视为有问题。不确定就是 CONTINUE_FIX。

范围：只围绕 loop_contract.md、当前轮任务、验收 Checklist、变更证据、预算证据、上轮反馈或上诉审查。不得要求新增用户未要求的功能、runner 自动化、新脚本或复杂模块；范围外建议不得计入 ISSUE_COUNT。

AUDIT 步骤：
1. 读 state/<slug>/loop_contract.md、progress.md、inbox.md、上轮 feedback.md/appeal.md（如有）。
2. 先审 PLAN 质量。
3. 第二轮后先验旧账、再查新账。
4. 执行五门审查：contract / completeness / correctness / budget / evidence_regression。
5. 写 state/<slug>/feedback.md，严格使用固定格式。

PROCEED_TO_VERIFY 条件：
- ISSUE_COUNT: 0
- PLAN_CHECK verdict PASS
- 五门全 PASS
- VERIFY_HANDOFF.unresolved 为空
- 证据可检查
```

### feedback.md 固定格式

```md
DECISION: PROCEED_TO_VERIFY | CONTINUE_FIX | STOP_WITH_BLOCKER
ISSUE_COUNT: <number>

PLAN_CHECK:
- verdict: PASS | FAIL
- evidence:
- notes:

GATES:
- contract: PASS | FAIL
- completeness: PASS | FAIL
- correctness: PASS | FAIL
- budget: PASS | FAIL
- evidence_regression: PASS | FAIL

ISSUES:
1. failure_type: logic_error | requirement_gap | missing_edge_case | regression | quality_issue | budget_issue | missing_skill | weak_validation | external_blocker
   severity: blocker | major | minor
   evidence:
   fix_instruction:

APPEALS:
- item:
  ruling: UPHELD | OVERRULED | CLARIFIED
  reason:

VERIFY_HANDOFF:
- checklist_items_ready:
- evidence_paths:
- unresolved:
```

### 裁决路由

```text
if DECISION == PROCEED_TO_VERIFY:
    VERIFY by same auditor agent
elif DECISION == STOP_WITH_BLOCKER:
    report blocker and current state
elif DECISION == CONTINUE_FIX:
    if fix_round >= 3 + appeal_rounds: stop with hard limit
    elif marginal_improvement < 10% and no appeal round: converge and deliver current best
    else: LOOP
```

每次路由后更新 `progress.md` 的 cost。低收益暂停、硬上限、上诉死锁、阻塞或需要用户确认时，同时写入 `state/inbox.md`。

## 5. LOOP 与上诉

**谁做**：主 Agent 路由与执行；审查子 Agent 审查与裁决。

主 Agent 可对明显误判写 `state/<slug>/appeal.md`，但不得替审查 Agent 改写结论。

```md
## [APPEAL] 指令 3
原指令：
上诉理由：
反证：
```

审查 Agent 对每条上诉裁决：

- `UPHELD`：原指令成立，主 Agent 执行。
- `OVERRULED`：撤回，不计入修正轮。
- `CLARIFIED`：重写为更精确的修正指令。

连续 2 轮仅含上诉无实际修正，视为上诉死锁。

## 6. VERIFY

**谁做**：同一审查子 Agent

VERIFY 不是主 Agent 自证通过。审查子 Agent 对照 Checklist、`feedback.md` 和证据逐项最终验收，输出 `state/<slug>/final_verify.md`。

```md
VERDICT: VERIFIED | RETURN_TO_LOOP | STOP_WITH_BLOCKER

CHECKLIST:
1. item:
   verdict: PASS | FAIL
   evidence:

OPEN_ISSUES:
- failure_type:
  evidence:
  fix_instruction:

DELIVERABLE_SUMMARY:
- changed:
- why:
- risks_or_limits:
- user_should_know:
```

- `VERIFIED`：主 Agent 进入 DELIVER。
- `RETURN_TO_LOOP`：主 Agent 读取 `OPEN_ISSUES` 后回到 LOOP。
- `STOP_WITH_BLOCKER`：主 Agent 汇报阻塞和当前状态。

## 7. DELIVER

**谁做**：主 Agent

最终交付必须包含：

- 改了什么
- 为什么这样做
- 结果是否达标
- 风险/限制
- 用户后续需要知道什么
- 下一步建议

交付依据来自 `final_verify.md` 和 `progress.md`，不能由主 Agent 自行覆盖审查裁决。

## 8. 降级模式

优先使用子 Agent 或 CLI 独立审查。只有无可续接子 Agent 且 CLI 不可用时，才允许本地角色切换模拟审查，并在 `feedback.md` 明确写明降级原因。

```text
[角色切换：主 Agent -> 审查员]
读 state/ -> 必要验证 -> 五门审查 -> 写 feedback.md
[角色切换：审查员 -> 主 Agent]
```
