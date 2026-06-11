# REVISE 阶段手册

Orchestrator 在 Evaluator 判定 FAIL 后，分派 Troubleshooter subagent 并应用修正时加载。

## Troubleshooter agent 分派格式

`delegate_task` / `spawn_agent` 是分派入口；被分派对象的身份是独立 Troubleshooter agent。

```python
delegate_task(
    goal="你是独立诊断员。找出失败根因并输出修正方案。

输入：
- 原始 PLAN（第 N 轮）
- Evaluator 报告（含失败项问题描述）
- Worker 产出文件（阅读 state/ 目录）

输出以下结构化内容：
1. 根因分析 — 不是描述现象，是找出为什么 Worker 做不到
2. 修正后的步骤描述 — 可直接交给 Worker 执行
3. 修正后的 handoff 条件（如有变化）
4. 是否需要新增或替换 skill/reference",
    toolsets=["file"]
)
```

## Troubleshooter 输出 schema

```json
{
  "failed_checklist_items": ["标准 2", "标准 4"],
  "root_cause": "Worker 收到的步骤描述缺少输出格式约束，导致产出结构不完整",
  "failure_type": "prompt_gap | missing_skill | skipped_skill_gate | weak_validation | bad_state | budget_limit | external_blocker",
  "revised_steps": [
    {
      "original_step_id": 3,
      "revised_description": "分析 ≥3 组分歧...（完整步骤描述）",
      "revised_handoff": "state/step3_output.json 存在且含 'groups' 数组长度 ≥3",
      "required_skills_or_references": ["academic-search"],
      "change_rationale": "原描述缺少格式约束，补充了 JSON schema"
    }
  ],
  "new_steps": [],
  "deleted_steps": []
}
```

## Orchestrator 应用修正的合并规则

拿到 Troubleshooter 输出后：

1. **仅重跑失败步骤** — 已 PASS 的步骤不动，不重跑
2. **合并到 delta plan**：
   - 不变步骤 → 引用标记 "步骤 X 不变（第 N-1 轮已 PASS）"
   - 修正步骤 → 用 Troubleshooter 的 `revised_description` + `revised_handoff`
   - Skill 变更 → 加进 Loop Contract 的 `本轮 Skill/Reference`
   - 新增步骤 → 插入 `new_steps`，分配步骤编号
   - 删除步骤 → 标注 "原步骤 X 删除，原因：[rationale]"
3. **更新 checklist** — 如果 Troubleshooter 修改了步骤，对应 checklist 项也需更新
4. **保持已通过项目的 state/ 文件** — 不删除，下一轮 Evaluator 不用重验
5. **如果 Troubleshooter 诊断无法操作**（根因模糊、修正不具体）→ 在 delta plan 中标注不确定性，但仍尝试执行一轮（最多 3 轮硬上限兜底）
6. **如果根因是 weak_validation** → 优先加强 checklist 或证据要求，不只改 Worker 文案
7. **如果根因是 skipped_skill_gate** → 不扩大 prompt；把对应 skill 的 hard gate 写进步骤描述、handoff 和 checklist，并仅重跑受影响步骤

## 示例：合并后的 delta plan

```markdown
## Plan Delta（第 2 轮）
### 保持不变的步骤
- 步骤 1–2 不变（第 1 轮已 PASS，state/step1_output.json + state/step2_output.json）
### Loop Contract 变更
- 本轮 Skill/Reference 新增：academic-search
### 变更步骤
3. 分析 ≥3 组分歧，每组含双方代表论文、核心论据、实践后果，每组 ≥200 字。输出 JSON 格式含 "groups" 数组。
   - handoff 条件：state/step3_output.json 存在且 jq '.groups | length >= 3' 返回 true
   - 变更原因：第 1 轮缺少输出格式约束，Worker 产出缺少实践后果段落
### 更新后 Checklist
- [unchanged] 标准 1 — 登录接口返回 200
- [unchanged] 标准 2 — pytest 返回 0 failures
- [ ] 标准 3 — 分歧分析含 ≥3 组，每组 ≥200 字，JSON 格式含实践后果段落
```
