# ACT 阶段手册

Orchestrator 分派 1-N 个 Worker subagent 和执行 mini-check 时加载。

## Worker agent 分派格式

`delegate_task` / `spawn_agent` 是分派入口；被分派对象的身份是 Worker agent。若宿主支持批量 tasks，则每个 task 对应 1 个 Worker subagent；若只支持逐个分派，则为每个 task 单独启动 1 个 worker agent。

```python
# 批量分派示意：每个 task = 1 个 Worker agent
delegate_task(tasks=[
    {
        "goal": "步骤 N 的完整描述 + 输出格式 + 验收标准 + 必须调用的 skill/reference",
        "toolsets": ["terminal", "file", "web"]  # 最小必要集
    },
    ...
], context="原始需求：[全文]。验收标准：[checklist]。只做分配的步骤，返回产出+证据。")
```

## Worker 约束

- **leaf 角色** — 不给二次分派权限（防止 Worker 私自分派子 agent 做验收）
- **≤3 并行** — 无依赖步骤 batch 分派，上限 3
- **toolsets 最小集** — 只给完成当前步骤必要的工具，不给多余权限
- **skill 优先** — Worker goal 中如指定 skill/reference，必须先加载并按其流程执行；不得临时重写一套长 Prompt 替代
- **hard gate 不绕过** — 指定 skill 若要求用户确认、RED 测试、设计文档或验证命令，Worker 必须完成并返回证据，不能以"Loop 已经有计划/检查"为由跳过

## Worker 必须做的事

1. **执行分配的步骤** — 严格按 goal 描述的范围，不越界做其他步骤
2. **读取状态** — 先检查相关 `state/` 文件，复用已通过产出，不重复执行已 PASS 的步骤
3. **返回产出 + 证据** — 针对每个 checklist 项提供可核验的证据（文件路径、命令输出摘要）
4. **返回 skill 遵循证据** — 如本步骤指定了 skill/reference，说明已加载哪个文件、完成了哪些 hard gate
5. **自检 handoff 条件** — 确认产出物存在且格式正确，在返回中明确写：

```
handoff check: [产出物路径] 已验证存在
```

handoff 不通过时——Worker 不应交棒，而是自行修复或报告失败。

## Orchestrator mini-check 流程

每个步骤完成后（或并行 batch 全部完成后）：

1. 检查 Worker 返回是否包含 `handoff check:` 确认行
2. 如果 Worker 报告了失败 → **暂停，不跑后续步骤**
3. 如果 handoff 通过 → 启动下一步 Worker（或继续等待并行 batch）
4. 如果 Worker 返回中没有 handoff check → 标记为异常，要求 Worker 补充

**不等全跑完才检查。** 第 2 步错在第 3 步才发现的代价远大于逐步 mini-check。

## 并行 batch 协调

- 无文件依赖的步骤 → 一组 Worker agent 并行分派（如 `delegate_task(tasks=[...])`）
- 所有 Worker 完成后统一进入 CHECK
- batch 中某个 Worker 失败 → 等待全部完成（或超时），汇总后统一进入 Troubleshooter
- 成功步骤的产出保留（state/ 文件不删），Troubleshooter 只处理失败项

## 产出物落盘

Worker 产出应写入 `state/` 目录供 Evaluator 独立核验：

```
state/
├── step1_output.json    ← Worker 1 产出
├── step2_output.json    ← Worker 2 产出
├── step2_evidence.txt   ← 验证命令输出摘要
└── ...
```

Orchestrator 在分派 Worker 时应在 goal 中指定输出路径，例如：
> "将最终结果写入 state/step1_output.json，然后在返回中写 handoff check: state/step1_output.json 已验证存在"

## 反馈闭环

每个 Worker 返回都必须包含三类信息：

| 信息 | 用途 |
|------|------|
| 产出路径 | Evaluator 独立读取 |
| 证据路径或命令输出摘要 | 防止口头 PASS |
| skill/hard gate 证据 | 防止把 skill 降级成一次性 prompt |
| 下一步建议 | 供 Orchestrator 判断是否需要调整后续 Worker goal |

Orchestrator 可以参考 Worker 的下一步建议，但不能把它当验收结论。
