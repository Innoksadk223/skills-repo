# Loop Contract 模板

> 复制此文件到 `state/[task-slug]/loop_contract.md`，填入任务参数。这是 Agent Loop 的唯一配置入口。

---

## 意图

<!-- 用户真正要达成的结果，一句话 -->
[例如：修复 backend API 单元测试，使 pytest 全部通过]

## 完成判定

<!-- 最终怎样才算完成，必须可验证 -->
[例如：`pytest tests/` 退出码 0，且 `npm run build` 无 error]

## 非目标 / 范围边界

<!-- 写清本轮不做什么，防止审查或修正无限膨胀 -->
- 不做：[例如：不重构无关模块]
- 不做：[例如：不新增 runner 自动化或新脚本]
- 不做：[例如：不改变用户未要求的功能行为]

## 停止护栏

| 护栏 | 值 |
|------|-----|
| 最大修正轮数 | 3（硬上限） |
| 边际收益阈值 | 改进 < 10% → 收敛交付 |
| 资源预算 | [可选，人工监控，非代码强制：45min / 20k token] |

## 当前轮状态

<!-- 每轮 AUDIT 前更新，让审查 Agent 明白现在审什么 -->
- 轮次：Round [N]
- 当前任务：[首轮执行 / 修正反馈 / 上诉裁决 / 最终验证]
- 本轮变更证据：[文件路径 / diff 摘要 / 命令输出 / 产出物路径]
- 上轮反馈：`state/[task-slug]/feedback.md`（首轮写“无”）
- 上诉文件：`state/[task-slug]/appeal.md`（无上诉写“无”）

## 审查 Agent 作用域

<!-- 同一会话 + 同一工作目录 + 同一系列任务复用同一个审查 Agent；同一目标的连续追加请求也算同一系列 -->
- 会话标识：[当前对话 / CLI session / thread]
- 工作目录：[绝对路径]
- 任务系列：[例如：agent-loop 自身优化；同一目标的连续追加请求也算同一系列]
- 是否同一系列：[是 / 否；理由]
- 共享审查 Agent ID：`state/session_auditor_id.txt`
- 当前任务指针：`state/[task-slug]/auditor_id.txt`（指向或复制共享 ID）
- 允许新建审查 Agent 的例外：[无可续接共享 Agent / 工作目录变化 / 任务系列不相关 / 用户明确重置]

## 长期状态 progress.md

<!-- 这是跨轮状态脊柱。每轮开始前读取，每轮结束后更新 -->
- 路径：`state/[task-slug]/progress.md`
- done：[已经完成且有证据的事项]
- tried：[尝试过的方案 / 失败原因 / 上诉结果]
- next：[下一步动作或停止后的建议]
- open：[未解决问题 / 阻塞 / 风险]
- user-confirm：[需要用户确认的取舍或外部动作]
- cost：[本轮耗时 / 调用的 agent 或工具 / 是否值得继续 / 停止原因（如适用）]

## 等待审查期间状态维护

<!-- 审查 Agent 处理 AUDIT 时，主 Agent 只维护状态，不改变审查对象 -->
- 允许：[更新 progress.md / 补写 inbox.md / 整理 handoff 证据 / 记录成本与阻塞 / 检查共享审查 Agent ID]
- 禁止：[修改已提交审查的正式产物 / 新增未进契约的功能或自动化 / 预判审查结论 / 覆写 feedback.md]
- 审查责任：[审查 Agent 在 feedback.md 指出状态遗漏；小项目默认不新增独立记忆维护 Agent]

## 待处理箱 inbox.md

<!-- 不能自动继续的事项写到跨任务待处理箱；主 Agent 写，审查 Agent 只读并指出遗漏 -->
- 路径：`state/inbox.md`
- 写入触发：[需要用户确认 / 外部阻塞 / 低收益暂停 / 硬上限 / 上诉死锁 / 后续风险]
- 记录字段：[任务标识 / 优先级 / 原因 / 当前状态 / 建议动作 / 来源文件]

## 恢复规则

<!-- 恢复 loop 时先读 progress.md 与 inbox.md，再路由 -->
- 若 `user-confirm` 非空：先问用户，暂停自动执行
- 若存在上诉待处理：恢复同一审查会话处理上诉
- 若 `next` 指向未完成修正：继续 ACT
- 若上轮 `DECISION: PROCEED_TO_VERIFY`：恢复同一审查 Agent 进入 VERIFY，输出 `state/[task-slug]/final_verify.md`
- 若已有 `final_verify.md` 且 `VERDICT: VERIFIED`：进入 DELIVER
- 若已有 `final_verify.md` 且 `VERDICT: RETURN_TO_LOOP`：读取 `OPEN_ISSUES` 后回到 LOOP
- 若 `cost` 或停止原因显示低收益、硬上限、上诉死锁或阻塞：停止并汇报

## 成本 / 预算观测

<!-- 每轮更新，用于判断继续还是停止 -->
- 本轮耗时：[例如：12min]
- 调用的 agent / 工具：[例如：auditor agent, pytest, rg]
- 是否值得继续：[是 / 否；理由]
- 停止原因（如适用）：[PROCEED_TO_VERIFY / VERIFIED / STOP_WITH_BLOCKER / 改进<10% / 硬上限 / 上诉死锁]
- 预算风险：[是否出现工具/agent 调用过多、耗时过高、继续收益低、应降级或应询问用户]

## 执行步骤

<!-- 每步写「做什么 + 做到什么程度」+ 可自动判定的 handoff 条件 -->
1. [步骤名] — [做什么 + 做到什么程度]
   - handoff 条件：[产出物路径 / 验证命令]
2. [步骤名] — [做什么 + 做到什么程度]
   - handoff 条件：[...]

## 验收 Checklist

<!-- 每项：可量化、二元、附证据要求 -->
- [ ] 标准 1 — [如：登录接口返回 200 + JWT token，提供 curl 输出]
- [ ] 标准 2 — [如：pytest 返回 0 failures，提供 pytest -v 输出]
- [ ] 标准 3 — [如：npm run build 退出码 0]

## 审查输入包

<!-- AUDIT 前逐项确认；缺项先补 handoff，不让审查 Agent 猜 -->
- [ ] 用户目标：见“意图”
- [ ] 非目标：见“非目标 / 范围边界”
- [ ] 计划：见“执行步骤”
- [ ] 当前轮：见“当前轮状态”
- [ ] 变更证据：见“当前轮状态”
- [ ] 验收 Checklist：见“验收 Checklist”
- [ ] 上轮反馈或上诉：见“当前轮状态”
- [ ] 审查 Agent 作用域：见“审查 Agent 作用域”
- [ ] 长期状态：见 `progress.md`
- [ ] 待处理箱：见 `state/inbox.md`
- [ ] 恢复规则：见“恢复规则”
- [ ] 成本/预算观测：见“成本 / 预算观测”

## 最终汇报格式

<!-- 像产品经理向老板汇报：先讲结果，再讲依据与下一步 -->
- 本次完成了什么：[一句话说明业务/任务结果]
- 为什么这样做：[关键判断与取舍]
- 结果是否达标：[对照验收 Checklist]
- 风险与遗留问题：[只列影响后续决策的风险]
- 下一步建议：[1-3 个可执行建议]

## 需加载的技能

<!-- 先选 Skill，再写步骤。无匹配 skill 时写 "无可复用 skill" -->
- [skill-name] — [用途]

## 工作区

<!-- 每次任务生成唯一 slug（如 task-20260615-fix-auth），防止多次运行 state 冲突 -->
- 任务标识：`[task-slug]`（如 `fix-login-20260615`）
- 产出目录：`state/[task-slug]/`
- 源码目录：[如：`src/`]
- 测试目录：[如：`tests/`]
