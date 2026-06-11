# Synthesis

Create and maintain lightweight `synthesis/` entry pages that help humans enter a topic, route through the wiki, and see the current state at a glance.

A synthesis page is **not** the main knowledge structure. If a page contains thesis logic, support chains, objections, limitations, or evidence tables, extract those graph-worthy propositions into `claims/` using `references/claims.md`.

## Triggers

- **User request:** summarize a domain, create an overview, create a writing route map, or synthesize findings.
- **Lint suggestion:** dense concept/comparison clusters need a human entry page.
- **Argument material:** thesis map, theoretical framework, core controversy, or chapter route. These require claims extraction.

## Synthesis Types

### 1. Ordinary overview synthesis

Use for: “这个领域目前知道什么、争议在哪、缺口在哪”。

This does not always require claims. Keep it short and link to concepts/entities/comparisons.

### 2. Argument-oriented synthesis

Use for: 论文论证地图、理论框架、核心争议、章节论证路线。

This **must** create or update related `claims/` pages. The synthesis page remains a route map; the argument structure lives in `claims/`.

### 3. Literature-review matrix

Use for: 社科文献综述、开题报告、毕业论文阅读整理。

The matrix maps sources to research questions, methods, contributions, limits, claims, debates, and writing positions. It lives in `synthesis/` because it is a route map. Reusable propositions still belong in `claims/`; durable controversies belong in `debates/` or debate-style `comparisons/`.

## Procedure

1. **Identify scope** — be specific: not “AI”, but “LLM 对齐研究（2023-2024）” or “孝为仁之本的跨学科论证”.
2. **Gather relevant pages** — search `index.md` and `search_files` for concepts, entities, comparisons, and existing claims.
3. **Read key pages** — focus on high-confidence pages and graph hubs.
4. **If argument-oriented, extract claims first** — use `references/claims.md`; move evidence into the relevant claim pages.
5. **Write a lightweight synthesis page** in `synthesis/`.
6. **Update navigation** — add the synthesis page to `index.md`; add only core claims to the Claims section.
7. **Cross-link** — link from synthesis to key claims/concepts/entities/comparisons; add backlinks only when the synthesis is a durable entry page.
8. **Append to `log.md`**.

## Lightweight Template

```markdown
---
title: 综述标题
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: synthesis
tags: [from SCHEMA.md taxonomy]
sources: [wiki pages synthesized, not raw/]
confidence: medium
---

# 综述标题

## 入口定位
这个页面帮助进入什么问题？不要写成长篇论证。

## 主 claim
- [[主论题]] — 一句话说明。

## 核心路径
1. [[核心 claim A]] — 作用。
2. [[核心 claim B]] — 作用。
3. [[核心 claim C]] — 作用。

## 关键页面
- [[概念A]] — 核心概念。
- [[人物A]] — 关键作者/来源。
- [[辨析A]] — 关键区分。

## 当前缺口
- 需要补哪些概念、证据或反方。
```

## What Not to Put in Synthesis

Do not keep these as durable synthesis content:

- full argument chains;
- detailed evidence banks or long evidence tables;
- all objections and responses;
- long concept explanations;
- raw source excerpts.

Move them to:

- `claims/` for propositions, evidence, objections, limitations;
- `concepts/` for concept explanations;
- `comparisons/` for distinctions;
- `entities/` for authors/texts/organizations.

## Evidence Bank Rule

Do not generate a standalone `论文证据银行.md` as a default product. Evidence belongs in the claim it supports:

```text
claims/孝的道德基础是良好照料.md → Ivanhoe / Cline evidence
claims/家是道德生成的原初场域.md → 孙向晨 / 张祥龙 evidence
```

If an old evidence bank exists, migrate evidence into claims first, verify no information is lost, then ask before deleting or archiving the old file.

## When to Update

Revisit a synthesis page when:

- a core claim changes;
- new ingest touches 3+ pages in its scope;
- lint surfaces new contradictions or dense clusters;
- the user asks for a new writing route or overview.

Keep the synthesis page as a route map. If it starts becoming the main content, extract claims and slim it down.
