# VERIFY 阶段手册

Orchestrator 亲自对照原始需求和 checklist 验收任务是否完成时加载。

## 验收输入

主 agent 必须读取或核对：

- 原始需求（完整）
- Loop Contract（意图、完成判定、停止护栏、预算剩余）
- 本轮 Skill/Reference 与各 skill hard gate
- 验收 Checklist
- Worker 产出（阅读 state/ 目录下的文件）
- Feedbacker 报告（若有，阅读修正 prompt / delta plan）
- 验证命令输出或证据文件

## 验收输出格式

```markdown
## Verification（第 N 轮）
- [x] 标准 1 — PASS（证据：state/step1_output.json 含 3 组分歧，word count 输出 687 字）
- [ ] 标准 2 — FAIL（偏差：state/step2_output.json 缺少第 3 组对比的实践后果段落）
- [x] 标准 3 — PASS（证据：pytest -v 输出 12 passed, 0 failed）
### 证据充分性
- state/step1_output.json 可独立核验；state/step2_evidence.txt 缺失
### Skill 遵循情况
- 已核验 Worker 按 Loop Contract 加载指定 skill/reference；未提供 hard gate 证据的步骤不得 PASS
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

- **默认严格** — 主 agent 验收时要找差距，不急着放行。宽松=浪费所有人的 token。
- 证据不充分 → FAIL：Worker 说"测试通过"但未附 pytest 输出 → 不是 PASS
- skill/hard gate 证据不充分 → FAIL：PLAN 指定 TDD 但没有 RED/GREEN 输出，或指定 brainstorming 但没有用户确认 → 不是 PASS
- 只看 Feedbacker 摘要 → FAIL：主 agent 必须打开 `state/` 中的产出和证据
- 发现质量问题但 checklist 没覆盖 → 更新 checklist，再交给 Feedbacker 写修正 prompt
- 主 agent 只做验收和调度，不亲自修正文档/代码/产物；失败后的修正 prompt 交给 Feedbacker，修正执行交给 Worker

## Orchestrator 决策

1. 检查判定：PASS / REVISE / STAGNATE / BUDGET_STOP
2. 如果是 PASS → 进入 DELIVER
3. 如果是 REVISE → 收集失败项的问题描述 → 进入 FEEDBACK（加载 revise.md）
4. 如果是 STAGNATE → 进入 DELIVER，标注未达标项
5. 如果是 BUDGET_STOP → 进入 DELIVER，标注预算耗尽和未达标项
6. 如果验收记录不完整 → 补齐证据后重新判定
