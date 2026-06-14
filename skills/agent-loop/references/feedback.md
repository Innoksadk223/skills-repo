# FEEDBACK 阶段手册

Orchestrator 在 Worker 完成产出后、或主 agent 验收 FAIL 后，调用 Feedbacker subagent 生成反馈和修正 prompt 时加载。**整个 Loop 只用一个 Feedbacker 实例，多轮修正复用同一实例。**

## Feedbacker 分派

Feedbacker 是独立 subagent，只读 worktree，只写反馈。

```
分派 Feedbacker subagent，goal 包含：

你是独立反馈员。审核 Worker 产出，找出根因或提质空间，写出可直接交给 Worker 执行的修正 prompt。

输入：
- 原始 PLAN（当前轮次）
- Worker 的产出和证据（阅读 state/ 目录下的文件）
- 主 agent 的验收记录（若已有，含失败项、证据不足项或提质要求）

输出结构化内容：
1. 根因分析 — 不是描述现象，是找出为什么 Worker 没做到
2. 给 Worker 的修正 prompt — 可直接发给 Worker，让它继续修正。必须自包含：Worker 可能看不到之前的对话，prompt 里要包含它需要知道的所有上下文（当前产出哪里不够、期望改成什么样、格式/约束/证据要求）
3. 修正后的 handoff 条件（如有变化）
4. 是否需要新增、替换或强调 skill/reference
5. 判定：继续修正还是交给主 agent VERIFY

toolsets: ["file"]
```

## Feedbacker 输出 schema

```json
{
  "failed_checklist_items": ["标准 2", "标准 4"],
  "root_cause": "Worker 收到的步骤描述缺少输出格式约束，导致产出结构不完整",
  "failure_type": "prompt_gap | missing_skill | skipped_skill_gate | weak_validation | bad_state | budget_limit | external_blocker",
  "decision": "continue_fix | proceed_to_verify | stop_with_blocker",
  "worker_fix_prompt": "你是步骤 3 的 Worker。之前你产出了 state/step3_output.json，但缺少以下内容：1. 每组对比需包含实践后果段落（≥100 字）2. JSON 格式需含 'practical_consequences' 字段。请在已有产出基础上补充这些内容，更新 state/step3_output.json，完成后返回 handoff check。",
  "revised_handoff": "state/step3_output.json 存在且 jq '.groups[].practical_consequences | length >= 100' 返回 true",
  "required_skills_or_references": [],
  "change_rationale": "原描述缺少格式约束，补充了实践后果要求和 JSON schema"
}
```

**多 Worker 场景（串行或并行）中需要分别修正时**，用 `per_worker_fixes` 数组替代单个 `worker_fix_prompt`，每条含 `step_id` 指向原 Worker：

```json
{
  "decision": "continue_fix",
  "per_worker_fixes": [
    {"step_id": 1, "worker_fix_prompt": "Worker 1 的修正指令...", "revised_handoff": "..."},
    {"step_id": 2, "worker_fix_prompt": "Worker 2 的修正指令...", "revised_handoff": "..."}
  ]
}
```

单 Worker 时用 `worker_fix_prompt` 字段不变。Orchestrator 将每条 `worker_fix_prompt` 发给对应的原 Worker——Worker 1 的 prompt 只给 Worker 1，Worker 2 的 prompt 只给 Worker 2。

**`worker_fix_prompt` 是核心字段**——它不是给 Orchestrator 看的分析，而是下一轮直接发给 Worker 的执行指令。必须：
- 具体指出当前产出哪里不够（引用 worktree 中的文件内容或路径）
- 明确期望改成什么样（格式、内容、证据要求）
- 自包含——即使宿主只支持 one-shot、Worker 看不到前序对话，也能靠这个 prompt + worktree 文件继续修正

## Orchestrator 使用反馈的流程

1. **先看 `decision`**：
   - `continue_fix` → 将 `worker_fix_prompt` 转发给对应步骤的 Worker，让它继续修正
   - `proceed_to_verify` → 进入 VERIFY
   - `stop_with_blocker` → 进入 DELIVER，标注阻塞原因
2. **转发修正 prompt**：将 Feedbacker 的 `worker_fix_prompt` 原样发给 Worker——不修改、不转述、不"优化"。Orchestrator 只做信使。
3. **更新 plan delta**：
   - 不变步骤 → 引用标记 "步骤 X 不变（已 PASS）"
   - 修正步骤 → 用 Feedbacker 的 `worker_fix_prompt` + `revised_handoff`
   - Skill 变更 → 加进 Loop Contract
4. **保持已通过项目的 state/ 文件**——不删除，Worker 修正时可参考
5. **Worktree 写回**：Feedbacker 将完整输出写入 `state/feedback_round_N.json`，供 Worker 在修正时参考
6. **如果 Feedbacker 诊断无法操作**（根因模糊、修正不具体）→ 在 delta plan 中标注不确定性，但仍尝试执行一轮
7. **如果根因是 weak_validation** → 优先加强 checklist 或证据要求，不只改 Worker 文案
8. **如果根因是 skipped_skill_gate** → 不扩大 prompt；把对应 skill 的 hard gate 写进 Worker 指令和 checklist
9. **如果 Feedbacker 返回无效输出**（缺失必填字段、decision 值不合法、JSON 解析失败）→ Orchestrator 重试一次分派 Feedbacker。仍失败则视为 `stop_with_blocker`，进入 DELIVER 并标注「Feedbacker 评估失败」。

## 示例：合并后的 delta plan

```markdown
## Plan Delta（第 2 轮）
### 保持不变的步骤
- 步骤 1–2 不变（已 PASS，state/step1_output.json + state/step2_output.json）
### Loop Contract 变更
- 本轮 Skill/Reference 新增：academic-search
### 变更步骤
3. 补充实践后果段落，每组 ≥100 字。输出 JSON 格式含 "practical_consequences" 字段。
   - Worker 修正 prompt：见 state/feedback_round_2.json 中的 worker_fix_prompt
   - handoff 条件：state/step3_output.json 存在且 jq '.groups[].practical_consequences | length >= 100' 返回 true
   - 变更原因：第 1 轮缺少输出格式约束，Worker 产出缺少实践后果段落
### 更新后 Checklist
- [unchanged] 标准 1 — 登录接口返回 200
- [unchanged] 标准 2 — pytest 返回 0 failures
- [ ] 标准 3 — 分歧分析含 ≥3 组，每组含实践后果 ≥100 字，JSON 格式含 practical_consequences 字段
```
