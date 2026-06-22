# OKF 字段映射规则

将论证图谱 wiki 页面映射为 OKF 概念文件。所有字段除 `type` 外均为可选，但建议至少包含 `title` 和 `description`。

## OKF YAML Frontmatter 规范

```yaml
---
type: <claim|concept|entity|comparison|synthesis|debate|index|log>
title: <页面标题>
description: <一句话摘要，≤160 chars>
source: <相对于 wiki/ 的源页面路径，概念页使用；index 页使用 source_wiki 替代>
source_wiki: <指向 wiki/index.md 的路径，仅 index 类型使用>
tags: [<标签列表>]
timestamp: <ISO 8601，源页面 mtime 或 log.md 中的变更时间>
relates_to: [<okf/ 下其他页面的相对路径>]
---
```

## 字段映射规则

### `type`（必填）

| Wiki 目录 | OKF type |
|-----------|----------|
| `wiki/claims/` | `claim` |
| `wiki/concepts/` | `concept` |
| `wiki/entities/` | `entity` |
| `wiki/comparisons/` | `comparison` |
| `wiki/synthesis/` | `synthesis` |
| `wiki/debates/` | `debate` |

### `title`（建议必填）

优先级：
1. Wiki 页面 YAML frontmatter 的 `title` 字段
2. Wiki 页面第一个 `# heading` 文本
3. 文件名（去掉 `.md`，转为可读形式）

### `description`（建议必填）

提取 wiki 页面首个 `# heading` 之后第一个非空段落。截断到 160 字符，末尾加 `…`。不跨行合并；如果首段是列表或引用，跳过取下一段纯文本。

### `tags`

直接映射 wiki 页面 YAML frontmatter 的 `tags` 字段。若无，尝试从 wiki 页面 `relates_to` 或交叉链接的页面标题中提取关键词（每个 2-4 字）。

### `source`

相对于 `<知识库>/wiki/` 的路径。示例：`claims/孝的本质.md`。

### `timestamp`

从 wiki 页面的文件 mtime 提取。根据操作系统选择对应命令：

- **macOS**：`stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%SZ" <file>`
- **Linux**：`stat -c %y <file>` 或 `date -r <file> -Iseconds`
- **通用（Git）**：`git log -1 --format=%aI -- <file>`（若 wiki 使用 git，优先此方法）

### `relates_to`

提取 wiki 页面中的交叉链接，转换为 `okf/` 下的相对路径：

- Wiki 内链 `[文本](../claims/xxx.md)` → `okf/claims/xxx.md`
- Wiki 内链 `[文本](../concepts/yyy.md)` → `okf/concepts/yyy.md`
- 同类型内链 `[文本](zzz.md)` → 保持同目录，如 `okf/claims/zzz.md`
- 外部链接不纳入 `relates_to`

**LLM 辅助提取**：对于嵌入在正文段落中的交叉引用（非 Markdown 链接格式，如 "这反驳了某某概念"），由 LLM 在 body 压缩阶段识别并补充到 `relates_to`。agent 应在 LLM prompt 中要求返回补充的 relates_to 列表。

## OKF Body 内容规范

OKF body 是 AI 可消费的 Markdown（不要纯 JSON，保留 Markdown 可读性）。最小要求：

1. **核心论点/定义** 开头（1-3 句，适合 agent 快速判断相关性）
2. **结构化 key-value 块** 用于机器可解析的关键信息：
   ```markdown
   - 立场: 支持「孝源于情感联结」
   - 论证类型: 概念分析
   - 关键引文: `wiki/raw/孝经/开宗明义章.md`
   - 不确定性: 中等（跨文化适用性待验证）
   ```
3. **保留的论证关系**（support/oppose/limit/depend）以结构化标签标注，不以叙事方式展开
4. **保留的原始证据锚点**（`wiki/raw/` 路径），不搬运原文

## 交叉链接解析

`relates_to` 中每个条目是相对 `okf/` 的路径。验证时检查目标文件是否存在。

### 示例：输入输出对照

**输入**（`wiki/claims/孝的本质.md`）：

```markdown
---
title: 孝的本质
tags: [孝, 情感, 伦理]
---

# 孝的本质

孝的本质不在于生育事实，而在于长期的照料与情感联结。
这与「亲亲」概念密切相关，详见 [亲亲](../concepts/亲亲.md)。
此观点反对生物决定论，但受限于跨文化适用范围。
> 原文见 [孝经注疏](../../wiki/raw/孝经/开宗明义章.md)
```

**输出**（`okf/claims/孝的本质.md`）：

```yaml
---
type: claim
title: 孝的本质
description: 孝的本质不在于生育事实，而在于长期的照料与情感联结。
source: claims/孝的本质.md
tags: [孝, 情感, 伦理]
timestamp: 2026-06-15T08:30:00Z
relates_to: [concepts/亲亲.md]
---

# 孝的本质

孝的本质不在于生育事实，而在于长期的照料与情感联结。

- 立场: 支持「孝源于情感联结」
- 论证类型: 概念分析
- 支持: [亲亲](concepts/亲亲.md) — 情感联结是亲亲的基础
- 反对: 生物决定论 — 「生育事实不足以构成孝」
- 限定: 跨文化适用性待验证
- 原文锚点: `wiki/raw/孝经/开宗明义章.md`
- 不确定性: 中等
```
