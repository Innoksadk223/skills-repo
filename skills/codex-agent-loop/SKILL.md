---
name: codex-agent-loop
description: "Use when a Codex task needs independent maker-checker review, evidence-backed verification, issue-specific fix prompts, repeated correction, resumable review state, bounded optimization, or an explicit /agent-loop request. Keep the primary Codex responsible for planning, changes, and delivery while one native audit subagent is reused across AUDIT, VERIFY, OPTIMIZE, and FINAL_VERIFY."
---

# Codex Agent Loop

把执行与裁判分开。主 Codex 负责 PLAN、ACT、修正和交付；独立审查 agent 负责判定、复验、为每个 issue 编写可直接执行的 `fix_prompt`，并控制优化分流。

把本技能当作当前 Codex 根任务内的原生 multi-agent 工作流，不要把 child agent 当作独立 CLI session。

## 加载与状态

先复用已有 Plan mode、`writing-plans` 或其它可用计划。没有可执行计划时，先写最小合约。

1. 修改交付物前，把 `references/contract-template.md` 复制到 `state/<slug>/state.md`。
2. 向用户展示目标、非目标、假设、停止护栏和 checklist；必须取得显式确认。
3. 首次 AUDIT 前完整读取 `references/protocol.md`，后续阶段按其中格式续跑。

| 文件 | 所有者 | 用途 |
| --- | --- | --- |
| `state/<slug>/state.md` | 主 Codex | 合约、进度、证据、agent handle、恢复、基线、交付摘要 |
| `state/<slug>/review.md` | 审查 agent | AUDIT、appeal 裁决、VERIFY、OPTIMIZE、FINAL_VERIFY |
| `state/<slug>/appeal.md` | 主 Codex | 可选的证据化申诉 |
| `state/inbox.md` | 主 Codex | 可选的跨任务未决项 |

过程文件只负责路由，不能替代真实 diff、命令输出、日志或产物。

## 工作流

```text
PLAN → USER_GATE → ACT → OBSERVE → AUDIT
                                      │
                    CONTINUE_FIX ─────┤
                    ESCALATE_REPLAN ──┤
                    PROCEED_TO_VERIFY ▼
                                   VERIFY
                                      ▼
                               BASELINE_LOCK
                                      ▼
                  OPTIMIZE → AUDIT(re-verify)
                                      ▼
                              FINAL_VERIFY → DELIVER
```

每个环节完成后在 `state.md` 的 `loop_todo` 对应项打勾；`loop_todo` 是 `stage` 的可视化防漏，冲突时以 `stage` 为准。

1. **PLAN / USER_GATE**：锁定可检查的 goal、non-goals、assumptions、checklist、handoff、预算和停止条件。未获用户明确确认，不得进入 ACT。
2. **ACT / OBSERVE**：只做已确认范围；主 Codex 亲自读取并记录 diff、文件、日志和验证命令原始输出，不采信执行者口头总结。
3. **AUDIT**：首次审查只生成一个独立 agent，使用 `fork_turns="none"`，让它从状态文件读取上下文并写 `review.md`。
4. **LOOP**：reviewer 为每个 issue 生成独立 `fix_prompt`；主 Codex 按 execution order 原样执行或提交 appeal，不得代写、弱化或合并约束。
5. **VERIFY**：复用同一审查 agent，独立重跑每个 checklist 的验证命令。
6. **BASELINE_LOCK**：VERIFY 通过后，由主 Codex 记录文件、hash、回滚入口和证据；不得修改交付物。
7. **OPTIMIZE**：复用同一审查 agent 先写 `optimize_todo`（四维度 + 已知候选逐条登记），再执行四维预扫描并逐项关闭 todo，为 `OPTIMIZE_NOW` 生成 `optimize_prompt`。只自动执行低风险、无新依赖、无需确认且预期收益不少于 5% 的候选；`enrichment` 一律先问用户。
8. **FINAL_VERIFY / DELIVER**：让同一审查 agent 确认基线完整和停止理由；主 Codex 再汇总交付。

## 原生 Agent 生命周期

优先调用当前 Codex host 暴露的同义原生工具；工具名可能带 `collaboration.` namespace。

| 动作 | 工具 | 规则 |
| --- | --- | --- |
| 首次创建 reviewer | `spawn_agent` | 只调用一次；canonical task name 必记，agent ID 仅在 host 实际返回时选记 |
| 无进行中 turn 后进入下一阶段 | `followup_task` | 对 idle / completed 的同一 agent 触发新 turn |
| agent 正在运行时补充或纠偏 | `send_message` | 只投递消息，不把它当成新 turn |
| 等待 agent 更新 | `wait_agent` | 使用有界等待；返回的是通知，不是审查证据 |
| 查询与恢复 | `list_agents` | 用已记录 handle 判断 agent 是否仍可达 |
| 停止当前 agent turn | `interrupt_agent` | 中断后仍可用 `followup_task` 复用该 agent |

- 直接调用 agent 工具；不要把它们包进 shell、`functions.exec` 或其它工具调用。
- 默认把 `spawn_agent` 返回的 canonical task name 作为 target；仅在 host 确实返回且后续工具接受时使用 agent ID，绝不猜测。
- 不要为每个阶段新建 reviewer，也不要用 `create_thread`、`fork_thread`、`codex exec resume`、`--last` 或扫描 `~/.codex/sessions/` 控制 child agent。
- `wait_agent` 返回后，亲自读取 `review.md` 和实际证据；agent 的 final summary 本身不是 PASS。
- agent 共享当前工作区；禁止主 Codex 与 reviewer 并发写同一文件，禁止 reviewer 修改交付物。

## 审查硬规则

- 保持 maker-checker split：产出交付物的 agent 不得给自己判定 PASS。
- 让 reviewer 只写 `review.md`；若实际 sandbox 为只读，允许主 Codex 原样转存 reviewer 返回的完整审查块，但必须记录 `primary_verbatim`、内容 hash，且不得编辑结论。
- 不要声称 custom agent 的 `sandbox_mode` 一定覆盖父任务实时权限；subagent 继承父任务工具和 live runtime overrides，先以实际权限为准。
- 运行六个 gate：`contract`、`completeness`、`correctness`、`reuse_existing`、`budget`、`evidence_regression`。
- 第二轮及以后先关闭旧 issue，再重跑全部六个 gate。
- 每个阻塞 issue 必须有唯一 ID、证据、`fix_instruction` 和独立 `fix_prompt`；prompt 必含目标、证据、必改、禁改、验证和完成回报。
- `CLARIFIED` 必须由 reviewer 输出完整 replacement prompt；主 Codex 不得自行澄清。
- 把范围外建议放进 notes 或 `state/inbox.md`，不得伪装成阻塞项。
- 需要测试、lint、typecheck 或 build 时，在 ACT 记录输出，并在 VERIFY 由 reviewer 独立重跑。
- 本技能允许主 Codex 根据任务需要派出辅助 agent；只委派独立、有限、可验证的一次性任务，不让它参与 AUDIT / VERIFY、替代 reviewer 或与其它 agent 并发修改重叠文件。
- 口头 PASS 视为 FAIL；每个判定必须指向文件、diff、命令输出、日志或产物。

## 恢复

先读 `state.md`、`review.md`、`appeal.md` 和 `state/inbox.md` 中实际存在的文件，再按 `references/protocol.md` 路由。

- 当前根任务内：只用 `audit_task` 的 canonical prefix 调用 `list_agents`；可达就复用。
- agent 正在运行：等待或用 `send_message` 纠偏；agent 无进行中 turn（如 idle / completed）：用 `followup_task` 进入下一阶段。
- handle 不可达：记录 `UNREACHABLE` 和原因，递增 `audit_generation`，生成 replacement reviewer；让它从过程文件恢复并先关闭旧 issue。
- 不要删除旧审查记录，不要通过扫描本地 session 目录猜测恢复目标。
- `user-confirm` 非空、合约需变更、外部动作需授权或连续两次 `ESCALATE_REPLAN` 无进展时，停止并询问用户。

## 交付

只有 `FINAL_VERIFY: VERIFIED` 才能交付。总结改了什么、为什么、验证证据、风险和下一步。保留 agent handle 与过程文件，除非用户明确授权清理。

精确调用模板、判定格式、appeal、优化和恢复分支见 `references/protocol.md`。
