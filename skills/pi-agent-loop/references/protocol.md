# Pi Agent Loop Protocol

按 SKILL 的阶段表渐进读取。TeamState/Plan/ExecutionTask/ReviewRound/ExpertRound 是结构化协议；`leader/plan.md` 只是精简恢复视图，child Session 和按需 output/handoff 保存长正文。

## 目录

1. 角色 prompt · 2. Plan 与派发 · 3. Settled envelope · 4. Review/Fix/Final · 5. Expert/Optimizer · 6. HUMAN_ACCEPT · 7. 恢复与压缩 · 8. 停止与交付

## 1. 角色 Prompt

### Coder

```md
你是计划内 Coder <id>。主 Pi 是唯一 Leader。
输入：runtime 生成的最小 TaskPacket（taskId/attempt/objective/constraints/dependency summaries/owned paths/acceptance/relevant paths/output contract）和可选 Reviewer fix_prompt 原文。
权限：只写 owned paths；只执行当前 task/attempt；验证按用户全局授权运行（测试/构建/typecheck/lint/doctor/浏览器/真实模型冒烟无需逐次确认，真实模型冒烟执行前说明预期费用）。
输出：简短正文 + 最后一行 execution JSON envelope。
禁止：不读无关共享历史；不改计划外路径；不创建 Agent；不输出 VERIFIED/FINAL_VERIFY；不把 fix 变成新任务；不自动重放。
阻塞：status=BLOCKED，并在 requests 中把问题交 Leader。
```

### Reviewer

```md
你是计划指定 Reviewer，也是唯一判定角色。独立只读，不参与实现。
输入：ReviewRound id、目标 TaskPacket、attempt、submission summary/evidence/outputPath。
检查：contract/completeness/correctness/reuse/budget/evidence-regression；第 2+ 轮核对旧 fix 是否关闭。
输出：简短正文 + 最后一行 review JSON envelope；每个目标恰好一个 VERIFIED 或 FIX_REQUIRED。
FIX_REQUIRED：给完整、可执行、单一目标的 fix_prompt（目标/证据/必改/禁改/验证/回报）；Leader必须原样转交。
禁止：不改交付物；不接受 Coder 自报 PASS；不遗漏目标；不替 Leader扩大范围。
FINAL_VERIFY：在所有必要 task VERIFIED、专家门已关闭后独立核对 acceptance，输出 `FINAL_VERIFY: VERIFIED|RETURN_TO_LOOP|STOP_WITH_BLOCKER` 给 Leader；此文本不直接改 ExecutionTask verdict。
```

### Debugger

```md
你是计划内 read-only debugger。调查复杂根因，读取目标 TaskPacket/状态/代码/日志；不改交付物、不写 verdict。输出证据链、候选修复和验证建议，最后一行 expert JSON envelope。修复仍由原 Coder task 的 Reviewer fix attempt 或 amendment 后的新 task 落地。
```

### Product

```md
你是计划内 read-only product expert。仅在 Leader授权的实际体验入口上报告旅程、问题、建议和阻断项；不改代码、不替用户验收、不写 verdict。最后一行 expert JSON envelope。
```

### Optimizer

```md
你是计划内 read-only optimizer，仅附着 VERIFIED task。扫描实际 changed/relevant paths，检查 functionality/conciseness/maintainability；不给空泛建议。
候选需写可复查收益、成本、风险、是否改变已验证基线。无候选明确 summary=NO_CANDIDATE。
不改交付物、不写 verdict。候选交 Leader；任何落地都需 plan amendment 注册新 optimization task，再回 Coder -> Reviewer。
最后一行 expert JSON envelope。
```

未知角色不动态创建。若固定 kind 不覆盖需求，先 plan amendment / USER_GATE 明确新成员；当前 runtime 的 ExpertRound 只支持 debugger/product/optimizer。

## 2. Plan 与派发

Plan 一次固定：

- roster：`id/kind/role/instructions/model?/thinking?/tools?`；
- `reviewerId`：必须指向 kind=reviewer；
- tasks：`id/memberId/objective/constraints/dependsOn/ownedPaths/acceptance/relevantPaths/outputContract?`；
- global acceptance。

ownedPaths 是 cwd 相对具体路径或目录前缀；拒绝绝对路径、反斜杠、`.`、`..`、越界和规范化重复。路径相等或 `a` 是 `a/b` 父前缀即冲突。无依赖顺序的计划任务不能拥有冲突路径。

调用：

```text
plan(plan)                                  # initial revision 1
plan(expectedRevision=N, plan=complete)     # amendment N+1
run(taskId)
parallel(taskIds[])
review(reviewRoundId, taskIds[])
expert(expertRoundId, expertId, taskIds[], objective)
```

Leader只启动实时状态允许的节点。runtime 完整 preflight 后才准备 Dashboard/client；整批任何失败都不发送 prompt。TaskPacket 不含完整 roster、全局计划或历史正文。

## 3. Settled Envelope

最后一个非空行必须是单行 JSON，不用代码围栏。正文可在前；runtime 只解析最后一行。

Execution：

```json
{"agent_team_report":{"type":"execution","taskId":"task-a","status":"SUBMITTED","summary":"short factual result","evidence":["path/ref"],"requests":[{"kind":"question","text":"Leader decision needed"}]}}
```

`status` 仅 `SUBMITTED|BLOCKED`。

Review：

```json
{"agent_team_report":{"type":"review","reviewRoundId":"review-1","summary":"audit result","evidence":["path/ref"],"requests":[],"decisions":[{"taskId":"task-a","verdict":"FIX_REQUIRED","fix_prompt":"完整原样 prompt"}]}}
```

每个 target 恰好一次。`FIX_REQUIRED` 必须有 1-8000 字符 fix_prompt；`VERIFIED` 禁止 fix_prompt。

Expert：

```json
{"agent_team_report":{"type":"expert","expertRoundId":"expert-1","summary":"finding or NO_CANDIDATE","evidence":["path/ref"],"requests":[]}}
```

通用限制：summary 1-2000；evidence 最多 20 条、每条 1-1000；requests 最多 10 条，kind=`question|scope|dependency|human`、text 1-1000。额外字段、错误 type/ID、损坏 JSON、缺行、越界均无效。

无效 execution -> task `REPORT_INVALID` 并持锁。无效 review/expert -> round `REPORT_INVALID`；review targets 回 `SUBMITTED` 以便 Leader显式创建新 round，ownership 仍由 task 持有。不猜测、不重试。

## 4. Review、Fix 与 Final

ReviewRound 只接 SUBMITTED task，启动后目标为 AUDITING。合法决策：

- VERIFIED：释放该 task ownership；其所有前置均 VERIFIED 的 PENDING 依赖转 READY。
- FIX_REQUIRED：保存 fix_prompt 原文；ownership 不释放。

Leader不合并、弱化或改写 fix_prompt。再次 `run(taskId)` 自动携带原文并使 `attempt += 1`。Coder重新 SUBMITTED 后创建新 ReviewRound。连续两轮同根因无实质进展，停问用户。

所有交付 task VERIFIED 且专家门关闭后，Leader要求同一 Reviewer 做 FINAL_VERIFY：逐项核对全局 acceptance、最新 task verdict/证据、未决 requests、已知限制和未授权验证。FINAL_VERIFY 不替代 HUMAN_ACCEPT。

## 5. Expert 与 Optimizer

ExpertRound 附着一个或多个现有 task；只保存当前 summary/evidence/requests/outputPath。它不取 ownership，不改变 ExecutionTask。

- debugger：复杂根因才启用；报告交 Leader决定是否由 Reviewer产生 fix_prompt或 amendment。
- product：只体验和报告；不替用户验收。
- optimizer：只附着 VERIFIED task。NO_CANDIDATE 可关闭门；候选由 Leader评估。

Optimizer 候选若需改交付物，已验证 task 不直接重开。Leader通过 amendment 添加独立 optimization task、ownership 与 acceptance，重新 USER_GATE，再执行 Coder -> Review。低价值、风险高、新依赖或合约外 enrichment 可拒绝/延期，但理由保留在 expert summary。

## 6. HUMAN_ACCEPT

FINAL_VERIFY: VERIFIED 后，Leader向用户提交：

```md
STATUS: PENDING_ACCEPT
COMPLETION_CRITERIA: <逐项>
EVIDENCE: <TeamState summary、路径、已授权命令输出>
LIMITS: <未运行验证/风险>
EXPERIENCE_ENTRY: <手工入口>
```

- ACCEPTED：允许 DELIVER。
- REJECTED（合约内缺陷）：回 Review/Fix 循环。
- REJECTED（合约外需求）：plan amendment / USER_GATE。

Agent 不能替用户写 ACCEPTED。

## 7. 恢复与压缩

恢复路由：

1. `status` 获取实时计数、当前对象、阻塞、requests；确需完整 packet 才 `full:true`。
2. RUNNING 经父 session 恢复为显式 BLOCKED/INTERRUPTED，不重放。
3. REPORT_INVALID：检查 child Session/按需 output，Leader显式重跑同 task 或新 round。
4. FIX_REQUIRED：原 task 新 attempt。
5. SUBMITTED：新 ReviewRound。
6. VERIFIED：检查依赖 READY、专家门、FINAL/HUMAN gate。
7. 新成员/任务/范围：amendment。

成员启动时启用 Pi 原生 auto-compaction；orchestrator 不设自定义阈值、不在 settled 后主动调用 compact、不写压缩交接文件。原生压缩或会话失败表现为 `ERROR/INTERRUPTED`，不自动重放。Leader显式决定是否轮换接续；需要交接时由 Leader自行记录目标、边界、决策、已改文件、证据、未决、依赖、ownership 和下一步，并引用 TeamState taskId/leader plan。

## 8. 停止与交付

停问用户：同根因两轮无进展、合约变化、外部服务/权限/预算/安全风险、不可逆操作或 HUMAN_ACCEPT 合约外反馈。

DELIVER 汇总 changed/why、criteria、evidence、未运行验证、风险和 HUMAN_ACCEPT 结果。不删除旧 workspace、Session、计划或用户文件；清理需另行授权。
