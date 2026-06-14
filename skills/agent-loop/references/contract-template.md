# Loop Contract 模板

> 复制此文件到 `state/loop_contract.md`，填入任务参数。这是 Agent Loop 的唯一配置入口。

---

## 意图

<!-- 用户真正要达成的结果，一句话 -->
[例如：修复 backend API 单元测试，使 pytest 全部通过]

## 完成判定

<!-- 最终怎样才算完成，必须可验证 -->
[例如：`pytest tests/` 退出码 0，且 `npm run build` 无 error]

## 停止护栏

| 护栏 | 值 |
|------|-----|
| 最大修正轮数 | 3（硬上限） |
| 边际收益阈值 | 改进 < 10% → 收敛交付 |
| 资源预算 | [可选，人工监控，非代码强制：45min / 20k token] |

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

## 需加载的技能

<!-- 先选 Skill，再写步骤。无匹配 skill 时写 "无可复用 skill" -->
- [skill-name] — [用途]

## 工作区

<!-- 每次任务生成唯一 slug（如 task-20260615-fix-auth），防止多次运行 state 冲突 -->
- 任务标识：`[task-slug]`（如 `fix-login-20260615`）
- 产出目录：`state/[task-slug]/`
- 源码目录：[如：`src/`]
- 测试目录：[如：`tests/`]
