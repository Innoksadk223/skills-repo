---
name: agent-loop
description: Use when undertaking any multi-step task with verifiable outcomes — code generation/fix, research, writing, or complex workflows (3+ steps). Encodes a Plan → Act → Check → Revise → Deliver loop with structured self-verification, max 3 rounds, and automatic stagnation detection.
---

# Agent Loop

四角色分离的迭代循环。主 agent（Orchestrator）不执行也不验收——消除自评偏差。Worker、Evaluator、Troubleshooter 均为独立 `delegate_task` spawn。

## 四个角色

| 角色 | 谁 | 做什么 | delegate? |
|------|-----|------|:---:|
| **Orchestrator** | 主 agent（你） | PLAN + 最终 DELIVER + 资源调配 | — |
| **Worker(s)** | `delegate_task` spawn | ACT：执行步骤，返回产出 | ✅ |
| **Evaluator** | `delegate_task` spawn | CHECK：对照 checklist 逐项打分 | ✅ |
| **Troubleshooter** | `delegate_task` spawn | REVISE：诊断 FAIL + 写修正 prompt | ✅ |

**核心原则**：干活的不打分，打分的不干活。同一个 agent 对同一批产出只能担任一个角色。

## 完整流程

```
Orchestrator: PLAN
      ↓
Orchestrator: spawn Worker(s) → ACT
      ↓
Orchestrator: spawn Evaluator → CHECK
      ↓
   ALL PASS? ────→ Orchestrator: DELIVER
      ↓ NO
Orchestrator: spawn Troubleshooter → 诊断 + 修正 prompt
      ↓
Orchestrator: 拿到修正 prompt → 回到 ACT（仅重跑失败步骤）
      ↓
      重复 CHECK → ... → 触发终止 → DELIVER
```

---

## Phase 1: PLAN（Orchestrator）

**必须输出以下计划块，再开始任何执行动作：**

```markdown
## Plan（第 N 轮）
### 步骤
1. [步骤名称] — [做什么]
### 边界条件
- 不在范围内：...
- 前置假设：...
### 验收 Checklist
- [ ] 标准（可量化、二元判断，附证据要求）
### 执行策略
- 模式：[单 worker 串行 / 多 worker 并行（≤3）]
- 每 worker toolsets：[...]
```

规则：
- Checklist 每项 = 可量化、二元，附证据要求（"测试通过，提供 pytest 输出"而非"代码正确"）
- 每个步骤 → ≥1 个 checklist 项
- 第 2 轮起计划只输出**变更部分**（delta）
- 执行策略：分析步骤依赖图。无依赖 → parallel batch；有依赖 → 单 worker 串行

---

## Phase 2: ACT（Worker agent）

Orchestrator **不亲自执行**。通过 `delegate_task` spawn Worker：

**单 worker 串行：**
```python
delegate_task(
    goal="[完整步骤描述 + 输出格式要求]",
    toolsets=["web", "terminal", "file", ...],
    context="原始需求：[用户原始需求全文]。验收标准：[checklist]。只做分配给你的步骤。"
)
```

**多 worker 并行（batch）：**
```python
delegate_task(tasks=[
    {"goal": "步骤 1 的完整任务描述", "toolsets": [...]},
    {"goal": "步骤 2 的完整任务描述", "toolsets": [...]},
], context="原始需求：[全文]。验收标准：[checklist]。你只负责分配的步骤，完成后返回产出 + 证据。")
```

规则：
- 最多 3 个并行 worker
- Worker 角色 = `leaf`，toolsets 不含 `delegate_task`
- Worker 返回：**产出 + 针对每个 checklist 项的证据**（文件路径/输出摘要）
- Worker 失败时 Orchestrator 不要自行修正——交给 Troubleshooter

---

## Phase 3: CHECK（Evaluator agent）

Orchestrator **不亲自打分**。spawn 独立 Evaluator：

```python
delegate_task(
    goal="""你是独立验收员。严格对照 checklist 逐项打分。Worker 会尽量让产出看起来合格——你的职责是找出差距。

输入：
- 原始需求：[用户原始需求]
- 验收 Checklist：[checklist 全文]
- Worker 产出 + 证据：[worker 返回的完整内容]

要求：
1. 逐项判定 PASS/FAIL，附具体偏差说明
2. 计算通过率、较上轮提升%
3. 输出判定：PASS（全部达标）/ REVISE（需修正）/ STAGNATE（连续 2 轮提升 < 10%）
4. 如果 FAIL，为每个失败项提供具体的问题描述，供 Troubleshooter 使用""",
    toolsets=[],
    context="你是独立验收员。你的评分直接影响任务走向。宽松=浪费所有人的 token。"
)
```

输出格式（Evaluator 必须遵守）：

```markdown
## Evaluation（第 N 轮）
- [x] 标准 1 — PASS（证据有效：[...]）
- [ ] 标准 2 — FAIL（偏差：[具体差距]。Worker 声称...但实际...）

### 结果
- 通过：X/Y
- 较上轮提升：+Z%（首轮 N/A）
- 判定：PASS / REVISE / STAGNATE
- 失败项问题描述：[供 Troubleshooter 使用的具体诊断]
```

---

## Phase 4: REVISE（Troubleshooter agent）

当 Evaluator 判定为 REVISE 时，Orchestrator spawn Troubleshooter：

```python
delegate_task(
    goal="""你是问题诊断和修正专家。基于以下信息，诊断失败根因并输出修正后的执行 prompt。

输入：
- 原始计划：[Orchestrator 的 PLAN]
- 失败项：[Evaluator 报告中所有 FAIL 项及其问题描述]
- Worker 原始产出：[worker 输出]

输出：
1. 根因诊断（每个失败项一行：哪里出了问题，为什么）
2. 修正后的执行描述（仅针对失败步骤，精炼、具体、可操作）
3. 如有必要，更新 checklist 项（原来标准不合理时）""",
    toolsets=["file", "read"],
    context="你是 Troubleshooter。只做诊断和修正，不执行任务。"
)
```

Orchestrator 拿到 Troubleshooter 输出后 → 回到 Phase 2，仅重跑失败步骤。

---

## 终止条件（任一触发即停止）

| 条件 | 说明 |
|------|------|
| Evaluator 判定 PASS | 全部 checklist 达标 → DELIVER |
| 累计 3 轮 | 第 3 轮 Evaluator 结果不论 → DELIVER |
| Evaluator 判定 STAGNATE | 连续 2 轮提升 < 10% → DELIVER |

## DELIVER（Orchestrator）

- 最终输出
- 最后一轮 Evaluation 报告
- 未达标项清单（如有）
- 如果非 PASS 交付：标注"以下标准未达标：..."

---

## Token 经济学（每轮）

| 调用 | 何时 | 说明 |
|------|------|------|
| Orchestrator PLAN | 每轮 1 次 | 首轮完整，后续 delta |
| Worker ACT | 每轮 1-3 次 | 并行 ≤3 worker |
| Evaluator CHECK | 每轮 1 次 | 仅读 checklist + 产出，不给 tools |
| Troubleshooter | 仅 REVISE 时 1 次 | 不达标才调 |

首轮 PASS 总调数：1(PLAN) + 1~3(ACT) + 1(CHECK) = 3~5 次 LLM 调用。
每加一轮修正：+1(Troubleshooter) + 1~3(ACT) + 1(CHECK) = 3~5 次。

## 适用 / 不适用

**适用：** 代码生成/修复、研究/写作、复杂多步骤任务（≥3 步）
**不适用：** 单步任务、需实时人工介入、验收标准无法量化

## 陷阱

- **Orchestrator 越权** — 不要亲自执行或打分。自评偏差是本 skill 要解决的核心问题。
- **Evaluator 温和化** — 如果 Evaluator 连续 PASS，检查是否 prompt 不够严格。在 context 里强调"宽松 = 浪费所有人的 token"。
- **Worker 不给证据** — Worker prompt 必须要求提供针对 checklist 的证据。无证据的 PASS 不可信。
- **忘记轮数上限** — LLM 天然倾向"再试一次"，3 轮硬上限写在 skill 里不要破。

## 参考

- `references/design-decisions.md` — grill-me 决策推导
