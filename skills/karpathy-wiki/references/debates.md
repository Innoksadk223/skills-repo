# Debates

Create debate pages for durable controversies, not for ordinary concept summaries.

A debate page maps a research disagreement: what is at stake, which positions exist, which authors or sources represent them, which claims support or oppose them, and what evidence would move the debate.

## Folder Choice

Default: create debate-style pages under `comparisons/` when the wiki is small.

Optional: mature social-science wikis may create `debates/` for controversies that become central hubs. If `debates/` is used, add it to `index.md` and keep page frontmatter `type: debate`.

Do not create both a `comparisons/` page and a `debates/` page for the same controversy unless the comparison is a narrow term distinction and the debate page is a broader research dispute.

## When To Create A Debate Page

Create one when at least two of these are true:

- multiple authors or schools disagree on the same research question;
- the disagreement affects a thesis chapter, research design, or interpretation of evidence;
- the controversy has both support and counterevidence;
- several claims point to the same unresolved objection;
- the user asks for 争议、立场、谱系、反方、回应、导师可能追问.

## Frontmatter

```yaml
---
title: 争议标题
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: debate
tags: [from SCHEMA.md taxonomy]
sources: [wiki pages or raw source paths]
confidence: medium
status: working
positions: [立场A, 立场B]
related_claims: []
related_concepts: []
related_entities: []
---
```

## Template

Use `references/templates/debate-template.md`.

Minimum sections:

- `## 争议问题`
- `## 主要立场`
- `## 代表作者与来源`
- `## 关联 claims`
- `## 证据与反证`
- `## 方法边界`
- `## 写作用途`
- `## 待补缺口`

## Evidence Rule

Debate pages summarize evidence positions. They should not become evidence banks. When a piece of evidence supports a durable proposition, move it into the relevant claim's `## 证据矩阵` or `## 关键证据`.

## Relationship Rule

A debate page should link to:

- the core claim it threatens or supports;
- at least two positions, authors, concepts, or comparison pages;
- any limitation claim that prevents overreach.

## Pitfalls

- Do not turn every two-sided issue into a debate page. Use `comparisons/` for simple distinctions.
- Do not flatten the debate into "A is right, B is wrong" unless sources clearly support that judgment.
- Do not hide unresolved questions. A good debate page makes missing evidence visible.
