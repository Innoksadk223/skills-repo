---
name: karpathy-wiki
description: "Build and maintain a persistent, compounding knowledge base as interlinked markdown files (Karpathy's wiki pattern). Wiki content is written in Chinese with 中英对照 for English terms. Use when the user asks to create/start a wiki, ingest/add/process a source into their wiki, query their wiki, lint/audit/health-check their wiki, or references their wiki/knowledge base/notes in a research context."
version: 2.5.0
author: Hermes Agent
source: hermes-builtin
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [wiki, knowledge-base, research, notes, markdown, rag-alternative]
    category: research
    related_skills: [obsidian, arxiv]
---

# Karpathy's Wiki

Build and maintain a persistent, compounding knowledge base as interlinked markdown files.
Based on [Andrej Karpathy's wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Unlike traditional RAG (which rediscovers knowledge from scratch per query), the wiki
compiles knowledge once and keeps it current. Cross-references are already there.
Contradictions have already been flagged. Synthesis reflects everything ingested.

**Division of labor:** The human curates sources and directs analysis. The agent
summarizes, cross-references, files, and maintains consistency.

## Wiki Location

**Location:** Set via `WIKI_PATH` environment variable (e.g. in `~/.hermes/.env`).

If unset, defaults to `~/wiki`.

```bash
WIKI="${WIKI_PATH:-$HOME/wiki}"
```

The wiki is just a directory of markdown files — open it in Obsidian, VS Code, or
any editor. No database, no special tooling required.

## Architecture: Three Layers

```
wiki/
├── SCHEMA.md           # Conventions, structure rules, domain config
├── index.md            # Sectioned content catalog with one-line summaries
├── log.md              # Chronological action log (append-only, rotated yearly)
├── raw/                # Layer 1: Immutable source material
│   ├── articles/       # Web articles, clippings
│   ├── papers/         # PDFs, arxiv papers
│   ├── transcripts/    # Meeting notes, interviews
│   └── assets/         # Images, diagrams referenced by sources
├── entities/           # Layer 2: Entity pages (people, orgs, products, models)
├── concepts/           # Layer 2: Concept/topic pages
├── comparisons/        # Layer 2: 辨析页（comparison/distinction）
├── queries/            # Layer 2: Filed query results worth keeping
├── synthesis/          # Layer 2: Cross-topic synthesis pages
├── qa-log.md           # Q&A log (append-only, queries + answers)
```

**Layer 1 — Raw Sources:** Immutable. The agent reads but never modifies these.
**Layer 2 — The Wiki:** Agent-owned markdown files. Created, updated, and
cross-referenced by the agent.
**Layer 3 — The Schema:** `SCHEMA.md` defines structure, conventions, and tag taxonomy.

## Wiki Content Language

**The wiki content (page titles, body text, tags) is written in Chinese.** English technical terms use 中英对照（Chinese-first, English in parentheses）format.

- **Page titles:** Chinese. If the concept has a standard English name, use `中文名称（English Name）`.
  e.g. `注意力机制（Attention Mechanism）`、`Transformer 架构`、`RLHF（人类反馈强化学习）`
- **Body text:** Chinese throughout. English terms use 中英对照 on first occurrence.
- **Entity names:** Chinese translation (if widely adopted), English original on first mention.
- **Tags:** Chinese tags, with English in parentheses where the English term is standard.
- **File names:** Chinese filenames are supported (Obsidian handles Unicode). Keep naming consistent.
- **Wikilinks:** Use Chinese page names for link targets. `[[注意力机制]]`、`[[GPT 系列]]`
- **index.md entries:** One-line summaries in Chinese.
- **log.md entries:** Action keyword in English, subject in Chinese.

## Resuming an Existing Wiki (CRITICAL — do this every session)

When the user has an existing wiki, **always orient yourself before doing anything**:

① **Read `SCHEMA.md`** — understand the domain, conventions, and tag taxonomy.
② **Read `index.md`** — learn what pages exist and their summaries.
③ **Scan recent `log.md`** — read the last 20-30 entries to understand recent activity.

```bash
WIKI="${WIKI_PATH:-$HOME/wiki}"
read_file "$WIKI/SCHEMA.md"
read_file "$WIKI/index.md"
read_file "$WIKI/log.md" offset=<last 30 lines>
```

Only after orientation should you ingest, query, or lint. For large wikis (100+ pages),
also run a quick `search_files` for the topic at hand before creating anything new.

## Initializing a New Wiki

When the user asks to create or start a wiki:

1. Determine the wiki path (from `$WIKI_PATH` env var, or ask the user; default `~/wiki`)
2. Create the directory structure above
3. Ask the user what domain the wiki covers — be specific
4. Write `SCHEMA.md` customized to the domain: read [`references/templates/SCHEMA-template.md`](references/templates/SCHEMA-template.md), customize the domain and tag taxonomy, then write to `$WIKI/SCHEMA.md`
5. Write initial `index.md`: read [`references/templates/index-template.md`](references/templates/index-template.md). Scaling rule: when any index section exceeds 50 entries, split by pinyin first letter. When index exceeds 200 entries total, create `_meta/主题地图.md`.
6. Write initial `log.md`: read [`references/templates/log-template.md`](references/templates/log-template.md)
7. Create empty `qa-log.md` — append-only Q&A log. Format: `## [YYYY-MM-DD] Q: 问题` → `A: 摘要（来源：[[页面]]）`
8. Create `synthesis/` directory
9. Confirm the wiki is ready and suggest first sources to ingest

## Core Operations

| 用户意图 | 加载 | 说明 |
|---------|------|------|
| 摄入来源 (ingest) | [`references/ingest.md`](references/ingest.md) | 单个来源 → wiki 页面 + 交叉引用 + 导航更新 |
| 查询知识 (query) | [`references/query.md`](references/query.md) | 检索 → 综合回答 → 有价值的存档 |
| 健康检查 (lint) | [`references/lint.md`](references/lint.md) | 运行 `scripts/lint.py` → 解析 JSON → 汇报 + 研究建议 |
| 批量摄入 (bulk) | [`references/bulk-ingest.md`](references/bulk-ingest.md) | 5+ 来源的并行/顺序策略 |
| 综述 (synthesis) | [`references/synthesis.md`](references/synthesis.md) | 跨主题综述：当前认知 + 争议 + 知识缺口 |
| Obsidian 集成 | [`references/obsidian-setup.md`](references/obsidian-setup.md) | 图谱颜色分组、Dataview 等配置 |

## Searching

```bash
search_files "transformer" path="$WIKI" file_glob="*.md"
search_files "*.md" target="files" path="$WIKI"
search_files "tags:.*对齐" path="$WIKI" file_glob="*.md"
read_file "$WIKI/log.md" offset=<last 20 lines>
```

## Archiving

When content is fully superseded or the domain scope changes:

1. Create `_archive/` directory if it doesn't exist
2. Move the page to `_archive/` with its original path (e.g., `_archive/entities/old-page.md`)
3. Remove from `index.md`
4. Update any pages that linked to it — replace wikilink with plain text + "（已归档）"
5. Log the archive action

## Pitfalls

- **Never modify files in `raw/`** — sources are immutable. Corrections go in wiki pages.
- **Always orient first** — read SCHEMA + index + recent log before any operation in a new session.
- **Always update index.md and log.md** — skipping this makes the wiki degrade.
- **Don't create pages for things outside the domain** — follow the Page Thresholds in SCHEMA.md.
- **Don't create pages without cross-references** — every page must link to at least 2 other pages.
- **Frontmatter is required** — it enables search, filtering, and staleness detection.
- **Tags must come from the taxonomy** — add new tags to SCHEMA.md first, then use them.
- **Keep pages scannable** — a wiki page should be readable in 30 seconds. Split pages over 200 lines.
- **Ask before mass-updating** — if an ingest would touch 10+ existing pages, confirm scope with the user first.
- **Rotate the log** — when log.md exceeds 500 entries, rename it `log-YYYY.md` and start fresh.
- **Handle contradictions explicitly** — don't silently overwrite. Note both claims with dates, mark in frontmatter, flag for user review.
