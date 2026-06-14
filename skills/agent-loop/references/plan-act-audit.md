# PLAN → ACT → AUDIT → LOOP → VERIFY — 完整执行规范

> SKILL.md 仅保留概览表。执行工作流时加载本文档。

---

## 1. PLAN（需求收敛与契约落盘）

**谁做**：主 Agent

### 1.1 苏格拉底式追问（首轮必须）

1. **诊断**：用一句话说出你认为用户真正要的结果
2. **点破模糊点**：指出 1-3 个会改变路线的不确定性
3. **追问取舍**：用具体选项确认优先级、边界、质量标准
4. **收敛落盘**：用户回答后转为 Loop Contract + Checklist 输出 PLAN

只问影响执行的问题。用户要求跳过时在 PLAN 中显式写假设和风险。

### 1.2 PLAN 输出格式

```markdown
## Plan（第 1 轮）

### Loop Contract
- 意图：[一句话]
- 完成判定：[可验证]
- 停止护栏：最大修正 3 轮 / 改进<10%收敛 / 资源预算[可选]
- 任务标识：[task-slug]（唯一，防止多次运行 state 冲突）
- Worktree: state/[task-slug]/

### 执行步骤
1. [步骤名] — 做什么 + 做到什么程度 → handoff: [文件路径/验证命令]
2. [步骤名] — 做什么 + 做到什么程度 → handoff: [...]

### 验收 Checklist
- [ ] 标准（可量化、二元、附证据）

### 需加载的技能
- [skill] — [用途]
```

### 1.3 步骤与 Handoff 设计规则

- **步骤 = 做什么 + 做到什么程度**。不写"写登录"，写"实现 POST /login 返回 JWT，错误返回 `{error:...}`"
- **每个步骤 ≥ 1 个 Checklist 项**，交叉覆盖不留盲区
- **Handoff 条件可自动判定**：文件存在/命令退出码/验证命令输出。handoff ≠ 验收（handoff 管"产出物存在"，质量交审查子 Agent）
- **Checklist 每项**：可量化（"pytest 0 failures"非"测试通过"）、二元（PASS/FAIL）、附证据要求

### 1.4 第 2 轮起 Delta 格式

只输出变更部分：

```markdown
## Plan Delta（第 N 轮）
### 保持不变的步骤
- 步骤 1–2 不变（上轮已 PASS）
### 变更步骤
3. [修正描述] — 修正指令见 state/feedback.md — 变更原因：[审查诊断]
### 更新 Checklist
- [unchanged] 标准 1
- [ ] 标准 2 — [修正后新标准]
```

首轮 PLAN 向用户确认后进入 ACT。后续 Delta 轮不询问。

---

## 2. ACT（主 Agent 执行）

**谁做**：主 Agent

- 首轮：读 `state/loop_contract.md`，执行步骤，满足 handoff 条件
- 后续轮：读 `state/feedback.md`，逐条执行 CONTINUE_FIX 修正指令
- **Skill-First**：执行前检索加载领域技能，禁止纯 Prompt 猜测
- **TaskCreate/TaskUpdate** 拆分工作
- 产出落盘 `state/`

---

## 3. AUDIT（持久化审查子 Agent）

**谁做**：审查子 Agent（`Agent` 工具派发）。核心：分离执行与审查。

### 主 Agent 操作（按环境选方案）

**持久化硬规则（所有方案通用）**：

- 审查 Agent 必须跨轮存活，**严禁每轮新建**。同一任务的审查始终是同一个 Agent 实例。
- 主 Agent 在首轮后必须先验证 `state/auditor_id.txt` 存在，再派发。如果 ID 丢失，报 STOP_WITH_BLOCKER。
- 新 Agent = 新上下文 = 丢失审查记忆 = 违反铁律 #1。

**方案 A — Claude Code 原生（默认）**：

1. 首轮 `Agent()` 派发 → 从返回值取 `agentId` → `echo "<id>" > state/auditor_id.txt`
2. **后续轮严禁 `Agent()` 新建**，必须先验证 `state/auditor_id.txt` 存在。如文件丢失 → STOP_WITH_BLOCKER（不可自动恢复，需用户重新启动循环）。必须 `SendMessage(to: read("state/auditor_id.txt"), ...)` 续对话。
3. 读 `state/feedback.md` 提取裁决

**方案 B — CLI 跨平台审查（Hermes 等无原生子 Agent 的环境）**：

审查 Agent 是一个独立 CLI 进程，通过 `--session-id` / `--resume` 跨轮存活。主 Agent 无需在同一个平台。

```bash
# 首轮：审查 Agent 的 prompt 要求它把结果写入 state/feedback.md
cat > state/audit_prompt.md << 'PROMPT'
[子 Agent prompt 模板，含四维度+输出格式+要求写入 state/feedback.md]
PROMPT
claude -p "$(cat state/audit_prompt.md)" --session-id $SESSION_ID
# 审查 Agent 已直接将结果写入 state/feedback.md，主 Agent 直接读取

# 后续轮：恢复同一会话
cat > state/audit_continue.md << 'PROMPT'
审查 Round N。主 Agent 已逐条执行你上一轮的修正指令。
本轮变更: [列出文件+改动]
请重新验证，更新 ISSUE_COUNT 和 IMPROVEMENT，更新 state/feedback.md。
PROMPT
claude -p "$(cat state/audit_continue.md)" --resume $SESSION_ID
# 审查 Agent 保持全部对话历史，只收增量，更新 state/feedback.md
```

**关键**：审查 Agent（无论方案 A 子 Agent 还是方案 B CLI）都**直接写 state/feedback.md**。主 Agent 只读取，不代为转换。这保持了分离令——主 Agent 不加工审查结果。

CLI 的 `--session-id` / `--resume` 提供持久化。`--session-id` 要求 UUID 格式（用 `uuidgen` 生成）。Codex CLI 同理（具体 flag 名参考其文档）。

**方案 C — 本地角色切换（无 CLI 可用时的兜底）**：

见第 6 节降级模式。

### 审查子 Agent Prompt 模板

```text
Agent(description: "AUDIT 审查子 Agent", subagent_type: "general-purpose", prompt: """
你是独立审查员，跨轮存活，只审查不动手修改。

## 你的立场：严格审查

审查标准：主 Agent 的产出在证明自己正确之前，默认视为有问题。你的工作是深度审查——如果确实没问题，给出 PASS 并附上每条维度的审查证据；如果有问题，写清修正指令。

**PROCEED_TO_VERIFY 的可操作标准（全部满足才给）**：

以下5条均为结构化可核验标准——每条均可通过解析 feedback.md 自动判定，不依赖审查员主观判断：

1. **证据闭环**：每条 Checklist 验收项在审查报告中有 ≥1 个文件路径引用 + ≥1 个命令输出证据。无证据的口头声称 = FAIL。
2. **四维全覆盖**：需求核对/问题分析/质量审查/回归检查各维度在审查报告中有 ≥1 行审查记录，即使结论是"无问题"也必须有记录。
3. **边界可核验**：契约中指定的边界场景（空输入/异常输入/边界值）有实际测试命令及输出。未指定边界的，审查员至少构造 1 个边界输入并记录结果。
4. **修正闭环**：上轮所有修正指令在本轮有文件级变更证据（diff 片段或文件内容引用）。首轮此项自动通过。
5. **零未解决问题**：ISSUE_COUNT = 0，且审查报告不包含任何未归类为 issue 的怀疑项。

标准 1-4 是过程检查（"审查员是否做了该做的事"），标准 5 是结果检查（"是否还有未解决的问题"）。全部满足 = 审查通过。任何一条不满足 = CONTINUE_FIX 并写明具体哪条未满足。

如果你不确定某条是否满足，那是 CONTINUE_FIX，不是 PROCEED_TO_VERIFY。但五条全部满足后，必须给 PROCEED_TO_VERIFY——不给同样是失职。

## 审查四维度

1. **需求核对** — 逐条对照 state/loop_contract.md Checklist。不光检查"有没有"，还要检查"对不对"、"全不全"。附证据(文件路径+命令输出)。口头声称无证据 = FAIL。需求理解偏差也算问题。
2. **问题分析** — 不只列现象，深挖根因。标注 failure_type:
   logic_error | requirement_gap | missing_edge_case | regression | quality_issue | missing_skill | weak_validation | external_blocker
   多个问题有共同根因时合并分析，不要碎片化列举。
3. **质量审查** — 不仅跑 linter/type checker。审视：结构是否合理、有无冗余代码、命名是否准确、错误处理是否真正管用（不是写了 try 就算）、边界条件是否覆盖。主动构造边界输入验证。
4. **回归检查** — 不仅跑已有测试。思考：这个改动可能影响哪些看似无关的模块？主动补充回归测试场景。测试覆盖不足本身就是问题。

## 常见陷阱（这些都是你的责任发现）

- PLAN 步骤写"实现登录"而非"POST /login 返回 JWT，错误返回 {error:...}" → weak_validation
- Checklist 项无法量化（"代码正确"）→ weak_validation
- 主 Agent 口头声称完成但无文件路径 → 证据不足，FAIL
- 测试只覆盖 happy path，无边界/异常测试 → missing_edge_case
- 本轮改动修复了 A 但破坏了 B → regression
- CLI 参数未经实际验证（应跑 --help 确认）→ logic_error

## 每轮步骤
1. 读 state/loop_contract.md → 2. 审查本轮变更文件 → 3. 运行测试+主动补充验证(跑 linter, 构造边界输入, 跑 --help 验证 CLI 参数) → 4. 统计 ISSUE_COUNT，对比上轮 → 5. 写 feedback.md

## 输出格式(严格遵循)

# 审查报告 — Round N

DECISION: PROCEED_TO_VERIFY | CONTINUE_FIX | STOP_WITH_BLOCKER
ISSUE_COUNT: N
PREV_ISSUE_COUNT: N
IMPROVEMENT: X% 或 N/A
(公式: (PREV_ISSUE_COUNT - ISSUE_COUNT) / PREV_ISSUE_COUNT × 100%，首轮写 N/A。仅填数字+%，不要附加文字)

## 1. 需求核对
| 验收项 | 状态 | 证据 |
|--------|------|------|
| 契约第1条: xxx | ✅/❌ | state/xxx.py:42 或命令输出 |

## 2. 问题分析
根因: [共同根因说明]

## 3. 质量审查
| 维度 | 评估 | 问题 |
|------|------|------|
| 结构/健壮性/可维护性 | ✅/⚠️/❌ | [说明] |

## 4. 回归检查
| 测试 | 结果 | 来源 |
|------|------|------|

## 修正指令(仅 CONTINUE_FIX)
### 指令 N: [标题]
**failure_type**: [类型]
**位置**: file:line
**根因**: [一句话]
**修正**: [可直接执行的操作。不要写"改进XX"，写"将第N行 XX 改为 YY"]

## 判定规则
- PROCEED_TO_VERIFY: 五条可操作标准全部满足 → 必须给通过。ISSUE_COUNT=0 且证据完整 = 推定通过，不可仅凭"可能还有问题"拒绝。
- CONTINUE_FIX: 任意一条标准未满足，或有未解决的 issue → 继续修正。必须指明具体哪条标准未满足。
- STOP_WITH_BLOCKER: 外部依赖/权限/需求矛盾等，主 Agent 无法自行修复。必须指明具体阻塞原因。

## 上诉处理(收到 [APPEAL] 时)
审查续轮消息中如含 [APPEAL] 标记的指令，你必须逐一裁决：
- UPHELD — 原修正指令成立，主 Agent 必须执行
- OVERRULED — 同意主 Agent，撤回该指令（不计入 ISSUE_COUNT）
- CLARIFIED — 原指令表述不清，重写为更精确的修正指令
对每条 [APPEAL] 给出裁决和理由。
""")
```

### 裁决路由

```
decision = grep "DECISION:" state/feedback.md
if PROCEED_TO_VERIFY → VERIFY
elif STOP_WITH_BLOCKER → 报告阻塞, 交付当前版本
elif CONTINUE_FIX:
    if fix_round >= 3 → 硬上限交付
    elif IMPROVEMENT < 10% → 收敛交付
    else → LOOP(逐条执行修正指令, 重新提交审查)
```

---

## 4. LOOP（迭代循环 + 上诉）

**谁做**：主 Agent（路由 + 上诉）+ 审查子 Agent（审查 + 上诉裁决）

### 上诉机制

主 Agent 不是审查子 Agent 的盲从执行器。如果认为某条修正指令是误判，可以上诉。

**上诉流程**：

1. 主 Agent 读 `state/feedback.md`，遇到认为有误的修正指令时，不直接执行
2. 写 `state/appeal.md`，逐条标注 `[APPEAL]`，附理由和反证
3. 在 SendMessage 恢复审查会话时，将 appeal.md 内容附在消息中
4. 审查子 Agent 逐条裁决：UPHELD / OVERRULED / CLARIFIED
5. 主 Agent 读裁决结果：
   - OVERRULED 的指令 — 不执行，不计入该轮修正
   - UPHELD 的指令 — 原样执行
   - CLARIFIED 的指令 — 按重写后版本执行

```markdown
# state/appeal.md

## [APPEAL] 指令 3: 修复 SKILL.md 铁律标题数量
**原指令**: 将 `## 四条铁律` 改为 `## 五条铁律`
**上诉理由**: 铁律0是"分离令"元规则，与其他4条性质不同。保守方案：改为"## 铁律（共5条）"不标注数字。
**反证**: 见 state/loop_contract.md 铁律#0 的语义——它是元规则而非约束规则。
```

**上诉轮不消耗修正轮数**（但计入总 AUDIT 轮数防止无限上诉）。被 OVERRULED 的指令不要求主 Agent 执行。

### 循环伪码

```
fix_round = 0
appeal_rounds = 0
while True:
    ACT: 读 feedback.md
         for each 修正指令:
             if 指令疑似误判:
                 appeal_rounds += 1
                 write state/appeal.md  # 标注 [APPEAL] + 理由
             else:
                 逐条执行
    AUDIT: SendMessage(msg含appeal.md) → 审查子 Agent 重新验证 + 上诉裁决 → 更新 feedback.md
    fix_round += 1
    read DECISION, IMPROVEMENT
    if PROCEED_TO_VERIFY or STOP_WITH_BLOCKER: break
    if fix_round >= 3 + appeal_rounds: break  # 硬上限，上诉轮额外
    if IMPROVEMENT < 10% and appeal_rounds == 0: break  # 收敛(上诉轮不触发收敛)
```

**主 Agent 只做路由决策和上诉标注，不自行分析问题。** 上诉不是让主 Agent 替代审查员——只是标记明显的误判请求复核。

自动化：`CronCreate`/`ScheduleWakeup`（CC）或 `runner-template.py`（通用）。

---

## 5. VERIFY（最终验收）

**谁做**：主 Agent

对照 Checklist 逐项验收 state/ 产出物：

```markdown
## Verification
- [x] 标准 1 — PASS（证据: state/xxx.py:42 + pytest 12 passed）
- [x] 标准 2 — PASS（证据: curl /login 返回 200）
结果：3/3 PASS | 修正 1 轮
```

- PROCEED_TO_VERIFY → 交付产出物清单 + 验收结果 + 修正历史 → 询问用户保留或清理 `state/<slug>/`
- 收敛/硬上限 → 交付当前最优版本 + 标注未达标项 + 终止原因
- STOP_WITH_BLOCKER → 交付当前版本 + 阻塞原因

---

## 6. 降级模式（无 CLI 也无子 Agent 时的最后兜底）

**优先用 CLI 跨平台审查（第 3 节方案 B），不要直接降级。** 只有 CLI 也不可用时，才由主 Agent 角色切换模拟审查。

```
[角色切换：主 Agent → 审查员]
读 state/ → 跑测试 → 四维审查 → 写 feedback.md(格式同子Agent版)
[角色切换：审查员 → 主 Agent]
```

| 方案 | 审查 Agent | 上下文隔离 | 持久化 | 推荐度 |
|------|-----------|----------|--------|--------|
| A. CC 原生 `Agent` | 子 Agent | 天然 | `SendMessage` | 首选 |
| B. CLI 跨平台 | 独立 CLI 进程 | 天然 | `--session-id`/`--resume` | Hermes 推荐 |
| C. 本地角色切换 | 主 Agent 自己 | 无 | 无 | 最后兜底 |

| 差异 | 子 Agent / CLI 版 | 本地角色切换 |
|------|-----------------|------------|
| 上下文 | 天然隔离 | 需角色切换声明 |
| 修正轮数 | ≤3 | 建议 ≤2（防上下文膨胀） |
| 审查质量 | 独立视角客观 | 同一模型可能偏宽松 |
