---
name: agent-loop
description: "双Agent闭环工作流。主Agent执行(ACT)→独立审查子Agent五门审查+输出DECISION/failure_type修正指令(AUDIT)→主Agent逐条修正后重新提交(LOOP)→审查子Agent最终验收(VERIFY)→主Agent交付(DELIVER)。触发:/agent-loop,或多轮迭代+独立验证的高质量任务。"
---

# Agent Loop

**"不要再去提示 Agent 了。去设计一个循环，让循环来提示 Agent。"** — Boris Cherny & Peter Steinberger

一个模型审查自己的产出总是过于宽容。**分离执行者与审查者**是循环收敛的关键。主 Agent 执行，独立审查子 Agent 验证并写出可直接执行的修正指令，循环直到审查通过或触发终止。

## 参考资源

- `references/contract-template.md`：创建 `loop_contract.md` 时复制并按任务填写。
- `references/plan-act-audit.md`：需要完整执行规范、审查 prompt 或降级细节时加载。
- `references/runner-template.py`：实验性 CLI 调度模板；使用前必须检查并按当前平台调整。

## PLAN 契约门

PLAN 不是开场说明，而是进入 ACT 的硬门槛。没有 `state/<slug>/loop_contract.md` 和 `progress.md`，不得开始正式执行；用户要求跳过追问时，也必须把假设、风险和验收标准写进契约。

PLAN 至少包含：

- 意图：用户真正要达成什么
- 非目标：本轮明确不做什么，防止审查扩张
- 假设/澄清：影响路线但无法继续追问时的默认判断
- 执行步骤：每步写“做什么 + 做到什么程度”
- handoff 条件：产物路径、命令输出或可检查证据
- 验收 Checklist：可量化、二元、附证据要求
- 预算/成本边界：时间、工具/agent 调用、继续价值或停止信号；用户未给预算时写默认成本判断
- 审查输入包：AUDIT 需要读哪些文件和证据
- 恢复入口：下一轮从 `progress.md` 的哪些字段继续

PLAN 写不清，后续做得再多也只是放大误差。审查 Agent 必须把薄弱 PLAN 视为 `weak_validation`：目标不清、Checklist 不可验证、步骤没有 handoff、非目标缺失、假设未落盘，均不得 `PROCEED_TO_VERIFY`。

## 审查 Handoff

每轮 AUDIT 前，主 Agent 必须把同一个审查 Agent 需要的最小上下文包交清楚：

- 用户目标：用户真正要达成什么
- 非目标：本轮明确不做什么
- 计划：`state/<slug>/loop_contract.md` 中的步骤与验收 Checklist
- 当前轮任务：本轮是在首轮执行、修正、上诉还是最终验证
- 变更证据：文件路径、diff 摘要、命令输出或产出物路径
- 预算证据：`progress.md` 的 cost、工具/agent 调用、耗时、继续价值或停止原因
- 上轮反馈或上诉：`feedback.md` / `appeal.md` 路径，无则写“首轮无上轮反馈”
- 审查 Agent 作用域：当前会话、工作目录、任务系列、共享审查 Agent ID

审查子 Agent 只能按 `loop_contract.md`、当前轮任务和上述证据审核；缺少这些输入时，先要求补齐 handoff，不凭空扩展任务。AUDIT 还必须先审 PLAN 本身：契约不完整、验收不可判定、handoff 不可检查、范围边界缺失时，先退回修 PLAN，不继续审产物。AUDIT 前必须先查共享审查 Agent ID，不能因为 task-slug 变化就默认新建审查 Agent。

## 工作流

| 步 | 谁做 | 做什么 | 产物 |
|----|------|--------|------|
| 1. PLAN | 主 Agent | 苏格拉底式追问/显式假设 → 步骤设计 → handoff/Checklist → 生成 task-slug → 契约落盘；未完成不得 ACT | `state/<slug>/loop_contract.md` + `progress.md` |
| 2. ACT | 主 Agent | 执行步骤，满足 handoff 条件，产出落盘；更新进度脊柱 | 产出文件 + `progress.md` |
| 3. AUDIT | **审查子 Agent** | 先审 PLAN 质量，再按五门审查(契约/完成度/正确性/预算/证据回归) + failure_type 分类 → DECISION 三态裁决 | `state/<slug>/feedback.md` |
| 4. LOOP | 主 Agent | 读 DECISION → CONTINUE_FIX 则逐条执行修正指令（可[APPEAL]误判指令）→ 必要时输出 Plan Delta → 更新 progress → 重新提交审查 | 迭代至终止 |
| 5. VERIFY | **审查子 Agent** | 对照 Checklist 逐项最终验收，确认所有阻塞问题关闭，输出可否交付裁决 | `state/<slug>/final_verify.md` |
| 6. DELIVER | 主 Agent | 读取 `final_verify.md`，做理解交付，询问用户是否保留或清理 state | 最终回复 + `progress.md` |

### 审查输出格式

AUDIT 只保留五个检查门，避免散文式审查：

- 契约：PLAN、Checklist、handoff、非目标和假设是否可检查
- 完成度：是否满足用户目标，是否遗漏重点或越界扩张
- 正确性：逻辑、边界、质量、可维护性和精简性是否有直接影响完成判定的问题；能删而不损失目标、重点和可验证性的内容，必须要求删减
- 预算：是否记录并遵守时间、工具/agent 调用、token/成本、继续价值和停止信号；投入明显超过收益、可降级或应停问用户时，必须指出
- 证据回归：是否有文件路径、diff、命令输出或产物证据，是否破坏既有行为

`feedback.md` 必须使用固定格式：

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

### 二轮后审查

从第二轮 AUDIT 开始，审查 Agent 不得只复核上一轮 `ISSUES` 是否已修。每轮都必须先验旧账、再查新账：

- 旧账：逐条确认上一轮 `ISSUES`、`OPEN_ISSUES`、上诉裁决和 Plan Delta 是否闭环
- 新账：重新执行完整五门审查，检查修复是否引入新问题、回归、范围扩张、预算超支或证据断裂
- 裁决：只有旧账全关、新账为零、五门全 PASS，才允许 `PROCEED_TO_VERIFY`

如果第二轮之后的 `feedback.md` 只写“上轮问题已修复”而没有新一轮五门审查结果，必须判为 `weak_validation`。

`PROCEED_TO_VERIFY` 只能在 `ISSUE_COUNT: 0`、五门全 PASS、`VERIFY_HANDOFF.unresolved` 为空时给出。非阻塞建议可写入 notes，但不得伪装成必须修复的问题。

### 长期状态脊柱

`state/<slug>/progress.md` 是跨轮记忆，不替代 `feedback.md`。每轮开始前先读，结束后更新：

- done：已经完成并有证据的事项
- tried：尝试过的方案、失败原因、上诉结果
- next：下一步动作或停止后的建议
- open：未解决问题、阻塞、风险
- user-confirm：需要用户确认的取舍或外部动作
- cost：本轮耗时、调用的 agent/工具、是否值得继续、停止原因（如适用）

每轮必须把耗时、工具/agent、继续价值或停止原因写入 `progress.md` 或契约的当前轮状态区。

### 等待审查期间

审查 Agent 工作时，主 Agent 不必空转，但只能维护状态，不得改变正在被审查的正式产物：

- 允许：更新 `progress.md` 的 done/tried/next/open/user-confirm/cost、补写 `state/inbox.md`、整理 handoff 证据、记录等待中的阻塞或成本
- 禁止：修改本轮已提交审查的产出文件、追加未进契约的新功能、替审查 Agent 预判结论或提前执行假想修正

审查 Agent 在 `feedback.md` 中负责指出状态遗漏；主 Agent 只按反馈修正，不新增独立记忆维护 Agent。

### 待处理箱

`state/inbox.md` 是跨任务待处理箱，不替代单个任务的 `progress.md`。主 Agent 负责写入；审查 Agent 只读，并在 `feedback.md` 中指出遗漏。

遇到以下任一情况，主 Agent 必须写入 `state/inbox.md`：

- 需要用户确认才能继续
- 外部依赖、权限、网络、账号、API key 阻塞
- 改进 < 10% 后收敛暂停
- 达到修正硬上限
- 连续上诉死锁
- 有不阻塞本次交付、但需要后续决策的风险

每条记录包含：任务标识、优先级、原因、当前状态、建议动作、来源文件。

### 恢复规则

恢复 loop 时，先读 `state/<slug>/loop_contract.md`、`state/<slug>/progress.md` 的 `next/open/user-confirm/cost` 和 `state/inbox.md`，再决定路由：

- `user-confirm` 非空：先问用户，暂停自动执行
- 有上诉待处理：恢复同一审查会话处理上诉
- `next` 指向未完成修正：先确认是否需要 Plan Delta，再继续 ACT
- 上轮 `DECISION: PROCEED_TO_VERIFY`：恢复同一审查 Agent 进入 VERIFY
- 已有 `final_verify.md` 且结论为 `VERDICT: VERIFIED`：进入 DELIVER
- 已有 `final_verify.md` 且结论为 `VERDICT: RETURN_TO_LOOP`：读取 `OPEN_ISSUES`，回到 LOOP 修正
- `cost` 或停止原因显示低收益、硬上限、上诉死锁或阻塞：停止并汇报

凡是需求、范围、步骤、验收项或 handoff 条件发生变化，必须先更新 `loop_contract.md` 或写 Plan Delta，再执行修正。只改产物、不改契约，是下一轮 AUDIT 的 `weak_validation`。

### 最终验收与交付

VERIFY 不是主 Agent 自证通过；最终验收由审查子 Agent 执行。`final_verify.md` 必须使用固定格式：

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

`VERIFIED` 只能在 Checklist 全 PASS、无 open issues、证据可检查时给出。若发现新问题，返回 `RETURN_TO_LOOP` 并写入可执行修正指令；主 Agent 不得自行覆盖该裁决。

DELIVER 由主 Agent 执行。最终交付缺少以下任一项，不得视为完成：

- 改了什么
- 为什么这样做
- 风险/限制
- 用户后续需要知道什么

最终交付还必须包含产品经理对老板汇报式摘要：

- 本次完成了什么
- 为什么这样做
- 结果是否达标
- 风险与遗留问题
- 下一步建议

### 终止条件 (满足其一即停)

1. VERIFIED — 审查子 Agent 最终验收通过
2. STOP_WITH_BLOCKER — 无法自动修复的阻塞
3. 边际改进 < 10% — 收敛，交付当前最优版本（上诉轮不触发收敛）
4. 3 轮修正硬上限 — 强制交付（每有 1 轮上诉则上限 +1）
5. 连续 2 轮仅含上诉无实际修正 → 上诉死锁，强制交付

## 铁律

**0. 分离令（#1 陷阱）** — 主 Agent 严禁审查自己产出或替审查子 Agent 写 prompt。修正指令原样转发。

**1. 持久化审查** — 同一会话、同一工作目录、同一系列任务必须复用同一个审查 Agent。`state/<slug>/` 继续隔离任务产物，但审查 Agent 身份按 session/workdir/series 复用。共享 ID 写入 `state/session_auditor_id.txt`；`state/<slug>/auditor_id.txt` 只是指向该共享审查 Agent 的指针或拷贝，不代表每个 task-slug 都新建 Agent。后续轮**严禁新建 Agent**，必须 `SendMessage` 续对话（或 CLI `--resume`）。只有没有可续接共享审查 Agent、工作目录变化、任务系列不相关、用户明确要求重置时，才允许创建新审查 Agent。新建 = 丢失审查记忆 = 违规。

**2. 固定严格** — 审查子 Agent 的立场是"默认不信任"。agent-loop 不提供轻量/标准/严格分级；恢复、降级和审查 prompt 均按严格五门审查与既有通过标准执行。PROCEED_TO_VERIFY 需满足证据闭环、五门全 PASS、边界可核验、修正闭环、零未解决问题；VERIFIED 还必须逐项通过最终 Checklist，不是默认结局。

**3. Prompt 不是意见** — 每条修正指令含 `failure_type`（logic_error/requirement_gap/missing_edge_case/regression/quality_issue/budget_issue/missing_skill/weak_validation/external_blocker），主 Agent 逐条执行。

**4. 证据零容忍** — 口头 PASS 无文件路径或命令输出 = FAIL。

**5. 上诉权** — 主 Agent 可对认为误判的修正指令提 `[APPEAL]`，写 `state/appeal.md` 附理由和反证。审查子 Agent 必须在下一轮逐条裁决 UPHELD/OVERRULED/CLARIFIED。被 OVERRULED 的指令不执行且不计入修正轮数。上诉不是让主 Agent 替代审查——只是标记明显误判请求复核。

**6. 范围刹车** — 审查严格不等于无限加功能。修正指令只能针对契约、证据、回归或质量中直接影响完成判定的问题；用户未要求的功能、runner 自动化、新脚本、复杂模块化只能作为非阻塞备注，不计入 ISSUE_COUNT。审查 Agent 还必须检查产物是否过度膨胀：不损失目标、重点和可验证性的删减应作为 `quality_issue` 要求执行。

## 平台适配

**审查 Agent 不需要和主 Agent 跑在同一个平台。** 关键是审查者有独立上下文、跨轮存活。

### 方案优先级

| 优先级 | 主 Agent 环境 | 审查 Agent 实现 | 持久化方式 |
|--------|-------------|----------------|-----------|
| **默认** | Claude Code | `Agent` 工具派发子 Agent | `SendMessage` 续对话 |
| **备选 1** | Codex | Codex sub-agent | 同上机制 |
| **备选 2** | Hermes / 任意 | Claude Code CLI（独立进程） | `--session-id` 命名会话 + `--resume` 续接 |
| **备选 3** | Hermes / 任意 | Codex CLI（独立进程） | 同上 CLI 会话机制 |
| **降级模式（兜底）** | 无 CLI 可用 | 主 Agent 角色切换模拟审查 | `[角色切换]` 协议，≤2 轮 |

Codex 执行时，若可用 sub-agent/thread 续接机制，AUDIT 前先读 `state/session_auditor_id.txt` 并判断是否同会话、同工作目录、同系列任务；命中则复用该 ID。只有满足允许新建的例外条件时，才创建审查 Agent，捕获可续接 ID 写入 `state/session_auditor_id.txt`，并让 `state/<slug>/auditor_id.txt` 指向它；若当前 Codex 无可续接机制，直接使用 CLI 备选方案或降级模式，并在 `feedback.md` 说明降级原因。

### CLI 跨平台审查（备选 2/3）

主 Agent（Hermes）通过 CLI 启动独立审查进程，利用 CLI 的会话持久能力：

```bash
# AUDIT 前：同一会话/同一工作目录/同一系列任务优先复用共享审查会话
if [ -f state/session_auditor_id.txt ]; then
  SESSION_ID="$(cat state/session_auditor_id.txt)"
else
  # 仅在无可续接共享 Agent / 工作目录变化 / 任务系列不相关 / 用户明确重置时创建
  SESSION_ID=$(uuidgen)  # --session-id 要求 UUID 格式
  printf "%s\n" "$SESSION_ID" > state/session_auditor_id.txt
fi
mkdir -p "state/$TASK_SLUG"
printf "%s\n" "$SESSION_ID" > "state/$TASK_SLUG/auditor_id.txt"

# 首次共享会话：创建命名会话，审查 Agent 直接写 state/<slug>/feedback.md
claude -p "$(cat state/audit_prompt.md)" --session-id "$SESSION_ID"
# 同系列后续轮/后续任务：恢复同一共享会话，审查 Agent 更新 state/<slug>/feedback.md
claude -p "$(cat state/audit_continue.md)" --resume "$SESSION_ID"
```

审查 Agent 的 CLI 进程跨轮、跨同系列任务存活（通过 `--session-id` / `--resume`），不每轮或每个 task-slug 新建。主 Agent 只负责读写 state/ 文件、做路由决策。

### 循环调度

| Claude Code | Codex | Hermes / 通用 |
|-------------|-------|--------------|
| `CronCreate` / `ScheduleWakeup` | cron / hook | `while`+sleep / cron |
