# 终止条件、代价与陷阱

Orchestrator 做「继续/终止」决策或排查异常时加载。

## 终止条件

| 条件 | 触发动作 | 说明 |
|------|---------|------|
| Orchestrator 验收 PASS | **DELIVER** | 全部达标，交付 worktree（state/）中的最终产出物 |
| 累计 3 轮 FEEDBACK→ACT-FIX | **DELIVER + 标注未达标项** | 硬上限，防止无限循环。交付时标注哪些 checklist 项未达标 |
| STAGNATE（连续 2 轮提升 <10%） | **DELIVER** | 继续修正已无边际收益，交付当前 worktree 中的最佳版本 |
| BUDGET_STOP | **DELIVER + 标注预算耗尽** | 达到 PLAN 声明的 token、时间或费用上限 |

**不做「再试最后一次」的判断。** 3 轮硬上限、停滞检测和预算上限是安全网——到了就终止。

## Token 代价（每轮参考）

| 调用 | 次数 | 说明 |
|------|:---:|------|
| Orchestrator PLAN | 1 | 首轮完整，后续 delta |
| Worker ACT | 1-N | 并行度由依赖、预算和宿主能力决定 |
| Feedbacker FEEDBACK | 1 | 读取 worktree，写修正 prompt |
| Orchestrator VERIFY | 1 | 主 agent 读取 worktree 并验收 |

首轮 PASS：约 `N + 2` 次 LLM 调用（N = Worker 总数）。每加一轮修正：Feedbacker + 受影响 Worker + Orchestrator VERIFY。

## 预算护栏

PLAN 未声明预算时，默认护栏：

| 类型 | 默认值 |
|------|--------|
| 轮数 | 3 轮 |
| 并行 Worker | 按依赖、预算和宿主能力决定 |
| 时间 | 45 分钟 |
| token/费用 | 无法计量时，在 DELIVER 中声明未计量 |

预算只能在用户明确要求时放宽。Orchestrator 不得因为"快好了"自行加轮。

## 常见陷阱及对策

### 1. Orchestrator 越权

**问题**：Orchestrator 亲自执行步骤或替 Feedbacker 写修正 prompt → 主控和执行混在一起。
**对策**：执行交给 Worker，修正 prompt 交给 Feedbacker。Orchestrator 负责 PLAN + VERIFY + DELIVER + 资源调配。收到 Feedbacker 的 worker_fix_prompt 后原样转发，不修改。

### 2. PLAN 步骤描述太粗

**问题**：写"生成测试"而非"为 src/auth.py 写 pytest，覆盖 3 条路径，断言 200/401/403"。Worker 没有深度规格。
**对策**：见 references/plan.md → 步骤设计规则表。

### 3. 主 agent 验收放水

**问题**：连续全部 PASS 但质量差 → 主 agent 验收标准或证据门槛不足。
**对策**：在 VERIFY 阶段对证据充分性零容忍；发现 checklist 缺口时先更新 checklist，再交给 Feedbacker 写修正 prompt。验收对象是 worktree 中的交付物，不是 Worker 的自我总结。

### 4. Worker 不给证据

**问题**：Worker 声称完成但无文件路径、无命令输出 → Feedbacker / 主 agent 无法核验。
**对策**：ACT 阶段 mini-check 必须看到 `handoff check: [文件路径]` 行才放行。无此行的 Worker 返回视为失败。

### 5. 忘掉终止条件

**问题**：反复修正第 4、5 轮，"最后一次"变成"再来一次"。
**对策**：3 轮硬上限是代码逻辑，不是建议。Orchestrator 在每轮 VERIFY 后加载本文件核对。

### 6. 把 Loop 当 Prompt 放大器

**问题**：每轮临时写更长 Prompt，不沉淀 Skill，不加强验证。
**对策**：失败后优先问三件事：是否该调用已有 skill、是否该把重复步骤固化成 skill、是否该加强证据门槛。

### 7. 被其它 Skill 短路

**问题**：任务同时触发 TDD、brainstorming、writing-plans 等 skill，于是跳过 agent-loop，或只说"参考 loop 思想"。
**对策**：只要任务满足 agent-loop 触发条件，Loop 就是外层调度器。调用本 skill 即视为明确进入 Loop，并授权使用宿主可用的 subagent / worker 分派能力。其他 skill 的 hard gate 进入 handoff/checklist；若不能分派，必须声明限制并本地模拟角色。

### 8. 验收标准模糊导致跳过 Loop

**问题**：目标有具体产物，但 checklist 尚未明确，于是把任务当开放探索处理。
**对策**：先进入 PLAN，用 brainstorming 或领域 skill 补齐可量化 checklist；只有没有具体产物的开放探索才不触发 Loop。

### 9. 把 Prompt 放在 Skill 前面

**问题**：已有匹配 skill，却写一次性长 prompt 让 Worker 临场发挥。
**对策**：PLAN 先列 skill/reference，再写步骤。没有匹配 skill 时才允许一次性 prompt，并在 Loop Contract 标注原因。

### 10. 修正 prompt 被 Orchestrator 转述

**问题**：Feedbacker 写了精确的修正指令，Orchestrator 觉得"我可以说得更好"于是改写——引入新偏差。
**对策**：Orchestrator 只做信使。Feedbacker 的 worker_fix_prompt 原样转发给 Worker。

### 11. Worker 只会说不会改

**问题**：Worker 收到修正 prompt 后，分析了一番为什么需要改，但没有实际修改 worktree 中的文件。
**对策**：Worker goal 中明确要求"更新 state/ 中的文件"而非"分析问题"。handoff check 必须有文件存在 + 内容变更证据。
