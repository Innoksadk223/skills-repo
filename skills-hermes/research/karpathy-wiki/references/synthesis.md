# Synthesis

Create and maintain cross-topic overview pages that synthesize the wiki's current state of knowledge on a domain or sub-domain.

Unlike concept pages ("X 是什么"), synthesis pages answer "关于这个领域，目前知道什么、争议在哪、趋势如何。"

## Triggers

- **User request:** user asks to summarize a domain, create an overview, or synthesize findings.
- **Lint suggestion:** `references/lint.md` flags domains where concept pages are dense but no synthesis exists.

## Procedure

① **Identify scope** — what domain or sub-domain to synthesize. Be specific: not "AI", but "LLM 对齐研究（2023-2024）" or "中国社会分层研究".

② **Gather relevant pages** — search index.md and `search_files` for all concepts, entities, and comparisons in scope.

③ **Read key pages** — focus on high-confidence pages and pages with the most inbound links (hubs).

④ **Write synthesis page** in `synthesis/`:

```markdown
---
title: 综述标题
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: synthesis
tags: [from SCHEMA.md taxonomy]
sources: [all wiki pages synthesized, not raw/]
confidence: medium
---

# 综述标题

## 当前认知
[What the wiki collectively knows about this domain — synthesize, don't just list]

## 主要争议
[Contradictory claims, contested pages, open debates surfaced by lint]

## 知识缺口
[Concepts mentioned but stub-only, areas with low confidence, missing sources]

## 关键页面
- [[概念A]] — 核心框架
- [[概念B]] — 替代视角
- [[辨析：A vs B]] — 关键区分
```

⑤ **Update navigation** — add to `index.md` under synthesis section, append to `log.md`.

⑥ **Cross-link** — add wikilinks from the synthesis page to mentioned pages, and from key hub pages back to the synthesis.

## When to Update

Revisit a synthesis page when:
- A new ingest touches 3+ pages in its scope
- Lint surfaces new contradictions in the domain
- User asks for an update
