---
name: agent-loop
description: Use when undertaking any multi-step task with verifiable outcomes — code generation/fix, research, writing, or complex workflows with 3 or more distinct steps.
---

# Agent Loop

四角色分离的迭代循环：Orchestrator 规划、Worker 执行、Evaluator 打分、Troubleshooter 诊断修正。每轮 spawn 独立 agent，消除自评偏差。

## When to Use

- 任务 ≥3 个独立步骤
- 验收标准可量化（不是"好不好"而是"有没有"）
- 需要质量保证且不想 agent 对自己宽松
- 代码生成/修复、研究报告写作、多步数据处理

**不适用：** 单步任务、完全探索性对话、验收标准无法量化的开放任务。

## 四角色

| 角色 | 身份 | delegate? | 职责 |
|------|------|:---:|------|
| Orchestrator | 你（主 agent） | — | PLAN + DELIVER + 资源调配 |
| Worker(s) | `delegate_task` | ✅ | ACT：执行步骤，返回产出+证据 |
| Evaluator | `delegate_task` | ✅ | CHECK：对照 checklist 逐项打分 |
| Troubleshooter | `delegate_task` | ✅ | REVISE：诊断 FAIL + 写修正 prompt |

**核心规则：干活的不能给自己打分。每个 agent 在同一轮只担任一个角色。**

## 流程

```
PLAN（Orchestrator 输出计划块 + 每步 handoff 条件）
  ↓
ACT — Step 1（Worker 执行 → 自检产出物存在 → handoff）
  ↓ mini-check
ACT — Step 2（依赖 Step 1 时串行，无依赖时并行）
  ↓ mini-check
ACT — Step N
  ↓
CHECK（Orchestrator spawn Evaluator，逐项打分）
  ↓
ALL PASS? → DELIVER
  ↓ FAIL
Troubleshooter（诊断 + 输出修正 prompt）
  ↓
Orchestrator 拿到修正 → 回到 ACT（仅重跑失败步骤）
```

## PLAN 输出格式

```markdown
## Plan（第 N 轮）
### 步骤
1. [步骤] — [做什么 + 做到什么程度]
   - handoff 条件：[产出物路径 / 验证命令 / 必须存在的文件]
2. [步骤] — [做什么 + 做到什么程度]
   - handoff 条件：[...]
### 边界条件
- 不在范围：...
### 验收 Checklist
- [ ] 标准（可量化、二元、附证据要求）
### 执行策略
- Worker 数：[1 / ≤3 并行]
- Worker toolsets: [...]
```

规则：
- Checklist 每项 = 可量化、二元，附证据要求（"测试通过，提供 pytest 输出"而非"代码正确"）
- 每个步骤 → ≥1 个 checklist 项
- **handoff 条件 = 产出物必须存在且格式正确，下一步才能开始。** 形式：文件路径（`/path/to/output.json`）、验证命令（`grep "PASS" result.txt`）、或 Worker 自述（"已确认 X 存在"）。不等全跑完才检查——第 2 步错在第 3 步才发现的代价远大于 mini-check。
- **步骤描述必须编码做什么 + 做到什么程度。** ❌ "写共识与分歧" / ✅ "分析 ≥3 组分歧，每组含双方代表论文、核心论据、实践后果，每组 ≥200 字"。结构标签不是深度规格。
- 第 2 轮起计划只输出**变更部分**（delta）
- 执行策略：分析步骤依赖图。无依赖 → parallel batch；有依赖 → 单 worker 串行

## ACT — spawn Worker

```python
delegate_task(tasks=[
    {"goal": "步骤 N 的完整描述 + 输出格式", "toolsets": [最小集]},
    ...
], context="原始需求：[全文]。验收标准：[checklist]。只做分配的步骤，返回产出+证据。")
```

Worker 规则：leaf 角色、不给 delegate 权限、≤3 并行。

**Worker 必须做的事：**
1. 执行分配的步骤
2. 返回产出 + 证据
3. **自检 handoff 条件**：确认产出物存在且格式正确，在返回中明确写"handoff check: [产出物路径] 已验证存在"。不通过时不交棒——Worker 应自行修复或报告失败。

**Orchestrator 在每步后做的事：**
- 检查 Worker 是否报告了 handoff 条件通过
- 通过 → 启动下一步 Worker（或等待并行 batch 全部完成）
- 不通过 → 暂停，不跑后续步骤。将失败信息交给 Troubleshooter

## CHECK — spawn Evaluator

```python
delegate_task(
    goal="你是独立验收员。严格对照 checklist 逐项打分，找出差距而非放行。宽松=浪费所有人的 token。
输入：原始需求 + Checklist + Worker产出。输出：逐项 PASS/FAIL + 判定 + 失败项问题描述。",
    toolsets=[])
```

Evaluator 输出格式：

```markdown
## Evaluation（第 N 轮）
- [x] 标准 1 — PASS（证据有效）
- [ ] 标准 2 — FAIL（偏差：...）
### 结果：X/Y | 提升：+Z% | 判定：PASS/REVISE/STAGNATE
```

## REVISE — spawn Troubleshooter（仅 FAIL 时）

```python
delegate_task(
    goal="诊断失败根因 + 输出修正后的执行描述。输入：原始PLAN + Evaluator报告 + Worker产出。输出：根因 + 修正后的步骤描述。",
    toolsets=["file", "read"])
```

Orchestrator 拿到修正后回到 ACT，仅重跑失败步骤。

## 终止条件

| 条件 | 触发 |
|------|------|
| Evaluator 判定 PASS | 全部达标 → DELIVER |
| 累计 3 轮 | 不论结果 → DELIVER + 标注未达标项 |
| Evaluator 判定 STAGNATE | 连续 2 轮提升 <10% → DELIVER |

## Token 代价（每轮）

| 调用 | 次数 | 说明 |
|------|:---:|------|
| Orchestrator PLAN | 1 | 首轮完整，后续 delta |
| Worker ACT | 1-3 | 并行 batch |
| Evaluator CHECK | 1 | 无 tools，只读 |
| Troubleshooter | 0-1 | 仅 REVISE 时 |

首轮 PASS：3-5 次 LLM 调用。每加一轮修正：+3-4 次。

## 陷阱

- **Orchestrator 越权** — 亲自执行或打分 = 自评偏差。这是本 skill 要消除的核心问题。
- **PLAN 步骤太粗** — "写共识与分歧"不告诉 Worker 写到什么深度。步骤描述 = 做什么 + 做到什么程度 + 输出格式。
- **Evaluator 放水** — Evaluator prompt 必须强调"严格"。连续两轮全部 PASS 但交付质量差 → 调高 Evaluator 的严格度。
- **Worker 不给证据** — Worker prompt 必须要求输出针对每个 checklist 项的证据（文件路径、输出摘要）。无证据的 PASS 不可信。
- **忘掉终止条件** — 3 轮硬上限和停滞检测是安全网，不做"再试最后一次"的判断。
