# Ingest

When the user provides a source (URL, file, paste), integrate it into the wiki.

## Procedure

### ① Capture the raw source

- **URL** → use `web_extract` to get markdown, save to `raw/articles/`
- **PDF (remote URL)** → use `web_extract` (handles PDFs), save to `raw/papers/`
- **PDF (local file)** → use pymupdf (see `ocr-and-documents` skill) to extract text, save to `raw/papers/` as `.md`. Note: `web_extract(file://...)` is blocked for local files. For scanned/image PDFs, use marker-pdf (needs ~5GB).
- **Local file** (MD, DOCX, EPUB, TXT) → copy to `raw/articles/` or `raw/papers/` using `terminal` (cp / shell copy). DOCX/EPUB files may need conversion to markdown first — use `pandoc` if available, or `ocr-and-documents` skill for PDFs. If no conversion tool is available, read what you can with `read_file` and note limitations. Name the file descriptively.
- **Pasted text** → save to appropriate `raw/` subdirectory
- Name the file descriptively: `raw/articles/karpathy-wiki-2026.md`
- **Add raw frontmatter** with `ingested`, `sha256` of the body. Compute the hash over the body after the closing `---`, ignoring blank lines immediately after frontmatter. Use `source_url` for web-sourced files only (omit for local files). On re-ingest: recompute sha256, compare to stored value — skip if identical, flag drift if different.

### ② Discuss takeaways

Discuss with the user — what's interesting, what matters for the domain. (Skip this in automated/cron contexts — proceed directly.)

### ③ Check what already exists

Search index.md and use `search_files` to find existing pages for mentioned entities/concepts. This is the difference between a growing wiki and a pile of duplicates.

### ④ Write or update wiki pages

**New entities/concepts:** Create full pages for any entity/concept mentioned in the source that is notable within the domain (see SCHEMA.md Page Thresholds).

**Concept pages may use these Chinese section headings:** `核心概念`、`相关概念`、`概念厘定`.

- `核心概念` = the source's main ideas, mechanisms, arguments, or constructs that the page is centrally about.
- `相关概念` = concepts explicitly present in the same raw source that help explain, compare, qualify, contextualize, extend, or apply the core concept, but do not form the page's main focus.
- `概念厘定` = an optional clarification section used to distinguish adjacent concepts, resolve ambiguity, define boundaries, or reconcile terminology differences found in the current raw source or already-existing wiki pages.

Rules for these sections:
- `核心概念` and `相关概念` must be grounded in `raw/` sources only. Do not add a concept unless it appears explicitly in the ingested raw material.
- `相关概念` is not a dump bucket for background knowledge. Leave out plausible but unconfirmed concepts.
- `概念厘定` is optional — add it only when there is a real distinction, overlap, ambiguity, naming conflict, or scope issue worth clarifying.
- `概念厘定` may rely on the current raw source plus already-existing wiki pages, but must not introduce unsupported outside knowledge.
- If the clarification grows into a reusable multi-concept distinction, create or update a dedicated page under `comparisons/` and keep only a short summary in the concept page.
- Prefer omission over inference.

**Page titles:** Chinese with 中英对照 when the English term is standard: `[[注意力机制（Attention Mechanism）]]`、`[[安德烈·卡帕西（Andrej Karpathy）]]`、`[[Transformer 架构]]`（well-known English term as-is + Chinese suffix）、`[[OpenAI]]`（well-known English name kept as-is）

**Existing pages:** Add new information, update facts, bump `updated` date. When new info contradicts existing content, follow the Update Policy below.

**Cross-reference:** Every new or updated page must link to at least 2 other pages via `[[wikilinks]]`. Check that existing pages link back.

**Tags:** Only use tags from the taxonomy in SCHEMA.md.

**Provenance:** On pages synthesizing 3+ sources, append `^[raw/articles/source.md]` markers to paragraphs whose claims trace to a specific source.

**Confidence:** For opinion-heavy, fast-moving, or single-source claims, set `confidence: medium` or `low` in frontmatter. Don't mark `high` unless the claim is well-supported across multiple sources.

**Stub pages for dead links:** After all pages are written, scan every `[[wikilink]]` in the new/updated pages. For each wikilink that points to a page that doesn't exist yet, create a minimal stub page (see SCHEMA.md → Stub Pages for format). This ensures Obsidian's graph view has no dead links. Use Chinese page names. Add stubs to the appropriate directory (`concepts/` or `entities/`). Stubs never reference `raw/` sources — their `sources:` field stays empty and content is derived from the wiki pages that link to them.

### ⑤ Update navigation

- Add new pages (full and stub) to `index.md` under the correct section, sorted by pinyin (拼音首字母) for Chinese titles
- Update the "总页数" count and "最后更新" date in index header
- Append to `log.md`: `## [YYYY-MM-DD] ingest | 来源标题`
- List every file created or updated in the log entry

### ⑥ Report what changed

List every file created or updated to the user.

A single source can trigger updates across 5-15 wiki pages. This is normal and desired — it's the compounding effect.

## Update Policy

When new information conflicts with existing content:

1. Check the dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and sources
3. Mark the contradiction in frontmatter: `contradictions: [page-name]`
4. Flag for user review in the lint report
