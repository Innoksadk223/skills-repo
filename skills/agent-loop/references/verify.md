# VERIFY 阶段手册

Orchestrator 亲自对照原始需求和 checklist 验收 worktree 中的最终交付物时加载。

**验收对象是 worktree 里的产出物，不是计划。** PLAN 写得好不好不重要——`state/` 里的文件是否达标才是唯一标准。

## 验收输入

主 agent 必须读取或核对：

- 原始需求（完整）
- Loop Contract（意图、完成判定、停止护栏、预算剩余）
- 验收 Checklist
- Worker 产出（阅读 state/ 目录下的文件，不是看 Worker 的总结摘要）
- Feedbacker 报告（阅读 state/feedback_round_N.json，含判定和修正历史）
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
| PASS | 全部 checklist 项通过，交付物在 worktree 中可独立核验 |
| REVISE | 至少一项 FAIL，且问题有明确修正方向 |
| STAGNATE | 连续 2 轮提升 <10%，问题反复出现未解决 |
| BUDGET_STOP | 已达到 Loop Contract 中的 token/时间/费用上限 |

## 严格度校准

- **验收的是交付物，不是计划**：PLAN 可能不完美，但只要 worktree 里的产出物全部达标，就是 PASS
- **PASS 不等于交付**：如果 checklist 全部通过但交付物本身指出了可操作的改进项（如审计报告列出了应修复问题），Orchestrator 必须自动进入 FEEDBACK → ACT-FIX，不得问用户"要不要继续"，不得直接 DELIVER。只有产出物就是用户要的最终成果时才交付
- **证据零容忍**：Worker 声称通过但未附输出/路径 → FAIL。skill 指定了 TDD 但没有 RED/GREEN 输出 → FAIL。主 agent 必须打开 worktree 文件，不能只看 Worker 摘要

## Orchestrator 决策

1. 检查判定：PASS / REVISE / STAGNATE / BUDGET_STOP
2. 如果是 PASS：
   - 交付物是用户要的**最终成果** → 进入 DELIVER，交付 worktree 中的产出物
   - 交付物是**中间产物**且自身指出可操作改进项（如审计报告、诊断报告）→ 自动进入 FEEDBACK → ACT-FIX，不询问用户
3. 如果是 REVISE → 收集失败项的问题描述 → 进入 FEEDBACK（加载 feedback.md）
4. 如果是 STAGNATE → 进入 DELIVER，标注未达标项
5. 如果是 BUDGET_STOP → 进入 DELIVER，标注预算耗尽和未达标项
6. 如果验收记录不完整 → 补齐证据后重新判定
