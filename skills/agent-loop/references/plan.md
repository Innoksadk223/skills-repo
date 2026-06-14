# PLAN 阶段手册

Orchestrator 制定和修订执行计划时加载。

## PLAN 输出格式（首轮完整版）

```markdown
## Plan（第 N 轮）
### Loop Contract
- 意图：[用户真正要达成的结果，一句话]
- 完成判定：[最终怎样才算完成，必须可验证]
- 停止护栏：[最大轮数 / token 或费用上限 / 时间上限]
- Worktree 目录：state/
- 本轮 Skill/Reference：[要调用的 skill 或 reference；没有可复用 skill 时才写一次性 prompt]
- Skill 优先级：[agent-loop 为外层调度器；列出其它 skill 的 hard gate 如何进入 handoff/checklist]
### 步骤
1. [步骤名] — [做什么 + 做到什么程度]
   - handoff 条件：[产出物路径 / 验证命令 / 必须存在的文件]
2. [步骤名] — [做什么 + 做到什么程度]
   - handoff 条件：[...]
### 边界条件
- 不在范围：...
### 验收 Checklist
- [ ] 标准（可量化、二元、附证据要求）
### 执行策略
- Worker 数：[1-N；按依赖、预算和宿主能力决定并行度]
- 依赖说明：[步骤 X 依赖步骤 Y 的产出文件 → 串行 / 所有步骤无文件依赖 → 并行]
- Worker toolsets: [...]
- 预算策略：[每轮最多 N 个 Worker / 超过 X 分钟或 Y token 停止]
```

## 步骤设计规则

**编码「做什么 + 做到什么程度」，不写结构标签。**

| ❌ 错误 | ✅ 正确 |
|--------|--------|
| "写共识与分歧" | "分析 ≥3 组分歧，每组含双方代表论文、核心论据、实践后果，每组 ≥200 字" |
| "生成测试" | "为 src/auth.py 写 pytest，覆盖 login/logout/token-refresh 三条路径，断言 HTTP 状态码" |
| "搜索文献" | "用 academic-search 检索近 3 年 'RLHF alignment' 相关论文，筛选引用 >10 的，上限 15 篇" |

**每个步骤 → ≥1 个 checklist 项。** 步骤和 checklist 交叉覆盖，不留盲区。

**先选 Skill，再写步骤。** 如果某步是重复能力（搜索、代码审查、文档生成、调试、验证），优先指定已有 skill/reference；只有没有可复用单位时才写一次性执行描述。Loop 的资产是经过测试的 Skill，不是越写越长的 Prompt。

## 多 Skill 组合规则

**agent-loop 管流程，其它 skill 管专业动作。** 当任务同时触发 TDD、brainstorming、writing-plans、frontend-design、academic-search 等技能时，不在它们之间二选一；把它们放进 Loop Contract 和步骤里。

| 场景 | PLAN 写法 |
|------|-----------|
| 其他 skill 有 hard gate | 把 gate 写成 handoff 条件或 checklist，例如"设计已获用户确认"、"RED 测试已失败" |
| 其他 skill 要求先做计划/规格 | 该 skill 的计划/规格步骤成为 ACT 的前置步骤，未通过 mini-check 不进入实现 |
| 其他 skill 与 Loop 都要求验证 | 主 agent 在 VERIFY 阶段检查该 skill 的验证证据，而不是替它放行 |
| brainstorming 已完成设计确认 | 回到 agent-loop 的 PLAN/ACT，不让 brainstorming 接管后续流程 |
| 目标产物明确但验收标准模糊 | 在 PLAN 中先用 brainstorming 或领域 skill 补齐 checklist，再进入 ACT |
| 无匹配 skill | 才写一次性 prompt，并在 Loop Contract 标注"无可复用 skill" |

**禁止的降级：**
- ❌ "这个任务也触发 TDD，所以不用 agent-loop"
- ❌ "验收标准还不清楚，所以不用 agent-loop"
- ❌ "brainstorming 已要求写 plan，所以由 writing-plans 接管 agent-loop"
- ❌ "用户已经调用 agent-loop，但仍说没有显式授权 subagent"
- ❌ "只参考 loop 思想，直接按 prompt 执行"

正确做法：声明 agent-loop 已触发；调用本 skill 即视为明确进入 Loop，并授权使用宿主可用的 subagent / worker 分派能力。若不能分派，说明限制，并在本地按 Worker/Feedbacker 角色模拟，主 agent 仍负责最终验收。

## Handoff 条件设计

形式任选其一，但必须**可自动判定真伪**：

| 形式 | 示例 |
|------|------|
| 文件路径 | `state/step1_output.json` 存在且非空 |
| 验证命令 | `grep "PASS" result.txt` 返回非空 |
| Worker 自述 | "handoff check: 已确认 X 文件存在，格式为 JSON，含 3 个 key" |

**handoff 条件 ≠ 验收标准。** handoff 只管"产出物存在且格式对"，不管"质量好不好"——质量交给主 agent 的 VERIFY。

## Checklist 设计

每项必须：
- **可量化** — "测试通过"不是可量化的，"pytest 返回 0 failures"才是
- **二元** — PASS 或 FAIL，没有"基本完成""大致 OK"
- **附证据要求** — 明确"提供 pytest 输出""提供文件 md5"而非"代码正确"

示例：
```
- [ ] 登录接口返回 200，pytest test_login 全部通过（提供 pytest -v 输出）
- [ ] 分歧分析含 ≥3 组对比，每组 ≥200 字（提供 word count 命令输出）
```

## 停止护栏设计

PLAN 必须声明至少三类护栏：

| 护栏 | 示例 |
|------|------|
| 最大迭代 | `max_rounds = 3` |
| 无进展检测 | 连续 2 轮通过率提升 <10% → STAGNATE |
| 资源预算 | 超过 45 分钟 / 20k token / 指定费用上限 → 停止并交付当前状态 |

没有停止护栏，不允许进入 ACT。

## 执行策略：依赖判定规则

**文件依赖 = 串行。** 如果步骤 B 的 Worker goal 描述中包含步骤 A 产出文件的路径 → 串行。否则 → 可并行。

判定流程：
1. 扫描每个步骤的 goal 和 handoff 条件，提取引用的文件路径
2. 如果步骤 B 引用步骤 A 的产出路径 → A → B 串行
3. 所有剩余无依赖步骤 → 按宿主能力和预算组成 parallel batch
4. 串行链内部按依赖顺序逐个分派 Worker

**并行 batch 失败处理：** batch 中任一 Worker 失败 → 等待 batch 全部完成（或超时），将失败步骤信息汇总后统一进入 Feedbacker。

## 第 2 轮起 Delta 格式

只输出**变更部分**，不变步骤用引用标记：

```markdown
## Plan Delta（第 N 轮）
### 保持不变的步骤
- 步骤 1–2 不变（第 N-1 轮已 PASS）
### Loop Contract 变更（如有）
- 预算剩余：[...]
- 停止护栏调整：[只能收紧，不能默默放宽]
### 变更步骤
3. [步骤名] — [新描述]
   - handoff 条件：[新条件]
   - Worker 修正 prompt：见 state/feedback_round_N.json 中的 worker_fix_prompt
   - 变更原因：[Feedbacker 诊断 / 新增需求]
### 新增步骤（如有）
4. [新步骤] — [...]
### 删除步骤（如有）
- 原步骤 X 已删除，原因：[...]
### 更新后 Checklist（仅列出变更项）
- [ ] 标准（标记 [unchanged] 或完整重写）
```
