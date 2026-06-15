---
name: agent-loop
description: "双Agent闭环工作流。主Agent执行(ACT)→独立审查子Agent四维审查+输出DECISION/failure_type修正指令(AUDIT)→主Agent逐条修正后重新提交(LOOP)→直到PROCEED_TO_VERIFY或触发终止条件。审查子Agent持久交互跨轮存活。触发:/agent-loop,或多轮迭代+独立验证的高质量任务。"
---

# Agent Loop

**"不要再去提示 Agent 了。去设计一个循环，让循环来提示 Agent。"** — Boris Cherny & Peter Steinberger

一个模型审查自己的产出总是过于宽容。**分离执行者与审查者**是循环收敛的关键。主 Agent 执行，独立审查子 Agent 验证并写出可直接执行的修正指令，循环直到审查通过或触发终止。

## 审查 Handoff

每轮 AUDIT 前，主 Agent 必须把同一个审查 Agent 需要的最小上下文包交清楚：

- 用户目标：用户真正要达成什么
- 非目标：本轮明确不做什么
- 计划：`state/<slug>/loop_contract.md` 中的步骤与验收 Checklist
- 当前轮任务：本轮是在首轮执行、修正、上诉还是最终验证
- 变更证据：文件路径、diff 摘要、命令输出或产出物路径
- 上轮反馈或上诉：`feedback.md` / `appeal.md` 路径，无则写“首轮无上轮反馈”

审查子 Agent 只能按 `loop_contract.md`、当前轮任务和上述证据审核；缺少这些输入时，先要求补齐 handoff，不凭空扩展任务。

## 工作流

| 步 | 谁做 | 做什么 | 产物 |
|----|------|--------|------|
| 1. PLAN | 主 Agent | 苏格拉底式追问 → 步骤设计 → handoff/Checklist → 生成 task-slug → 契约落盘 | `state/<slug>/loop_contract.md` |
| 2. ACT | 主 Agent | 执行步骤，满足 handoff 条件，产出落盘 | 产出文件 |
| 3. AUDIT | **审查子 Agent** | 四维审查(需求/问题/质量/回归) + failure_type 分类 → DECISION 三态裁决 | `state/<slug>/feedback.md` |
| 4. LOOP | 主 Agent | 读 DECISION → CONTINUE_FIX 则逐条执行修正指令（可[APPEAL]误判指令）→ 重新提交审查 | 迭代至终止 |
| 5. VERIFY | 主 Agent | 对照 Checklist 逐项验收 state/<slug>/ 产出物 → 询问用户是否保留或清理 state | 交付/收敛报告 |

### 终止条件 (满足其一即停)

1. PROCEED_TO_VERIFY — 审查通过
2. STOP_WITH_BLOCKER — 无法自动修复的阻塞
3. 边际改进 < 10% — 收敛，交付当前最优版本（上诉轮不触发收敛）
4. 3 轮修正硬上限 — 强制交付（每有 1 轮上诉则上限 +1）
5. 连续 2 轮仅含上诉无实际修正 → 上诉死锁，强制交付

## 铁律

**0. 分离令（#1 陷阱）** — 主 Agent 严禁审查自己产出或替审查子 Agent 写 prompt。修正指令原样转发。

**1. 持久化审查** — 首轮 `Agent` 派发并捕获 `agentId` → `state/<slug>/auditor_id.txt`。后续轮**严禁新建 Agent**，必须 `SendMessage` 续对话（或 CLI `--resume`）。新建 = 丢失审查记忆 = 违规。主 Agent 在每轮 AUDIT 前必须先验证 `state/<slug>/auditor_id.txt` 存在。

**2. 默认严格** — 审查子 Agent 的立场是"默认不信任"。PROCEED_TO_VERIFY 需满足五条可操作标准（证据闭环/四维全覆盖/边界可核验/修正闭环/零未解决问题），不是默认结局。

**3. Prompt 不是意见** — 每条修正指令含 `failure_type`（logic_error/requirement_gap/missing_edge_case/regression/quality_issue/missing_skill/weak_validation/external_blocker），主 Agent 逐条执行。

**4. 证据零容忍** — 口头 PASS 无文件路径或命令输出 = FAIL。

**5. 上诉权** — 主 Agent 可对认为误判的修正指令提 `[APPEAL]`，写 `state/appeal.md` 附理由和反证。审查子 Agent 必须在下一轮逐条裁决 UPHELD/OVERRULED/CLARIFIED。被 OVERRULED 的指令不执行且不计入修正轮数。上诉不是让主 Agent 替代审查——只是标记明显误判请求复核。

**6. 范围刹车** — 审查严格不等于无限加功能。修正指令只能针对契约、证据、回归或质量中直接影响完成判定的问题；用户未要求的功能、runner 自动化、新脚本、复杂模块化只能作为非阻塞备注，不计入 ISSUE_COUNT。

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

Codex 执行时，若可用 sub-agent/thread 续接机制，首轮必须捕获可续接 ID 并写入 `state/<slug>/auditor_id.txt`，后续轮用该 ID 续接；若当前 Codex 无可续接机制，直接使用 CLI 备选方案或降级模式，并在 `feedback.md` 说明降级原因。

### CLI 跨平台审查（备选 2/3）

主 Agent（Hermes）通过 CLI 启动独立审查进程，利用 CLI 的会话持久能力：

```bash
SESSION_ID=$(uuidgen)  # --session-id 要求 UUID 格式
# 首轮：创建命名会话，审查 Agent 直接写 state/feedback.md
claude -p "$(cat state/audit_prompt.md)" --session-id "$SESSION_ID"
# 后续轮：恢复同一会话，审查 Agent 更新 state/feedback.md
claude -p "$(cat state/audit_continue.md)" --resume "$SESSION_ID"
```

审查 Agent 的 CLI 进程跨轮存活（通过 `--session-id` / `--resume`），不每轮新建。主 Agent 只负责读写 state/ 文件、做路由决策。

### 循环调度

| Claude Code | Codex | Hermes / 通用 |
|-------------|-------|--------------|
| `CronCreate` / `ScheduleWakeup` | cron / hook | `while`+sleep / cron |
