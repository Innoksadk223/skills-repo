# 终止条件、代价与陷阱

Orchestrator 做「继续/终止」决策或排查异常时加载。

## 终止条件

| 条件 | 触发动作 | 说明 |
|------|---------|------|
| Orchestrator 验收 PASS | **DELIVER** | 全部达标，交付 worktree（state/）中的最终产出物 |
| 累计 3 次修正轮 | **DELIVER + 标注未达标项** | 硬上限，防止无限循环。交付时标注哪些 checklist 项未达标 |
| STAGNATE（连续 2 次修正轮提升 <10%） | **DELIVER** | 继续修正已无边际收益，交付当前 worktree 中的最佳版本 |
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

## 常见陷阱速查

### 1. Orchestrator 越权（最频发）

Orchestrator 亲自执行步骤或替 Feedbacker 写修正 prompt。**对策**：执行交给 Worker，修正 prompt 交给 Feedbacker，Orchestrator 只做 PLAN + VERIFY + DELIVER。Feedbacker 的 worker_fix_prompt 原样转发。

### 其余陷阱速查

| # | 陷阱 | 对策 → |
|---|------|--------|
| 2 | PLAN 步骤太粗（"生成测试"而非具体规格） | → `plan.md` 步骤设计规则表 |
| 3 | 验收放水（证据不充分也给 PASS） | → `verify.md` 严格度校准 |
| 4 | Worker 不给证据（声称完成无文件路径） | → `act.md` mini-check 要求 `handoff check:` |
| 5 | 忘掉终止条件（反复修正超限） | → 本文件终止条件表（硬上限是代码逻辑） |
| 6 | Loop 当 Prompt 放大器（不沉淀 Skill） | → 失败后先问：是否该调用已有 skill？ |
| 7 | 被其它 Skill 短路 | → `plan.md` 禁止降级列表 |
| 8 | 验收标准模糊时自行猜测 | → `plan.md` 铁律：先问用户 |
| 9 | Prompt 放 Skill 前面 | → 同 #6，PLAN 先列 skill 再写步骤 |
| 10 | 修正 prompt 被转述 | → `feedback.md` 原样转发规则 |
| 11 | Worker 只会说不会改 | → `act.md` handoff + worktree 输出规则 |
