# CHECK 阶段手册

Orchestrator 分派 Evaluator subagent 和解读评估结果时加载。

## Evaluator agent 分派格式

`delegate_task` / `spawn_agent` 是分派入口；被分派对象的身份是独立 Evaluator agent。

```python
delegate_task(
    goal="你是独立验收员。严格对照 checklist 逐项打分，找出差距而非放行。宽松=浪费所有人的 token。

输入：
- 原始需求（完整）
- Loop Contract（意图、完成判定、停止护栏、预算剩余）
- 验收 Checklist
- Worker 产出（阅读 state/ 目录下的文件）

输出：逐项 PASS/FAIL + 判定 + 失败项问题描述 + 证据充分性。",
    toolsets=["file"]  # Evaluator 必须能独立读取 state/ 中的 Worker 产出
)
```

**toolsets 至少包含 `"file"`** — Evaluator 必须独立读取 Worker 产出文件核验证据，而非仅依赖 Orchestrator 的 context 注入。这是角色隔离成立的前提。

## Evaluator 输出格式

```markdown
## Evaluation（第 N 轮）
- [x] 标准 1 — PASS（证据：state/step1_output.json 含 3 组分歧，word count 输出 687 字）
- [ ] 标准 2 — FAIL（偏差：state/step2_output.json 缺少第 3 组对比的实践后果段落）
- [x] 标准 3 — PASS（证据：pytest -v 输出 12 passed, 0 failed）
### 证据充分性
- state/step1_output.json 可独立核验；state/step2_evidence.txt 缺失
### 结果：2/3 | 提升：+20% | 判定：REVISE
```

### 判定规则

| 判定 | 条件 |
|------|------|
| PASS | 全部 checklist 项通过 |
| REVISE | 至少一项 FAIL，且问题有明确修正方向 |
| STAGNATE | 连续 2 轮提升 <10%，问题反复出现未解决 |
| BUDGET_STOP | 已达到 Loop Contract 中的 token/时间/费用上限 |

## 严格度校准

- **默认严格** — Evaluator prompt 中的"宽松=浪费所有人的 token"是设计意图，不可删除
- 证据不充分 → FAIL：Worker 说"测试通过"但未附 pytest 输出 → 不是 PASS
- 只看 Orchestrator 摘要 → FAIL：Evaluator 必须打开 `state/` 中的产出和证据
- 连续两轮全部 PASS 但交付质量差 → Evaluator 严格度不够，下一轮加强 prompt 中的严格措辞
- Orchestrator 不应干预 Evaluator 的打分——如果对判定有异议，在 DELIVER 时标注分歧而非私下修改

## Orchestrator 解读 Evaluator 返回

1. 检查判定：PASS / REVISE / STAGNATE / BUDGET_STOP
2. 如果是 PASS → 进入 DELIVER
3. 如果是 REVISE → 收集失败项的问题描述 → 进入 REVISE（加载 revise.md）
4. 如果是 STAGNATE → 进入 DELIVER，标注未达标项
5. 如果是 BUDGET_STOP → 进入 DELIVER，标注预算耗尽和未达标项
6. 如果 Evaluator 返回格式不符合上述模板 → 要求重新输出（但不给暗示性引导）
