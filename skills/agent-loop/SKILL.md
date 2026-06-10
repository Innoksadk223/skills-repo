---
name: agent-loop
description: Use when undertaking any multi-step task with verifiable outcomes — code generation/fix, research, writing, or complex workflows (3+ steps). Encodes a Plan → Act → Check → Revise → Deliver loop with structured self-verification, max 3 rounds, and automatic stagnation detection.
---

# Agent Loop

Hermes 内的结构化单 agent 迭代循环。核心原则来自经典 ReAct loop 的原始定义——**一个 LLM 在一个上下文窗口内持续循环**——而非多 agent 编排。

## 设计原则

1. **单 agent 优先** — `delegate_task` 只在上下文隔离必要时用（需要读大量资料、worker 结果会淹没主 agent 全局判断）。否则所有执行在主 session 内完成。
2. **流程纪律由 Skill 定义** — 不等 LLM 自己"记得"要自检、要遵守轮数上限。Skill 注入结构。
3. **Token 效率 = 上下文纯度** — 每多一个子 agent 就多一次完整 LLM 调用。省 token 的第一原则是减少 agent 数量。

## 四阶段循环

```
PLAN → ACT → CHECK → (不达标?) → 诊断 → 修正 prompt → ACT → CHECK → ... → DELIVER
```

### 1. PLAN（计划阶段）

**必须输出以下格式的计划块，再开始任何执行动作：**

```markdown
## Plan（第 N 轮）
### 步骤
1. [步骤名称] — 做什么
### 边界条件
- 不在范围内：...
- 前置假设：...
### 验收 Checklist
- [ ] 标准 1（可量化、二元判断）
- [ ] 标准 2
```

规则：
- Checklist 每项 = 可量化、二元判断。❌ "代码整洁" / ✅ "所有测试通过 + lint 零告警"
- 每个步骤 → ≥1 个 checklist 项
- 简单任务（≤3 步）：计划 ≤ 5 行。复杂任务：允许详细，但计划不消耗循环轮次
- 第 2 轮起的计划只输出**变更部分**（delta），不复述全部

### 2. ACT（执行阶段）

- 能在一个 session 内完成的，不做子 agent
- 并行 vs 串行由 agent 根据步骤间依赖关系动态判断
- `delegate_task` 触发条件：单步骤需要读取/处理的信息量 ≥ 当前上下文窗口的 40%
- **每完成一个步骤，在原计划中标记 `[x]`**。步骤失败时立即诊断，不盲跑下一步

### 3. CHECK（验收阶段）

**不另起 agent 做裁判。不依赖 LLM 主观判断。**

执行步骤：
1. 对照 checklist 逐项自检
2. **必须输出以下格式的自检报告：**

```markdown
## Self-Check（第 N 轮）
- [x] 标准 1 — PASS（证据：[文件/输出/URL]）
- [ ] 标准 2 — FAIL（偏差：[具体差距]）

### 结果
- 通过：X/Y
- 较上轮提升：+Z%（首轮记 N/A）
- 判定：[继续修正 / 交付]
```

3. 证据必须具体（文件路径、测试输出、URL），不得写"已完成"这种无据判断
4. 第 2 轮起必须计算较上一轮的 checklist 通过率提升百分比

### 4. 循环控制

**终止条件（满足任一即停止）：**

| 条件 | 说明 |
|------|------|
| 达标 | checklist 全部 `[✓]` |
| 3 轮上限 | 第 3 轮执行后不论结果都交付 |
| 价值衰减 | 连续 2 轮 checklist 通过率提升 < 10%，提前终止 |

**不达标时的修正流程（由主 agent 在同一 session 内完成）：**
1. 诊断：定位未达标项的根因
2. 重写执行 prompt：基于诊断结果调整指令
3. 回到 ACT 阶段，仅重跑未达标部分（不重跑全部）

**交付格式（达到终止条件时）：**
- 最终输出
- 最后一轮的 checklist 自检报告
- 未达标项清单（如有）

## Token 经济学

| 优化点 | 规则 |
|--------|------|
| 上下文隔离 | `delegate_task` 仅用于单步信息量 ≥ 40% 上下文窗口 |
| 计划开销 | 计划最多占单轮总 token 的 30%，超了就切换粗规划模式 |
| 验收开销 | checklist 自检，不另起 LLM 做裁判 |
| 并行 | 无依赖步骤并行（`delegate_task` batch 模式或同 session 并发工具调用） |
| 重跑范围 | 只重跑未达标步骤，不全部重来 |

## 适用场景

- 代码生成/修复（可自动验证）
- 研究/写作（主观质量，靠 checklist 约束）
- 复杂多步骤任务（≥3 个环节，如运维部署、数据处理流水线）

## 不适用场景

- 简单单步任务（一个 LLM 调用 + 工具就能解决）
- 需要实时人工介入的任务
- 验收标准完全无法量化的开放探索

## 与 delegate_task 的分工

| | 单 agent loop（本 skill） | delegate_task |
|---|--------------------------|---------------|
| 何时用 | 默认 | 上下文隔离必需时 |
| Token 开销 | 低 | 每次 spawn 多一次完整 LLM 调用 |
| 上下文 | 共享，agent 保持全局视野 | 隔离，子 agent 看不到全局 |
| 验收 | 同一 session 内自检 | 子 agent 返回摘要，主 agent 审核摘要 |

**规则**：能用本 skill 的 loop 完成，就不要 spawn 子 agent。spawn 是逃生阀，不是默认路径。

## 陷阱

- **最大的坑是把 loop 做成多 agent 架构** — 每加一个 agent 就多一份 token 开销和上下文传递损耗。经典 ReAct 就是单 agent，多 agent 是后来叠上去的优化，不是基础。
- **checklist 写成主观描述** — "文章质量好"不可验收。"论点覆盖 3 个维度 + 每个维度有 ≥1 个引用来源"可验收。
- **重跑全部而非增量** — 第 2 轮只修未达标部分，不要从头执行。
- **忘记轮数上限** — LLM 天然倾向于"再试一次"，没有硬上限就是 token 黑洞。

## 参考

- `references/design-decisions.md` — 本 skill 的 grill-me 决策推导记录（8 个问题的逐层递进）
- `references/testing-record.md` — 2026-06-10 小型任务测试实录，含完整的 Plan/Check/Deliver 输出样例
