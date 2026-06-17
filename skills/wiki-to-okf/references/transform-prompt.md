# LLM Body 压缩 Prompt 模板

此 prompt 发给 LLM，将 karpathy-wiki 页面正文压缩为 AI 可消费的 OKF body。

## 使用方式

将 `{{PAGE_CONTENT}}` 替换为 wiki 页面去掉 YAML frontmatter 后的 Markdown 正文。将 `{{PAGE_TYPE}}` 替换为页面类型（claim/concept/entity/comparison/synthesis/debate）。将 `{{EXISTING_LINKS}}` 替换为页面中已有的 Markdown 交叉链接列表。

## Prompt

```
你将收到一份人类可读的百科/论证页面。请将其压缩为 AI agent 可消费的简洁格式。

## 约束

1. 不要丢失任何论证关系（支持/反对/限定/依赖）。将每个关系写成一行：
   - 支持: [目标概念] — 一句理由
   - 反对: [目标概念] — 一句理由
   - 限定: 适用范围或条件
   - 依赖: 前置概念或来源

2. 保留所有原始引文锚点（如 `wiki/raw/xxx.md` 路径）。不要搬运引文原文——只保留路径引用。

3. 开头用 1-3 句写出核心论点/定义。这段是 agent 判断相关性的第一关。

4. 去掉叙事性段落、修辞、过渡句、重复。

5. 用结构化 key-value 格式标注元信息：
   - 立场: <一句话>
   - 论证类型: <概念分析|实证研究|文本解读|比较分析|综述>
   - 不确定性: <无|低|中|高> — 简短说明原因

6. 从正文中提取的交叉引用（非 Markdown 链接格式，如"这反驳了某某"），在末尾返回：
   ADDITIONAL_LINKS:
   - <okf/相对路径>
   - <okf/相对路径>
   
   如果无法确定目标页面属于哪个类型目录（claims/concepts/entities/comparisons/synthesis/debates），标记为 UNRESOLVED:
   UNRESOLVED:
   - 概念名: <无法确定路径的原因>

7. 不要添加页面中没有的信息。不要"补充背景"或"展开讨论"。

8. 输出纯 Markdown，不要 JSON 包裹。不要加解释性或总结性前缀。

## 页面类型

{{PAGE_TYPE}}

## 已知交叉链接

{{EXISTING_LINKS}}

## 页面正文

{{PAGE_CONTENT}}
```

## 参数说明

| 参数 | 来源 |
|------|------|
| `{{PAGE_CONTENT}}` | wiki 页面去掉 YAML frontmatter 后的完整正文 |
| `{{PAGE_TYPE}}` | 页面类型（从目录名推断：claims→claim, concepts→concept, …） |
| `{{EXISTING_LINKS}}` | 页面中已有的 Markdown 链接，格式化为列表（每行一个路径） |

## 输出期望

LLM 应返回纯 Markdown 正文，适合写入 OKF 概念文件的 YAML frontmatter 之后。典型输出：

```markdown
孝的本质不在于生育事实，而在于长期的照料与情感联结。此观点构成对生物决定论的直接反驳，但跨文化适用性存在争议。

- 立场: 支持「孝源于情感联结」
- 论证类型: 概念分析
- 支持: [亲亲](concepts/亲亲.md) — 情感联结是亲亲的基础
- 反对: 生物决定论 — 「生育事实不足以构成孝」
- 限定: 跨文化适用性待验证
- 原文锚点: `wiki/raw/孝经/开宗明义章.md`
- 不确定性: 中等 — 东亚语境验证充分，其他文化证据不足

ADDITIONAL_LINKS:
- concepts/情感联结.md
```
