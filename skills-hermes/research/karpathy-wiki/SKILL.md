---
name: karpathy-wiki
description: "Build and maintain a persistent, compounding knowledge base as interlinked markdown files (Karpathy's wiki pattern). Wiki content is written in Chinese with 中英对照 for English terms. Use when the user asks to create/start a wiki, ingest/add/process a source into their wiki, query their wiki, lint/audit/health-check their wiki, or references their wiki/knowledge base/notes in a research context."
version: 2.3.0
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
└── queries/            # Layer 2: Filed query results worth keeping
```

**Layer 1 — Raw Sources:** Immutable. The agent reads but never modifies these.
**Layer 2 — The Wiki:** Agent-owned markdown files. Created, updated, and
cross-referenced by the agent.
**Layer 3 — The Schema:** `SCHEMA.md` defines structure, conventions, and tag taxonomy.

## Wiki Content Language

**The wiki content (page titles, body text, tags) is written in Chinese.** English technical terms use 中英对照（Chinese-first, English in parentheses）format.

- **Page titles:** Chinese. If the concept has a standard English name, use `中文名称（English Name）`.
  e.g. `注意力机制（Attention Mechanism）`、`Transformer 架构`、`RLHF（人类反馈强化学习）`
- **Body text:** Chinese throughout. English terms use 中英对照 on first occurrence:
  `反向传播（Backpropagation）`，then use either Chinese or the English abbreviation.
- **Entity names:** Chinese translation (if widely adopted), English original on first mention.
  e.g. `安德烈·卡帕西（Andrej Karpathy）`、`OpenAI`（well-known English name kept as-is）、`深度求索（DeepSeek）`
- **Tags:** Chinese tags, with English in parentheses where the English term is standard.
  e.g. `tags: [模型, 训练, 微调（fine-tuning）, 对齐（alignment）]`
- **File names:** Chinese filenames are supported (Obsidian handles Unicode). Keep naming consistent.
  e.g. `Transformer-架构.md` or `transformer-architecture.md` — both fine, pick one style.
- **Wikilinks:** Use Chinese page names for link targets. `[[注意力机制]]`、`[[GPT 系列]]`
- **index.md entries:** One-line summaries in Chinese.
- **log.md entries:** Action keyword in English, subject in Chinese.
  e.g. `## [2026-06-04] ingest | Transformer 架构详解`

## Resuming an Existing Wiki (CRITICAL — do this every session)

When the user has an existing wiki, **always orient yourself before doing anything**:

① **Read `SCHEMA.md`** — understand the domain, conventions, and tag taxonomy.
② **Read `index.md`** — learn what pages exist and their summaries.
③ **Scan recent `log.md`** — read the last 20-30 entries to understand recent activity.

```bash
WIKI="${WIKI_PATH:-$HOME/wiki}"
# Orientation reads at session start
read_file "$WIKI/SCHEMA.md"
read_file "$WIKI/index.md"
read_file "$WIKI/log.md" offset=<last 30 lines>
```

Only after orientation should you ingest, query, or lint. This prevents:
- Creating duplicate pages for entities that already exist
- Missing cross-references to existing content
- Contradicting the schema's conventions
- Repeating work already logged

For large wikis (100+ pages), also run a quick `search_files` for the topic
at hand before creating anything new.

## Initializing a New Wiki

When the user asks to create or start a wiki:

1. Determine the wiki path (from `$WIKI_PATH` env var, or ask the user; default `~/wiki`)
2. Create the directory structure above
3. Ask the user what domain the wiki covers — be specific
4. Write `SCHEMA.md` customized to the domain (see template below)
5. Write initial `index.md` with sectioned header
6. Write initial `log.md` with creation entry
7. Confirm the wiki is ready and suggest first sources to ingest

### SCHEMA.md Template

Read [`references/templates/SCHEMA-template.md`](references/templates/SCHEMA-template.md), customize the domain and tag taxonomy for the user's domain, then write to `$WIKI/SCHEMA.md`.

### index.md Template

Read [`references/templates/index-template.md`](references/templates/index-template.md) and write to `$WIKI/index.md`.

**Scaling rule:** When any index section exceeds 50 entries, split into sub-sections by pinyin first letter or sub-domain. When the index exceeds 200 entries total, create `_meta/主题地图.md` for theme-based navigation.

### log.md Template

Read [`references/templates/log-template.md`](references/templates/log-template.md) and write to `$WIKI/log.md`.

## Core Operations

### 1. Ingest

When the user provides a source (URL, file, paste), integrate it into the wiki:

① **Capture the raw source:**
   - **URL** → use `web_extract` to get markdown, save to `raw/articles/`
   - **PDF (remote URL)** → use `web_extract` (handles PDFs), save to `raw/papers/`
   - **PDF (local file)** → use pymupdf (see `ocr-and-documents` skill) to extract
     text, save to `raw/papers/` as `.md`. Note: `web_extract(file://...)` is
     blocked for local files. For scanned/image PDFs, use marker-pdf (needs ~5GB).
   - **Local file** (MD, DOCX, EPUB, TXT) → copy to `raw/articles/` or `raw/papers/`
     using `terminal` (cp / shell copy). DOCX/EPUB files may need conversion to
     markdown first — use `pandoc` if available, or `ocr-and-documents` skill for
     PDFs. If no conversion tool is available, read what you can with `read_file`
     and note limitations. Name the file descriptively.
   - **Pasted text** → save to appropriate `raw/` subdirectory
   - Name the file descriptively: `raw/articles/karpathy-wiki-2026.md`
   - **Add raw frontmatter** with `ingested`, `sha256` of the body.
     Use `source_url` for web-sourced files only (omit for local files).
     On re-ingest: recompute sha256, compare to stored value — skip if identical,
     flag drift if different. Detects silent source changes and duplicate re-ingests.

② **Discuss takeaways** with the user — what's interesting, what matters for
   the domain. (Skip this in automated/cron contexts — proceed directly.)

③ **Check what already exists** — search index.md and use `search_files` to find
   existing pages for mentioned entities/concepts. This is the difference between
   a growing wiki and a pile of duplicates.

④ **Write or update wiki pages:**
   - **New entities/concepts:** Create full pages for any entity/concept mentioned
     in the source that is notable within the domain (see SCHEMA.md Page Thresholds).
     **Use Chinese page titles** with 中英对照 when the English term is standard:
     `[[注意力机制（Attention Mechanism）]]`、`[[安德烈·卡帕西（Andrej Karpathy）]]`、
     `[[Transformer 架构]]`（well-known English term as-is + Chinese suffix）、
     `[[OpenAI]]`（well-known English name kept as-is）
   - **Existing pages:** Add new information, update facts, bump `updated` date.
     When new info contradicts existing content, follow the Update Policy.
   - **Cross-reference:** Every new or updated page must link to at least 2 other
     pages via `[[wikilinks]]`. Check that existing pages link back.
   - **Tags:** Only use tags from the taxonomy in SCHEMA.md
   - **Provenance:** On pages synthesizing 3+ sources, append `^[raw/articles/source.md]`
     markers to paragraphs whose claims trace to a specific source.
   - **Confidence:** For opinion-heavy, fast-moving, or single-source claims, set
     `confidence: medium` or `low` in frontmatter. Don't mark `high` unless the
     claim is well-supported across multiple sources.
   - **Stub pages for dead links:** After all pages are written, scan every
     `[[wikilink]]` in the new/updated pages. For each wikilink that points to
     a page that doesn't exist yet, create a minimal stub page (see SCHEMA.md →
     Stub Pages for format). This ensures Obsidian's graph view has no dead
     links — every concept you can click on has at least a placeholder.
     Use Chinese page names. Add stubs to the appropriate directory
     (`concepts/` or `entities/` based on what the linked term is).
     Stubs never reference `raw/` sources — their `sources:` field stays empty
     and content is derived from the wiki pages that link to them.

⑤ **Update navigation:**
   - Add new pages (full and stub) to `index.md` under the correct section, sorted by pinyin (拼音首字母) for Chinese titles
   - Update the "总页数" count and "最后更新" date in index header
   - Append to `log.md`: `## [YYYY-MM-DD] ingest | 来源标题`
   - List every file created or updated in the log entry

⑥ **Report what changed** — list every file created or updated to the user.

A single source can trigger updates across 5-15 wiki pages. This is normal
and desired — it's the compounding effect.

### 2. Query

When the user asks a question about the wiki's domain:

① **Read `index.md`** to identify relevant pages.
② **For wikis with 100+ pages**, also `search_files` across all `.md` files
   for key terms — the index alone may miss relevant content.
③ **Read the relevant pages** using `read_file`.
④ **Synthesize an answer** from the compiled knowledge. Cite the wiki pages
   you drew from: "根据 [[页面A]] 和 [[页面B]]……"
⑤ **File valuable answers back** — if the answer is a substantial 辨析 (comparison/distinction),
   deep dive, or novel synthesis, create a page in `queries/` or `comparisons/`.
   Don't file trivial lookups — only answers that would be painful to re-derive.
⑥ **Update log.md** with the query and whether it was filed.

### 3. Lint

When the user asks to lint, health-check, or audit the wiki:

① **Orphan pages:** Find pages with no inbound `[[wikilinks]]` from other pages.
```python
# Use execute_code for this — programmatic scan across all wiki pages
import os, re
from collections import defaultdict
wiki = "<WIKI_PATH>"
# Scan all .md files in entities/, concepts/, comparisons/, queries/
# Extract all [[wikilinks]] — build inbound link map
# Pages with zero inbound links are orphans
```

② **Broken wikilinks:** Find `[[links]]` that point to pages that don't exist.

③ **Index completeness:** Every wiki page should appear in `index.md`. Compare
   the filesystem against index entries.

④ **Frontmatter validation:** Every wiki page must have all required fields
   (title, created, updated, type, tags, sources). Tags must be in the taxonomy.

⑤ **Stale content:** Pages whose `updated` date is >90 days older than the most
   recent source that mentions the same entities.

⑥ **Contradictions:** Pages on the same topic with conflicting claims. Look for
   pages that share tags/entities but state different facts. Surface all pages
   with `contested: true` or `contradictions:` frontmatter for user review.

⑦ **Quality signals:** List pages with `confidence: low` and any page that cites
   only a single source but has no confidence field set — these are candidates
   for either finding corroboration or demoting to `confidence: medium`.

⑧ **Source drift:** For each file in `raw/` with a `sha256:` frontmatter, recompute
   the hash and flag mismatches. Mismatches indicate the raw file was edited
   (shouldn't happen — raw/ is immutable) or ingested from a URL that has since
   changed. Not a hard error, but worth reporting.

⑨ **Page size:** Flag pages over 200 lines — candidates for splitting.

- **Stub upgrades:** For each stub page (those with `confidence: low` and the 📝 marker), check how many other pages now [[wikilink]] to it. If a stub is referenced by 2+ full pages, flag it as a candidate for upgrade to a full page.
- **Stub cleanup:** For each stub, check if ALL pages that [[wikilink]] to it are now archived. If yes, archive the stub too — an orphan stub with no active referrers is dead weight.

⑩ **Tag audit:** List all tags in use, flag any not in the SCHEMA.md taxonomy.

⑪ **Log rotation:** If log.md exceeds 500 entries, rotate it.

⑫ **Report findings** with specific file paths and suggested actions, grouped by
   severity (broken links > orphans > source drift > contested pages > stale content > style issues).

⑬ **Append to log.md:** `## [YYYY-MM-DD] lint | N issues found`

## Working with the Wiki

### Searching

```bash
# Find pages by content
search_files "transformer" path="$WIKI" file_glob="*.md"

# Find pages by filename
search_files "*.md" target="files" path="$WIKI"

# Find pages by tag
search_files "tags:.*对齐" path="$WIKI" file_glob="*.md"

# Recent activity
read_file "$WIKI/log.md" offset=<last 20 lines>
```

### Bulk Ingest

When ingesting multiple sources at once, batch the updates:

**Sequential workflow (fewer than 5 sources, or sources that reference each other):**
1. Read all sources first
2. Identify all entities and concepts across all sources (one search pass, not N)
3. Check existing pages for all of them
4. Create/update pages in one pass (avoids redundant updates)
5. Update index.md once at the end
6. Write a single log entry covering the batch

**Parallel workflow (5+ independent sources — use delegate_task):**
When you have many sources that don't cross-reference each other heavily,
parallelize the analysis phase to save time:

1. Copy all source files to `raw/` first (one batch command).
2. **Split sources into groups** of 2-4 files each (max 3 groups — limited by
   `max_concurrent_children`). Each group gets a `delegate_task` call.
3. Each subagent reads assigned files and returns structured summary with
   entities, concepts, key quotes, and cross-references *within that group*.
4. **Collect all summaries** back in the parent session. Synthesize across
   groups — a person/idea may appear in files from different groups, and only
   the parent session can connect those dots.
5. **Create/update wiki pages in the parent session only.** The parent uses
   the combined intelligence to write entity, concept, and 辨析 pages
   with cross-group cross-references that no single subagent could produce.
6. Update `index.md` and `log.md` exclusively in the parent session.

> ⚠️ **Subagent file-mutation hazard (critical pitfall):** `delegate_task`
> children share the parent's filesystem. A subagent that writes to `index.md`
> or creates wiki pages can:
> - **Rename files** the parent is tracking (e.g. `log.md` → `log 2.md`)
> - **Overwrite** pages the parent or another subagent created
> - **Create orphans** — pages the subagent added to `index.md` but the
>   parent doesn't know about
>
> **Rule: Subagents analyze and return structured data only. The parent
> creates pages and updates navigation.** If you must let subagents write
> pages (e.g. they hold the full context needed), always verify by re-reading
> `index.md` and `log.md` in the parent immediately after — never trust
> subagent claims of "index.md updated" without a confirmation read.

### Archiving

When content is fully superseded or the domain scope changes:
1. Create `_archive/` directory if it doesn't exist
2. Move the page to `_archive/` with its original path (e.g., `_archive/entities/old-page.md`)
3. Remove from `index.md`
4. Update any pages that linked to it — replace wikilink with plain text + "（已归档）"
5. Log the archive action

### Obsidian Integration

The wiki directory works as an Obsidian vault out of the box:
- `[[wikilinks]]` render as clickable links
- Graph View visualizes the knowledge network
- YAML frontmatter powers Dataview queries
- The `raw/assets/` folder holds images referenced via `![[image.png]]`

For best results:
- Set Obsidian's attachment folder to `raw/assets/`
- Enable "Wikilinks" in Obsidian settings (usually on by default)
- **Exclude `raw/` from graph view:** Settings → Files & Links → Excluded files → add `raw/`. Also in Graph view → Filter → Excluded folders → add `raw/`. This keeps the knowledge graph clean — only wiki pages appear as nodes, not raw source files.
- **Graph color grouping by `type`:** Graph view → Groups → create groups based on `type` field. Suggested colors: `entity` → blue (#4a9eff), `concept` → green (#4caf50), `comparison` → orange (#ff9800), `query` → grey (#9e9e9e). Stubs (pages with `confidence: low`) → dashed border or low opacity.
- Install Dataview plugin for queries like `TABLE tags FROM "实体" WHERE contains(tags, "公司")`

If using the Obsidian skill alongside this one, set `OBSIDIAN_VAULT_PATH` to the
same directory as the wiki path.

### Obsidian Headless (servers and headless machines)

On machines without a display, use `obsidian-headless` instead of the desktop app.
It syncs vaults via Obsidian Sync without a GUI — perfect for agents running on
servers that write to the wiki while Obsidian desktop reads it on another device.

**Setup:**
```bash
# Requires Node.js 22+
npm install -g obsidian-headless

# Login (requires Obsidian account with Sync subscription)
ob login --email <email> --password '<password>'

# Create a remote vault for the wiki
ob sync-create-remote --name "Karpathy Wiki"

# Connect the wiki directory to the vault
cd ~/wiki
ob sync-setup --vault "<vault-id>"

# Initial sync
ob sync

# Continuous sync (foreground — use systemd for background)
ob sync --continuous
```

**Continuous background sync via systemd:**
```ini
# ~/.config/systemd/user/obsidian-wiki-sync.service
[Unit]
Description=Obsidian Karpathy Wiki Sync
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/path/to/ob sync --continuous
WorkingDirectory=/home/user/wiki
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now obsidian-wiki-sync
# Enable linger so sync survives logout:
sudo loginctl enable-linger $USER
```

This lets the agent write to `~/wiki` on a server while you browse the same
vault in Obsidian on your laptop/phone — changes appear within seconds.

## Pitfalls

- **Never modify files in `raw/`** — sources are immutable. Corrections go in wiki pages.
- **Always orient first** — read SCHEMA + index + recent log before any operation in a new session.
  Skipping this causes duplicates and missed cross-references.
- **Always update index.md and log.md** — skipping this makes the wiki degrade. These are the
  navigational backbone.
- **Don't create pages for things outside the domain** — follow the Page Thresholds in SCHEMA.md. A footnote about a car brand in an AI wiki doesn't warrant a page. But within-domain concepts mentioned in one source are fair game.
- **Don't create pages without cross-references** — isolated pages are invisible. Every page must
  link to at least 2 other pages.
- **Frontmatter is required** — it enables search, filtering, and staleness detection.
- **Tags must come from the taxonomy** — freeform tags decay into noise. Add new tags to SCHEMA.md
  first, then use them.
- **Keep pages scannable** — a wiki page should be readable in 30 seconds. Split pages over
  200 lines. Move detailed analysis to dedicated deep-dive pages.
- **Ask before mass-updating** — if an ingest would touch 10+ existing pages, confirm
  the scope with the user first.
- **Rotate the log** — when log.md exceeds 500 entries, rename it `log-YYYY.md` and start fresh.
  The agent should check log size during lint.
- **Handle contradictions explicitly** — don't silently overwrite. Note both claims with dates,
  mark in frontmatter, flag for user review.

## Related Tools

[llm-wiki-compiler](https://github.com/atomicmemory/llm-wiki-compiler) is a Node.js CLI that
compiles sources into a concept wiki with the same Karpathy inspiration. It's Obsidian-compatible,
so users who want a scheduled/CLI-driven compile pipeline can point it at the same vault this
skill maintains. Trade-offs: it owns page generation (replaces the agent's judgment on page
creation) and is tuned for small corpora. Use this skill when you want agent-in-the-loop curation;
use llmwiki when you want batch compile of a source directory.
