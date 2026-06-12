---
name: karpathy-wiki
description: "Build and maintain a persistent, graph-readable wiki as interlinked markdown files. Use when the user asks to create/start a wiki, ingest/add/process sources, query a wiki, lint/audit/health-check a wiki, create synthesis/claims, or work with a research knowledge base/Obsidian graph."
---

# Karpathy's Wiki

Build and maintain a persistent, compounding knowledge base as interlinked markdown files.
Based on [Andrej Karpathy's wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Core principle: **the wiki must be graph-readable, not just human-readable.** Human-friendly summaries are useful, but durable knowledge belongs in linked pages whose relationships are visible in Obsidian.

**Division of labor:** The human curates sources and directs analysis. The agent captures sources, extracts concepts/entities/comparisons/claims, cross-links pages, maintains navigation, and keeps the graph healthy.

When the user wants to enrich an existing area of the wiki (for example, "补充儿童教育"), treat it as **user-directed expansion**: orient to the current graph, identify the gap, find raw evidence, use any available `reading_dossiers/` deep-reading handoff, then compile formal wiki nodes. Do not start by writing pages from general memory.

## Wiki Location

Set via `WIKI_PATH` environment variable (e.g. in `~/.hermes/.env`). If unset, default to `~/wiki`.

```bash
WIKI="${WIKI_PATH:-$HOME/wiki}"
```

The wiki is just a directory of markdown files — open it in Obsidian, VS Code, or any editor. No database required.

## Architecture: Graph-Readable Layers

```
wiki/
├── SCHEMA.md           # Conventions, structure rules, domain config
├── index.md            # Core catalog; lists all standard pages + only core claims
├── log.md              # Chronological action log (append-only, rotated yearly)
├── raw/                # Layer 1: immutable source material; excluded from graph
│   ├── articles/
│   ├── papers/
│   ├── transcripts/
│   └── assets/
├── entities/           # Layer 2: people, authors, orgs, products, texts
├── concepts/           # Layer 2: concepts/topics
├── comparisons/        # Layer 2: 辨析页（comparison/distinction）
├── debates/            # Layer 2: durable social-science controversies (optional)
├── claims/             # Layer 2: graph-visible argument nodes
├── queries/            # Layer 2: filed query results worth keeping
├── synthesis/          # Layer 2: lightweight human entry pages only
├── qa-log.md           # Q&A log (append-only)
```

- **raw/**: Immutable. Read but do not modify except during source capture/re-ingest. Do not make raw files graph nodes.
- **concepts/entities/comparisons/**: Knowledge nodes.
- **debates/**: Optional controversy hubs for mature social-science wikis; use `comparisons/` for simple distinctions.
- **claims/**: Argument nodes — propositions that can be supported, opposed, limited, or depended on.
- **synthesis/**: Lightweight entry pages / route maps. Do not store the main argument structure or detailed evidence bank here.
- **SCHEMA.md**: Domain rules, frontmatter, tag taxonomy, thresholds.

## Wiki Content Language

**Wiki content is written in Chinese.** English technical terms use 中英对照（Chinese-first, English in parentheses）format.

- **Page titles:** Chinese; standard English terms use `中文名称（English Name）` when helpful.
- **Body text:** Chinese throughout; first occurrence can include English.
- **File names:** Chinese filenames are fine. For `claims/`, use the full proposition sentence as the filename.
- **Wikilinks:** Use Chinese page names: `[[注意力机制]]`, `[[孝的道德基础是良好照料]]`.
- **index.md/log.md:** Chinese summaries; log action keyword can be English.

## Resuming an Existing Wiki (CRITICAL)

When the user has an existing wiki, always orient before editing:

1. Read `SCHEMA.md` — domain, conventions, taxonomy.
2. Read `index.md` — existing pages and core claims.
3. Scan recent `log.md` — last 20-30 entries.
4. For large wikis (100+ pages), `search_files` for the topic before creating anything new.

```bash
WIKI="${WIKI_PATH:-$HOME/wiki}"
read_file "$WIKI/SCHEMA.md"
read_file "$WIKI/index.md"
read_file "$WIKI/log.md" offset=<last 30 lines>
```

## Initializing a New Wiki

When creating a wiki:

1. Determine wiki path from `$WIKI_PATH` or ask; default `~/wiki`.
2. Create the directory structure above, including `claims/`, optional `debates/`, and `synthesis/`.
3. Ask what domain the wiki covers.
4. Write `SCHEMA.md` from `references/templates/SCHEMA-template.md`, customized to the domain.
5. Write `index.md` from `references/templates/index-template.md`. When any section exceeds 50 entries, split by pinyin first letter; when index exceeds 200 entries total, create `_meta/主题地图.md`.
6. Write `log.md` from `references/templates/log-template.md`.
7. Create empty `qa-log.md`: `## [YYYY-MM-DD] Q: 问题` → `A: 摘要（来源：[[页面]]）`.
8. Confirm the wiki is ready and suggest first sources to ingest.

## Core Operations

| 用户意图 | 加载 | 说明 |
|---------|------|------|
| 摄入来源 (ingest) | `references/ingest.md` | 单个来源 → wiki 页面 + 交叉引用 + 导航更新 |
| 查询知识 (query) | `references/query.md` | 检索 → 综合回答 → 有价值的存档 |
| 论证节点 (claims) | `references/claims.md` | 将论文/理论论证拆成图谱可见的小型论证卡片 |
| 社科增强 (social science) | `references/social-science.md` | 社科论文、理论框架、概念界定、方法边界和证据类型 |
| 争议谱系 (debates) | `references/debates.md` | 多立场理论争议、反方回应、导师追问和研究缺口 |
| 文献综述矩阵 | `references/literature-review.md` | 将一批文献整理成 thesis-ready matrix |
| 健康检查 (lint) | `references/lint.md` | 运行 `scripts/lint.py` → 解析 JSON → 汇报 + 研究建议 |
| 批量摄入 (bulk) | `references/bulk-ingest.md` | 5+ 来源的并行/顺序策略 |
| 综述/入口 (synthesis) | `references/synthesis.md` | 轻量入口页；论证型 synthesis 必须抽取 claims |
| 用户意图补库 (user-directed expansion) | `references/query.md` + `references/ingest.md` + `references/claims.md` | 用户指出想补某一主题时，先找 raw 来源与 deep-reading dossier，再正式入图谱 |
| Obsidian 集成 | `references/obsidian-setup.md` | 图谱路径分组、Dataview、raw 排除 |

## Bundled Resources

Load only the files needed for the current operation:

| Resource | When to read |
|---|---|
| `references/social-science.md` | Social-science thesis, literature review, theory framework, methods, or evidence boundaries |
| `references/debates.md` + `references/templates/debate-template.md` | Durable controversies, competing positions, objections, or advisor-defense questions |
| `references/literature-review.md` + `references/templates/literature-review-template.md` | Turning a source batch into a thesis-ready literature review matrix |
| `references/templates/SCHEMA-template.md` | Initializing or refreshing wiki conventions |
| `references/templates/claim-template.md` | Creating or upgrading claim pages |
| `references/templates/index-template.md`, `references/templates/log-template.md` | Initializing navigation and logs |
| `scripts/lint.py`, `scripts/lint_self_test.py` | Health checks or script changes |

## Searching

```bash
search_files "孝" path="$WIKI" file_glob="*.md"
search_files "*.md" target="files" path="$WIKI"
search_files "type: claim" path="$WIKI/claims" file_glob="*.md"
read_file "$WIKI/log.md" offset=<last 20 lines>
```

## User-Directed Expansion

Use this when the user says they want to add, deepen, rebalance, or supplement an area already visible in the wiki, such as "我想补充儿童教育".

1. Orient first: read `SCHEMA.md`, `index.md`, recent `log.md`, and search existing wiki pages for the user's topic.
2. Identify the graph gap in plain language: missing concept, thin claim, missing objection, weak comparison, missing source, or shallow synthesis.
3. Find raw evidence before writing: use available RAG/source-discovery workflow from `social-science-km` or `SiliconFlow-rag`; do not rely on wiki pages alone.
4. If no usable raw source is found, stop and report the source-discovery gap; do not create placeholder claims from general knowledge.
5. For long, theory-heavy, or thesis-critical raw sources, require a `deep-reading-to-wiki` dossier before formal wiki edits.
6. When a dossier exists, verify its `source_raw`, `user_intent` when present, high-value context capsules, and raw anchors before compiling it.
7. Compile only after evidence is located: create/update `concepts/`, `claims/`, `comparisons/`, `entities/`, and lightweight `synthesis/` according to existing rules.
8. Preserve the user's stated inclination as a research direction, not as evidence. Raw sources support claims; the user's interest only chooses what to investigate.
9. Update `index.md` and `log.md`; if the expansion touches 10+ existing pages, confirm scope before mass-editing.

## Argument Structure Rule

When content contains thesis structure, theoretical framework, objections, limitations, or evidence logic, do **not** leave it as a long `synthesis/` page. Extract graph-worthy propositions into `claims/`.

Use `claims/` for:
- main theses;
- support propositions;
- core objections;
- limitation/boundary claims;
- bridge claims connecting fields or theories.

Use `synthesis/` only for lightweight entry pages: route maps, reading order, current state, key links, and gaps. Do not generate a standalone long evidence bank; evidence belongs inside the claim it supports.

For social-science projects, load `references/social-science.md` before building claims or synthesis. Use debate pages for durable controversies and literature-review matrices for source-to-writing route maps.

## Archiving

When content is fully superseded or domain scope changes:

1. Create `_archive/` if needed.
2. Move the page to `_archive/` with original path preserved.
3. Remove from `index.md`.
4. Update pages that linked to it — replace wikilink with plain text + `（已归档）`.
5. Log the archive action.

## Common Pitfalls

- **Never modify files in `raw/`** except source capture/re-ingest; corrections go in wiki pages.
- **Always orient first** — read SCHEMA + index + recent log before working.
- **Don't turn user inclination into claims** — use it to choose a search direction, then locate raw evidence.
- **Don't compile a dossier blindly** — check that its raw anchors still support the proposed wiki nodes.
- **Always update index.md and log.md** — skipping this makes the wiki degrade.
- **Don't create pages outside the domain** — follow SCHEMA thresholds.
- **Don't create graph-dead pages** — every page should link to at least 2 other pages; create stubs for dead wikilinks.
- **Don't bury arguments in synthesis** — if it is a proposition with support/opposition/limits, make a claim page.
- **Don't keep evidence banks as durable products** — evidence belongs under the relevant claim; raw locations are plain-text paths, not wikilinks.
- **Don't flatten social-science disputes** — preserve competing definitions, methods, positions, and evidence limits.
- **Frontmatter is required** — it enables filtering, linting, and staleness detection.
- **Tags must come from the taxonomy** — add new tags to SCHEMA.md first.
- **Keep pages scannable** — split pages over ~200 lines.
- **Ask before mass-updating** — if an operation would touch 10+ existing pages, confirm scope.
- **Handle contradictions explicitly** — do not silently overwrite; mark contested claims and flag for review.

## Verification Checklist

- [ ] `SCHEMA.md`, `index.md`, and recent `log.md` were read before edits.
- [ ] User-directed expansion found usable raw evidence before writing formal pages.
- [ ] If a `reading_dossiers/` handoff was used, its raw anchors and context risks were checked.
- [ ] New/updated pages have required frontmatter and Chinese wikilinks.
- [ ] `claims/` exists when the wiki contains argument-oriented material.
- [ ] Core claims are listed in `index.md`; non-core claims are discoverable through links.
- [ ] Social-science projects used `references/social-science.md` for concepts, evidence types, debates, and method boundaries.
- [ ] Claim pages include `## 命题` and `## 关系` so Obsidian graph edges are visible.
- [ ] No `raw/` file is wikilinked as a graph node; raw evidence locations are plain-text paths.
- [ ] `index.md` and `log.md` were updated.
- [ ] `scripts/lint.py <wiki_path>` was run when doing health checks or structural migrations.
