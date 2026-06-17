# OKF Index 与 Log 模板

## `okf/index.md` 模板

顶层导航枢纽。仿 OKF 的 `index.md` 语义：progressive disclosure——agent 先读此页，根据需要深入子目录。

```markdown
---
type: index
title: <知识库名称> — OKF Bundle
description: <知识库的一句话描述>
timestamp: <生成时间，ISO 8601>
source_wiki: <指向 wiki/index.md 的路径>
---

# <知识库名称>

<从 wiki/index.md 或 SCHEMA.md 提取的简介，1-2 句>

## 类型概览

| 类型 | 页面数 | 入口 |
|------|--------|------|
| claims | N | [claims/](claims/index.md) |
| concepts | N | [concepts/](concepts/index.md) |
| entities | N | [entities/](entities/index.md) |
| comparisons | N | [comparisons/](comparisons/index.md) |
| synthesis | N | [synthesis/](synthesis/index.md) |
| debates | N | [debates/](debates/index.md) |

## 最近变更

<从 okf/log.md 提取最近 5 条>

## 使用说明

此 bundle 遵循 Open Knowledge Format v0.1。每个概念文件含 YAML frontmatter（type, title, description, tags, relates_to）和 AI 优化的 Markdown body。

作为 AI agent：从本页开始导航，按 `relates_to` 追踪概念图谱，使用 body 中的结构化 key-value 块做决策，用 `source` 字段回溯人读原文。
```

## 类型子目录 `index.md` 模板

每个类型目录（如 `okf/claims/index.md`）列出该类型的全部页面：

```markdown
---
type: index
title: <类型名（中文）>
description: <该类型的简要说明>
source_wiki: <指向 wiki/<type>/index.md 的路径，可选>
---

# <类型名>

<该类型在 OKF 中的语义说明>

## 页面列表

- [页面标题 1](页面1.md) — 一句话描述
- [页面标题 2](页面2.md) — 一句话描述
- ...
```

描述从对应页面的 OKF YAML `description` 字段提取。

## `okf/log.md` 模板

```markdown
---
type: log
title: OKF Bundle 变更日志
---

# OKF Bundle 变更日志

## <ISO 日期> — 初始生成

- 源 wiki: <wiki/ 路径>
- 源 wiki 状态: <git commit hash 或 wiki/log.md 起始行>
- 转换统计:
  - claims: N
  - concepts: N
  - entities: N
  - comparisons: N
  - synthesis: N
  - debates: N
- 转换引擎: wiki-to-okf v0.1
- 模型: <使用的 LLM 模型名>

## <ISO 日期> — 增量更新

- 变更页面: <页面路径列表>
- 变更原因: <来自 wiki/log.md 的对应条目>
```
