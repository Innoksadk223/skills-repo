# 本地模拟模式

宿主不支持 subagent 分派时，Orchestrator 在本地按 Worker/Feedbacker 角色分步执行。流程逻辑不变——PLAN → ACT → FEEDBACK → ACT-FIX → VERIFY 全保留，只是角色由主 agent 依次扮演。

## 何时触发

- 宿主无 subagent / worker 分派入口
- subagent 分派失败且重试无效
- 用户明确要求本地执行

## 角色切换协议

每个阶段开始前，Orchestrator 声明切换：

```
[角色切换：Orchestrator → Worker]
```

阶段结束后返回：

```
[角色切换：Worker → Orchestrator]
```

## Worker 本地模拟

1. **读 worktree** — 先检查 `state/` 目录，复用已有产出
2. **执行步骤** — 按 goal 描述执行，写入 `state/stepN_output.json`
3. **自检 handoff** — 确认产出物存在且格式正确
4. **返回证据** — 输出 `handoff check: state/stepN_output.json 已验证存在`

关键约束：
- 不跳过 skill 的 hard gate（TDD、设计确认等）
- 修正回合读 `state/feedback_round_N.json` 中的 `worker_fix_prompt`，在已有产出上修正
- 产出写入 worktree，不只在对话中描述

## Feedbacker 本地模拟

1. **读 worktree** — 阅读 `state/` 中所有 Worker 产出
2. **诊断根因** — 对照 checklist 逐项检查
3. **写出 worker_fix_prompt** — 自包含的修正指令
4. **写入 worktree** — 输出保存到 `state/feedback_round_N.json`

关键约束：
- Feedbacker 不直接改 Worker 产出
- `worker_fix_prompt` 必须具体（指出当前产出哪里不够、期望改成什么样）
- 输出必须含 `decision` 字段

## 与 subagent 版的差异

| 方面 | subagent 版 | 本地模拟版 |
|------|-----------|-----------|
| 上下文隔离 | 天然隔离 | 需角色切换声明 |
| 并行 Worker | 支持 | 不支持（串行模拟） |
| token 代价 | 子 agent 独立计费 | 全在主 agent 上下文 |
| 修正轮数 | 建议 ≤3 | 建议 ≤2（防上下文膨胀） |
| 验收标准 | 不变 | 不变 |
