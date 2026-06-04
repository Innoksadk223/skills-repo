# 调度器模板

> 复制此模板到你的 SKILL.md，替换 `{...}` 占位符。

```markdown
---
name: {skill-name}
description: {一句话 + 触发条件 + 适用场景}
---

# {技能名}

## 调度流程

1. **M1** — {动作} → `state/M1_{output}.{ext}`
2. **M2** — {动作} → `state/M2_{output}.{ext}`
3. **M3** — {动作} → `state/M3_{output}.{ext}`

## 决策树

- 如果 M1 返回 `{condition}` → {分支动作}
- 如果 {condition} → {分支动作}

## 模块清单

| 模块 | 文件 | 输入 | 输出 |
|------|------|------|------|
| M1 | [{M1_filename}.md] | {来源} | state/{M1_output} |
| M2 | [{M2_filename}.md] | M1 | state/{M2_output} |
| M3 | [{M3_filename}.md] | M2 | state/{M3_output} |
```

### 约束

- 模块最多 7 个（超过说明该拆成两个 skill）
- SKILL.md 不超过 100 行
- 决策树只写关键分支，不枚举所有边界
