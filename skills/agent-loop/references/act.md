# ACT 阶段手册

Orchestrator 分派 Worker subagent 执行任务、处理反馈修正回合时加载。

## Worker 分派

使用宿主可用的 subagent / worker 分派入口。每个 Worker 以 leaf 角色运行（不给二次分派权限）。

**首轮分派**：
```
分派 Worker subagent，goal 包含：
- 步骤的完整描述 + 输出格式 + 验收标准
- 必须调用的 skill/reference（如有）
- 输出路径：将结果写入 state/stepN_output.json
- handoff check：返回中写明 "handoff check: [产出物路径] 已验证存在"

toolsets: 最小必要集（如 ["terminal", "file", "web"]）
```

**修正回合**（Worker 已产出初稿，收到 Feedbacker 的修正 prompt 后）：
```
向同一个 Worker（或具备其上下文的等效实例）发送：
- Feedbacker 的 worker_fix_prompt（原样转发）
- 当前 worktree 中相关文件的路径
- 要求：在已有产出基础上修正，更新 worktree 文件，返回 handoff check

如果宿主不支持 subagent 多轮对话：重新分派 Worker，goal = worker_fix_prompt + "当前 worktree 文件在 state/ 中，请先阅读它们，然后在已有基础上修正"
```

## Worker 约束

- **leaf 角色** — 不给二次分派权限
- **toolsets 最小集** — 只给完成当前步骤必要的工具
- **skill 优先** — Worker goal 中如指定 skill/reference，必须先加载并按其流程执行
- **hard gate 不绕过** — 指定 skill 若要求审批、RED 测试、设计文档或验证命令，Worker 必须完成并返回证据，不能跳过
- **skill 加载失败立即报告** — 如指定 skill/reference 文件不存在或无法读取，Worker 必须在返回中报告 `handoff check: FAIL — skill [名称] 加载失败`，Orchestrator 暂停后续步骤并标注阻塞
- **修正回合不重做已完成的部分** — Worker 收到修正 prompt 后，只改被指出问题的部分，保留已有正确内容

## Worker 必须做的事

1. **执行分配的步骤** — 严格按 goal 描述的范围
2. **读取 worktree** — 先检查相关 `state/` 文件。首轮：确认 worktree 结构；修正回合：读取已有产出和 feedback 文件
3. **返回产出 + 证据** — 针对每个 checklist 项提供可核验的证据（文件路径、命令输出摘要）
4. **返回 skill 遵循证据** — 如本步骤指定了 skill/reference，说明已加载哪个文件、完成了哪些 hard gate
5. **自检 handoff 条件** — 确认产出物存在且格式正确，在返回中明确写：

```
handoff check: [产出物路径] 已验证存在
```

handoff 不通过时——Worker 不应交棒，而是自行修复或报告失败。

## Orchestrator mini-check 流程

每个步骤完成后：

1. 检查 Worker 返回是否包含 `handoff check:` 确认行
2. 如果 Worker 报告了失败 → **暂停，不跑后续步骤**
3. 如果 handoff 通过 → 启动下一步 Worker（或继续等待并行 batch）
4. 如果 Worker 返回中没有 handoff check → 标记为异常，要求 Worker 补充

## 修正回合的协调

Worker 产出初稿 → Feedbacker 审核 → **Feedbacker 的 worker_fix_prompt 发回同一个 Worker**：

1. Orchestrator 收到 Feedbacker 的反馈输出（含 worker_fix_prompt）
2. 如果 `decision == "continue_fix"`：
   - 将 worker_fix_prompt（或 per_worker_fixes 中对应 step_id 的 prompt）原样发给对应 Worker（转发规则详见 feedback.md）
   - Worker 读取 worktree（含 feedback 文件），在已有产出上修正
   - Worker 更新 worktree 文件，返回新的 handoff check
3. 如果 Worker 修正后 Feedbacker 仍判断未通过 → 重复步骤 2（受终止条件约束）
4. 如果 decision == proceed_to_verify → 进入 VERIFY
5. **硬规则：修正完成后，Orchestrator 必须重新调用同一个 Feedbacker 评估修正结果，不得跳过 Feedbacker 直接进入 VERIFY。** 每次 ACT-FIX 后必须进入 FEEDBACK，由同一个 Feedbacker 判定是否 proceed_to_verify。

**如果宿主只支持 one-shot subagent**：Orchestrator 重新分派 Worker 时，goal 需包含完整上下文。模板：

```
[原始任务摘要，≤3 句]
[已有 worktree 文件内容摘要]
[Feedbacker 的 worker_fix_prompt，原样粘贴]
```

等效于"同一个 Worker 继续"的效果。

## 并行 batch 协调

- 无文件依赖的步骤 → 一组 Worker 并行分派
- 所有 Worker 完成后统一进入 FEEDBACK
- batch 中某个 Worker 失败 → 等待全部完成（或超时），汇总后统一进入 Feedbacker
- 成功步骤的产出保留（worktree 文件不删），Feedbacker 只处理失败项
- 修正回合只对失败步骤的**原 Worker**进行——Worker 1 的产出由 Worker 1 修正，Worker 2 不越界

## 产出物落盘（worktree）

Worker 产出应写入 `state/` 目录（worktree）：

```
state/
├── step1_output.json       ← Worker 1 产出
├── step2_output.json       ← Worker 2 产出
├── step2_evidence.txt      ← 验证命令输出摘要
├── feedback_round_1.json   ← Feedbacker 第 1 轮反馈（含 worker_fix_prompt）
├── feedback_round_2.json   ← Feedbacker 第 2 轮反馈
└── ...
```

Orchestrator 在分派 Worker 时在 goal 中指定输出路径。PLAN 阶段由 Orchestrator 负责创建 `state/` 目录；如 Orchestrator 无法创建文件，由首个 Worker 在执行前创建。

## 反馈闭环

每个 Worker 返回都必须包含三类信息：

| 信息 | 用途 |
|------|------|
| 产出路径 | Feedbacker / 主 agent 读取 |
| 证据路径或命令输出摘要 | 防止口头 PASS |
| skill/hard gate 证据 | 防止把 skill 降级成一次性 prompt |
| 下一步建议 | 供 Orchestrator 判断是否需要调整后续 Worker goal |

Orchestrator 可以参考 Worker 的下一步建议，但不能把它当验收结论。
