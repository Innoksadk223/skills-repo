# 终止条件、代价与陷阱

Orchestrator 做「继续/终止」决策或排查异常时加载。

## 终止条件

| 条件 | 触发动作 | 说明 |
|------|---------|------|
| Evaluator 判定 PASS | **DELIVER** | 全部达标，交付最终产出 |
| 累计 3 轮 | **DELIVER + 标注未达标项** | 硬上限，防止无限循环。交付时标注哪些 checklist 项未达标 |
| STAGNATE（连续 2 轮提升 <10%） | **DELIVER** | 继续修正已无边际收益，交付当前最佳版本 |
| BUDGET_STOP | **DELIVER + 标注预算耗尽** | 达到 PLAN 声明的 token、时间或费用上限 |

**不做「再试最后一次」的判断。** 3 轮硬上限、停滞检测和预算上限是安全网——到了就终止。

## Token 代价（每轮参考）

| 调用 | 次数 | 说明 |
|------|:---:|------|
| Orchestrator PLAN | 1 | 首轮完整，后续 delta |
| Worker ACT | 1-N | 每批 ≤3 个 Worker agent |
| Evaluator CHECK | 1 | toolsets=["file"]，独立读取 state/ |
| Troubleshooter | 0-1 | 仅 REVISE 时分派 |

首轮 PASS：约 `N + 2` 次 LLM 调用（N = Worker agent 总数；每批 ≤3 并行）。每加一轮修正：失败 Worker 数 + Evaluator + 可选 Troubleshooter。

## 预算护栏

PLAN 未声明预算时，默认护栏：

| 类型 | 默认值 |
|------|--------|
| 轮数 | 3 轮 |
| 并行 Worker | 每批 ≤3 |
| 时间 | 45 分钟 |
| token/费用 | 无法计量时，在 DELIVER 中声明未计量 |

预算只能在用户明确要求时放宽。Orchestrator 不得因为"快好了"自行加轮。

## 常见陷阱及对策

### 1. Orchestrator 越权

**问题**：Orchestrator 亲自执行步骤或替 Evaluator 打分 → 自评偏差。
**对策**：所有执行交给 Worker agent，所有验收交给 Evaluator agent；`delegate_task` / `spawn_agent` 只是分派入口。Orchestrator 只做 PLAN + DELIVER + 资源调配。

### 2. PLAN 步骤描述太粗

**问题**：写"生成测试"而非"为 src/auth.py 写 pytest，覆盖 3 条路径，断言 200/401/403"。Worker 没有深度规格。
**对策**：见 references/plan.md → 步骤设计规则表。

### 3. Evaluator 放水

**问题**：连续全部 PASS 但质量差 → Evaluator prompt 严格度不足。
**对策**：Evaluator prompt 中"宽松=浪费所有人的 token"不可删。怀疑放水时，在下一轮 Evaluator goal 中加"上一轮可能过于宽松，本轮必须对证据充分性零容忍"。

### 4. Worker 不给证据

**问题**：Worker 声称完成但无文件路径、无命令输出 → Evaluator 无法核验。
**对策**：ACT 阶段 mini-check 必须看到 `handoff check: [文件路径]` 行才放行。无此行的 Worker 返回视为失败。

### 5. 忘掉终止条件

**问题**：反复修正第 4、5 轮，"最后一次"变成"再来一次"。
**对策**：3 轮硬上限是代码逻辑，不是建议。Orchestrator 在每轮 CHECK 后加载本文件核对。

### 6. 把 Loop 当 Prompt 放大器

**问题**：每轮临时写更长 Prompt，不沉淀 Skill，不加强验证。
**对策**：失败后优先问三件事：是否该调用已有 skill、是否该把重复步骤固化成 skill、是否该加强证据门槛。
