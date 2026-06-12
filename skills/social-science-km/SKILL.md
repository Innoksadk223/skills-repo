---
name: social-science-km
description: Use when coordinating a social-science knowledge base across source conversion, deep-reading dossiers, karpathy-wiki graph compilation, and SiliconFlow-rag indexing or querying.
---

# Social Science Knowledge Management

Use this skill as the coordinator for a layered social-science knowledge system:

1. **Convert sources → `wiki/raw/`**: use MinerU first for all PDF files, especially scanned PDFs, 古籍/影印本, papers, tables, formulas, and complex layouts; use MarkItDown only as the lightweight first pass for clean non-PDF sources.
2. **Deep-read long or important sources → `reading_dossiers/`**: use `deep-reading-to-wiki` when direct raw-to-wiki ingest would be shallow, when the source is long/theoretical, or when the source is thesis-critical.
3. **Compile dossiers/raw → graph-readable `wiki/`**: use `karpathy-wiki` for formal `claims/`, `concepts/`, `entities/`, `comparisons/`, lightweight `synthesis/`, backlinks, `index.md`, and `log.md`.
4. **Build/query RAG indexes → `检索索引/`**: use `SiliconFlow-rag` for raw evidence recall, source discovery, and wiki-first expansion.

Do not create a separate `资料md/` layer. In this workflow, `wiki/raw/` is the single bottom-layer text store; `reading_dossiers/` is a pre-wiki interpretation layer; `wiki/claims`, `wiki/concepts`, `wiki/entities`, and `wiki/comparisons` are graph-readable knowledge layers, not replacements for raw evidence.

## Workflow Router

Use the cheapest path that preserves quality:

| User intent / source state | Route |
|---|---|
| New PDFs or documents need conversion | Step 1 → Step 2 decision → Step 3 → Step 4 update |
| Source is a book, long chapter, theory-heavy paper, or thesis-critical text | Step 2 is required before Step 3 |
| Source is short, narrow, and low-risk | Step 3 may compile directly from `wiki/raw/` |
| Existing wiki question or citation lookup | Step 4 query; do not re-ingest |
| User wants to supplement a topic already visible in the wiki | Gap-driven expansion → Step 4 source discovery → Step 2 → Step 3 → Step 4 update |
| Wiki feels shallow or missing context after ingest | Step 2 retroactively creates a dossier, then Step 3 revises wiki |
| RAG output is weak | Check index freshness, then escalate query mode before changing wiki |

`deep-reading-to-wiki` exists to prevent shallow raw-to-wiki compilation. It produces `reading_dossiers/` only; formal wiki writing remains `karpathy-wiki`'s job.

### Gap-Driven Expansion

Use this route when the user looks at the current wiki and states an inclination or gap, for example: "我想补充一些关于儿童教育的内容."

Procedure:

1. Capture the user's intent as a research direction, not a conclusion.
2. Orient to the current wiki: read `wiki/SCHEMA.md`, `wiki/index.md`, recent `wiki/log.md`, and search graph-readable pages for the topic.
3. State the suspected gap: thin concept, missing claim, absent objection, weak comparison, underused source, or missing raw evidence.
4. Run source discovery with `SiliconFlow-rag`:
   - start with wiki-first when the topic is conceptual or argumentative;
   - use raw-only for direct source lookup;
   - add `--multi-query` when wording mismatch is likely;
   - add `--expand-context --context-window 1` when local passage context matters.
5. Return a short candidate-source list: source path, why it may help, key terms, and whether it likely needs deep reading.
6. If candidate raw sources are weak, stale, or fewer than needed, report the blocker and broaden/check the index before deep reading.
7. For each long/high-value candidate source, run Step 2 with `deep-reading-to-wiki`, passing the user intent and source-discovery shortlist into the dossier.
8. Compile accepted dossiers through Step 3 with `karpathy-wiki`.
9. After wiki edits, run Step 4 stale-index check and update the relevant index.

Do not add wiki pages from the user's inclination alone. The inclination chooses the search path; raw evidence and dossiers decide what enters the graph.

Keep this loop short: **intent → candidate raw sources → dossier when needed → formal wiki edit → index update**. Do not invent extra durable layers.

## Directory Contract

Always keep the source folder and the knowledge-base folder as siblings. If the source folder is `03-心理学文献/`, create or use `03-心理学文献（知识库）/` beside it as the project root for all processed outputs.

Use this fixed directory contract:

```
<source-folder>/                      ← 原始文档。只读，永不修改或删除
<source-folder>（知识库）/
├── reading_dossiers/                 ← deep-reading-to-wiki 输出；预编译深读档案，不是 raw，不进正式图谱
├── wiki/                             ← $WIKI_PATH（karpathy-wiki 项目根）
│   ├── SCHEMA.md                     ← karpathy-wiki 初始化生成的结构与规范
│   ├── index.md                      ← 知识库内容目录
│   ├── log.md                        ← 操作日志
│   ├── raw/                          ← MinerU / MarkItDown 输出的 Markdown 语料
│   │   ├── <topic>/                  ← 按原始主题/目录组织
│   │   └── _主题索引.md              ← Step 1 生成的语料清单
│   ├── claims/                       ← karpathy-wiki 编译的论证节点页
│   ├── concepts/                     ← karpathy-wiki 编译的概念页
│   ├── entities/                     ← karpathy-wiki 编译的实体页
│   ├── comparisons/                  ← karpathy-wiki 编译的比较/辨析页
│   ├── queries/                      ← karpathy-wiki 存档的查询结果
│   ├── synthesis/                    ← 轻量入口页/路线图，不承载主要证据银行
│   ├── qa-log.md                     ← 问答日志（karpathy-wiki 维护）
└── 检索索引/                         ← RAG 本地索引（由 SiliconFlow-rag 维护）
    ├── raw/                          ← raw source evidence index
    └── wiki/                         ← wiki structure index for wiki-first recall
```

Treat `<source-folder>（知识库）/` as the project root when running commands. Set `WIKI_PATH` to `<知识库>/wiki/` so that `karpathy-wiki` operates on the correct wiki directory. `reading_dossiers/` is read by agents as precompiled interpretation, but it is not raw evidence and is not a formal graph layer. `SiliconFlow-rag` builds two indexes relative to the project root: `wiki/raw/` → `检索索引/raw`, and graph-readable wiki pages → `检索索引/wiki`.

Do not place `raw/`, `wiki/`, `reading_dossiers/`, or `检索索引/` beside the source folder's parent directory, and do not put the knowledge-base folder inside the source folder. Keeping source and knowledge-base folders as siblings prevents converted Markdown, dossiers, wiki files, and index files from being scanned again as source material.

## Step 1: Convert Sources To Raw Markdown

Use `mineru-document-extractor` for PDFs and any MarkItDown failure/fallback cases. Use the `markitdown` skill and Microsoft MarkItDown CLI only for non-PDF sources that convert cleanly.

Dependency note: this workflow requires both the MinerU skill and the MinerU MCP. The skill is already installed; the MinerU MCP still needs to be installed/configured from https://mineru.net/ecosystem so agents can call MinerU directly.

Procedure:

1. Load/read both relevant skills when needed: `mineru-document-extractor` for PDFs and fallback extraction; `markitdown` for non-PDF document conversion.
2. Check the active Python environment with `python -m markitdown --version`; install `markitdown` and needed optional dependencies only if missing and only for non-PDF conversion.
3. Recursively scan the source folder for convertible files such as PDF, DOCX, PPTX, XLSX, HTML, TXT, Markdown, and common document formats.
4. Route conversions by file type:
   - **PDF (`.pdf`) → MinerU first**. Do not use MarkItDown as the default PDF path. MinerU is preferred for scanned/影印 PDFs, papers, tables, formulas, and complex layouts because it provides OCR and stronger document-structure extraction.
   - **Non-PDF → MarkItDown first** when the format is supported and the output looks usable.
   - **MarkItDown fallback → MinerU** when MarkItDown fails, returns empty/near-empty output, or produces obvious乱码/garbled text.
5. Convert each file to `<知识库>/wiki/raw/<source-folder-name>/...` while preserving the relative directory structure when possible. Keep the output extension as `.md`.
6. Existing Markdown sources may be copied into `<知识库>/wiki/raw/<source-folder-name>/...` as processed Markdown without changing their content.
7. Do not overwrite original files.
8. When MinerU is available through MCP, prefer the MinerU MCP tools. Use the MinerU CLI only when MCP is unavailable, the user explicitly asks for CLI usage, or the MCP tool cannot satisfy the workflow.
9. Detect unusable MarkItDown output before accepting it. Treat these as fallback triggers: empty output, only boilerplate/page markers, widespread replacement characters (`�`), mojibake patterns, or mostly unreadable text compared with the source language.
10. If both primary conversion and MinerU fallback fail, record the source path, target path, attempted tools, and errors in `wiki/raw/_conversion_failures.md` and tell the user.
11. Generate or update `wiki/raw/_主题索引.md` with a concise file list and rough topic grouping when enough filenames or headings are available.

### Batch Source Conversion With Subagents

For large source folders, source conversion may be split across subagents by directory, file type, or topic batch. This is especially useful when many PDFs need MinerU processing or when mixed formats may require MarkItDown → MinerU fallback checks.

Use subagents for **independent conversion batches only**:

- Assign each subagent a non-overlapping file list and a matching output subtree under `wiki/raw/`.
- Each subagent may run MinerU/MarkItDown for its assigned files and write only its own raw Markdown outputs plus a small per-batch conversion report.
- The parent agent owns shared files: merge per-batch reports into `wiki/raw/_conversion_failures.md`, generate/update `wiki/raw/_主题索引.md`, and verify final coverage.
- Do not let multiple subagents edit `_主题索引.md`, `_conversion_failures.md`, wiki pages, navigation, or RAG indexes concurrently.
- After all batches finish, the parent must check for missing source files, duplicate outputs, failed conversions, and MarkItDown outputs that still look garbled before moving to the Step 2 deep-reading decision.

Validation: every source file is either represented by one `.md` output under `wiki/raw/` or listed in `_conversion_failures.md` with the attempted tools and error.

Validation:

- `wiki/raw/` exists.
- At least one `.md` file exists under `wiki/raw/`, unless all conversions failed.
- PDF entries in `wiki/raw/` were produced by MinerU unless explicitly noted otherwise.
- Any MarkItDown failure/乱码 fallback is either successfully replaced by MinerU output or recorded in `wiki/raw/_conversion_failures.md`.
- `wiki/raw/_conversion_failures.md` exists when any file failed after all fallback attempts.

## Step 2: Create Deep-Reading Dossiers

Use `deep-reading-to-wiki` before formal wiki compilation when a source is long, theory-heavy, argument-rich, book-length, thesis-critical, or likely to produce shallow wiki nodes if read only through ordinary raw ingest.

Skip this step only when the source is short, narrow, low-risk, and the user explicitly wants quick ingest.

Procedure:

1. Read the installed `deep-reading-to-wiki/SKILL.md` if not already loaded in the conversation.
2. Work from the project root (`<知识库>/`), not inside `wiki/`.
3. Orient to the target wiki first: read `wiki/SCHEMA.md`, `wiki/index.md`, and recent `wiki/log.md`.
4. Use L0-L3 reading budget from `deep-reading-to-wiki`; do not default to full-book reading.
5. If invoked from Gap-Driven Expansion, include `trigger: user_directed_expansion`, `user_intent`, and the `source_discovery` shortlist in the dossier frontmatter.
6. Write the dossier to `reading_dossiers/<source-title>-深读档案.md`.
7. Require raw anchors, context capsules, skipped-area notes, candidate nodes, and a wiki handoff checklist.
8. Do not write `wiki/claims`, `wiki/concepts`, `wiki/entities`, `wiki/comparisons`, `wiki/synthesis`, `index.md`, or `log.md` in this step.

Validation:

- `reading_dossiers/` exists when Step 2 is used.
- Each long/high-value source has a corresponding dossier or a written reason for skipping.
- Each high-value candidate in the dossier has a raw anchor and context capsule.
- The dossier passes its anti-slack self-check before Step 3.

### Batch Deep Reading

For many long sources, split by non-overlapping source files or source groups. A subagent may create only its assigned dossier path under `reading_dossiers/`; it must not edit wiki pages, navigation files, or RAG indexes.

The parent agent owns final routing: review dossier quality, decide which dossiers are ready for `karpathy-wiki`, and keep a short list of skipped or blocked sources.

## Step 3: Compile Dossiers Or Raw Into Wiki

Use `karpathy-wiki`. Set `WIKI_PATH` to `<知识库>/wiki/` before running it. Its evidence layer is still `wiki/raw/`; when a dossier exists, treat it as a precompiled reading guide that points back to raw anchors, not as raw evidence.

Procedure:

1. Read the installed `karpathy-wiki/SKILL.md` if not already loaded in the conversation.
2. Export `WIKI_PATH=<知识库>/wiki/` (or tell the agent to set this environment variable).
3. Initialize only missing `wiki/` structures according to that skill:
   - `wiki/SCHEMA.md`
   - `wiki/index.md`
   - `wiki/log.md`
   - `wiki/qa-log.md`
   - `wiki/claims/`
   - `wiki/concepts/`
   - `wiki/entities/`
   - `wiki/comparisons/`
   - `wiki/queries/`
   - `wiki/synthesis/`
4. If a relevant dossier exists, compile from `reading_dossiers/` plus raw anchors. If no dossier is needed, compile directly from `wiki/raw/`.
5. Compile content into `wiki/claims/`, `wiki/concepts/`, `wiki/entities/`, `wiki/comparisons/`, and lightweight `wiki/synthesis/` per karpathy-wiki's workflow.
   - Use `claims/` for theses, support propositions, objections, limitations, and bridge claims.
   - Use `synthesis/` only as route maps, reading order, current state, and gaps; do not keep long durable evidence banks there.
   - For large or mature corpora, optional GraphRAG-lite global entry pages may live under `wiki/synthesis/_global/`. These pages are only theme/community route maps: major debates, reading paths, topic clusters, and gaps. They must link to `claims/`, `concepts/`, `entities/`, or `comparisons/`; they must not become durable evidence banks.
6. For user-directed expansion, compile only claims/concepts/comparisons/entities that are backed by accepted dossier entries or checked raw anchors.
7. Preserve context risks from the dossier inside the formal wiki page when they affect interpretation.
8. Update `wiki/index.md` and append to `wiki/log.md` after ingest.
9. When a dossier is used, update its frontmatter to `status: compiled` and list key `compiled_to:` wiki pages.
10. Preserve factual disagreements with source attribution instead of smoothing them away.

### Bulk Ingest Pattern (50+ files, multi-domain)

When the raw corpus is large and spans multiple disciplines, split work by stage:

- **Step 2 deep reading**: subagents may create non-overlapping dossiers under `reading_dossiers/`.
- **Step 3 formal wiki compilation**: subagents return structured analysis only; the parent writes all wiki pages and navigation files.

**Grouping strategy**: split by source directory domain — e.g. classical texts, secondary scholarship, empirical psychology. Keep groups under ~30 files each.

**Deep-reading subagent prompt shape**:
- Domain context (what this wiki covers)
- Exact file paths to read
- Exact dossier output path under `reading_dossiers/`
- Instruction to use `deep-reading-to-wiki`
- Explicit instruction: "Do not create or edit wiki pages"

**Wiki-compilation subagent prompt shape**:
- Domain context and existing wiki targets
- Exact raw files and/or dossier files to inspect
- Output format: candidate claims, concepts, entities, comparisons, cross-links, context risks
- Explicit instruction: "Only analyze, do NOT create or write any files"

**Parent synthesis**: collect dossiers and subagent summaries, identify cross-group connections that no single subagent could see, then create wiki pages in this order: claims and concepts first, then entities and comparisons, then only lightweight synthesis route maps if cross-domain themes emerge. Update index.md and log.md in one pass at the end.

**Pitfall**: subagent file-mutation hazard (karpathy-wiki skill warns about this). Subagents share the parent filesystem — never let them write wiki pages or update navigation. Only Step 2 subagents may write their assigned dossier files.

Validation:

- `wiki/index.md` exists.
- `wiki/log.md` exists.
- At least one article exists under `wiki/entities/` or `wiki/concepts/` after a successful compile.

## Step 4: Build Or Query RAG

Use `SiliconFlow-rag`.

Before the first real RAG build or query, make sure `SILICONFLOW_API_KEY` is configured in the environment or saved in the local private config `~/.codex/SiliconFlow-rag/config.json`. If it is missing, ask the user for a SiliconFlow API key, explain that raw Markdown chunks/questions will be sent to SiliconFlow for embeddings, wiki-page retrieval text will be sent when building the wiki index, and rerank sends candidate snippets. Never write a real key into repository files because the skills repo may be uploaded.

### Initial Build

Build both indexes after `wiki/raw/` and graph-readable wiki pages are populated, running from the project root (`<知识库>/`):

```bash
python skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki/raw \
  --index-dir 检索索引/raw \
  --metadata-mode enriched_raw

python skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki \
  --index-dir 检索索引/wiki \
  --include-dirs claims,concepts,entities,comparisons,synthesis,queries \
  --exclude-dirs raw,_archive \
  --metadata-mode wiki
```

Do not include `reading_dossiers/` in either default index. Dossiers are AI-generated precompiled reading guides; they may guide wiki compilation, but raw evidence must still come from `wiki/raw/` and formal recall should come from graph-readable wiki pages.

`enriched_raw` is the default raw-index mode for this workflow once wiki pages exist. It adds retrieval-only labels from wiki claims/concepts/entities/comparisons to raw chunks, improving recall without changing the evidence boundary: the quoted/cited text is still the raw chunk, not the wiki label. If this is the very first build and the wiki layer is empty, a plain raw index is acceptable temporarily; after Step 3 creates wiki pages, rebuild or incrementally update the raw index with `--metadata-mode enriched_raw`.

### Proactive Index Status Check & Incremental Update (mandatory)

**Every session** where the knowledge base is mentioned, proactively check whether either RAG index is stale before doing any query or wiki work. Do NOT wait for the user to ask.

1. Create a helper script `<知识库>/check_rebuild_rag.py` if it doesn't exist.
2. Run a check-only scan:

```bash
cd "<知识库>"
python check_rebuild_rag.py --check
```

3. **If stale**: tell the user which index needs updating, and distinguish the operation precisely:
   - `new/changed` files → say "新增/改动，需要增量更新索引" or "补入索引".
   - `deleted` files → say "有删除，需要从索引移除对应条目".
   - only say "重建" when the tool reports a settings/model/index-format change that forces a **full rebuild**.
   - Example: "RAG 索引有更新：raw 有 1 个新增文件，要不要增量更新 raw 索引？"
4. **If current**: say nothing, the indexes are fine.
5. After user confirms, update/add to the index:

```bash
cd "<知识库>"
python check_rebuild_rag.py
```

**Staleness logic**:

- Raw index checks `wiki/raw/` against `检索索引/raw/manifest.json`.
- Wiki index checks `wiki/claims`, `wiki/concepts`, `wiki/entities`, `wiki/comparisons`, `wiki/synthesis`, and `wiki/queries` against `检索索引/wiki/manifest.json`.
- Content hashes are SHA256, not mtime.
- Use `--incremental`; for ordinary new/changed files, describe the result as "增量更新 / 新增到索引". `SiliconFlow-rag` falls back to a full rebuild only if index settings changed; reserve "重建" for that case.
- If the wiki index is stale, run `karpathy-wiki` lint before updating the wiki index when the lint script is available. Broken links, source drift, missing claim structure, and frontmatter issues should be reported before embedding the wiki layer. Do not block urgent raw-only queries on non-severe wiki lint findings.

### Query

Default to routed querying rather than one expensive mode for every question. Use the cheapest mode that can answer the question well, then escalate only when retrieval quality is weak.

**Routing defaults:**

- Direct source lookup ("原文", "出处", "哪一段", "引用", "证据", page/source/quote/passage) → raw-only.
- Conceptual, argumentative, cross-source, comparison, or thesis-writing questions → wiki-first.
- Broad wording, terminology mismatch, or the first pass returns fewer than 3 usable raw sources → add `--multi-query`.
- Top hits are on-topic but poorly ordered, or the user is writing final prose / needs precise evidence ranking → add `--rerank`.
- A hit is relevant but depends on the previous/next paragraph, pronouns, table context, or transitional wording → add `--expand-context --context-window 1` before changing chunk size.
- Final citation checking or high-risk thesis claims → use deep mode: wiki-first + multi-query + rerank + context.

Raw-only:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --index-dir 检索索引/raw \
  --question "用户的问题"
```

Wiki-first:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "用户的问题"
```

Deep / writing mode:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "用户的问题" \
  --multi-query \
  --rerank \
  --candidates 20 \
  --expand-context \
  --context-window 1
```

### Unified Query (km_query.py)

For daily use, copy `skills/social-science-km/references/km_query.py` into the knowledge-base project root. It combines dual-index staleness checks, query routing, optional wiki lint, and query execution into one command.

```bash
python km_query.py "亲亲与仁的关系"
```

Behaviour:
- **Staleness check**: checks both raw and wiki manifests; if either is stale, prints a warning and exits unless the user uses `--skip-check`. Use "增量更新/新增到索引" wording for ordinary new/changed files; reserve "重建" for forced full rebuilds caused by settings/model/index-format changes.
- **Mode routing**: direct source lookups use raw-only; conceptual/cross-source questions use wiki-first when a wiki index exists.
- **If current**: raw-only prints `# RAG Evidence`; wiki-first prints `# Wiki Hits`, `# Expanded Query`, and `# Raw Evidence`.
- `--raw-only`: run raw-only query against `检索索引/raw`.
- `--skip-check`: skip staleness check, query with current indexes as-is.
- `--rerank`: enable SiliconFlow rerank for raw evidence candidates.
- `--multi-query`: enable LLM query rewriting when recall is weak.
- `--deep`: use the high-quality writing mode: wiki-first + multi-query + rerank + context, with `candidates=20`.

This is the recommended query entry point for agents and daily use — it prevents stale-index answers while using wiki structure for recall.

### Lightweight RAG Evaluation (recommended P1)

When changing `metadata_mode`, chunk size, overlap, include/exclude dirs, wiki structure rules, or query routing, run a small retrieval regression set before trusting the new behavior. Do not run a full evaluation for every new file; ordinary new/changed raw files only require stale-index checks and incremental updates.

Start from `skills/social-science-km/references/rag_eval_set.example.jsonl`, then create `eval/rag_eval_set.jsonl` in the knowledge-base root with 10-20 high-value questions:

```jsonl
{"question":"孝为什么不能只基于生育事实？","mode":"wiki","expected_sources":["wiki/raw/...md"],"expected_terms":["照料","生育事实"],"notes":"核心论证召回"}
{"question":"这段关于亲亲的原文出处在哪里？","mode":"raw","expected_sources":["wiki/raw/...md"],"expected_terms":["亲亲"],"notes":"直接证据查找"}
```

Minimum pass rule: expected source appears in the retrieved raw evidence and at least one expected term appears in the evidence text. LLM-judge/RAGAS-style faithfulness scoring is optional and should be used only for larger revisions or high-stakes writing.

Validation:

- `检索索引/raw/manifest.json`, `chunks.jsonl`, and `embeddings.jsonl` exist.
- `检索索引/wiki/manifest.json`, `chunks.jsonl`, and `embeddings.jsonl` exist when wiki pages exist.
- Raw index manifest uses `metadata_mode: enriched_raw` after the wiki layer exists.
- Wiki index manifest uses `metadata_mode: wiki`.
- Wiki-first query output contains `# Wiki Hits`, `# Expanded Query`, `# Raw Evidence`, source paths, and evidence snippets.
- `python skills/social-science-km/references/km_query_self_test.py` passes in the skills repo after changing `km_query.py`.

## Answering Template

When answering a knowledge-base question, the agent MUST follow this structure. Every substantive claim must cite raw evidence. Wiki hits explain the recall/argument path; raw evidence proves the answer. Never treat a wiki hit alone as proof, and never fabricate — if evidence is weak, say so.

```markdown
## 检索摘要
- 查询意图：（一句话概括用户想知道什么）
- Wiki 命中节点：（列出命中的 claim/concept/comparison/entity；如 raw-only 则写「未使用」）
- Raw 命中源文件：X 个（列出文件名）
- 索引状态：当前 / 过期（如过期已提醒用户）

## Wiki 路径
- 命中的 claim / concept / comparison 如何帮助扩展问题
- 相关的支持、反对、限定或依赖关系
- 注意：这里是召回路径，不是最终证据

## 原始证据
（每条证据一个子标题，来自不同源文件时分开展示）

### 观点／发现 A
- 来源：`wiki/raw/xxx/xxx.md`（chunk N）
> 原文引用

解读：（用 1-2 句话说明这段原文与问题的关系）

### 观点／发现 B
- 来源：`wiki/raw/yyy.md`（chunk N）
> 原文引用

解读：...

## 综合解读
- 只基于 Raw Evidence 回答问题
- 可以说明 Wiki Hits 帮助定位了哪些概念或论证节点
- 不把 wiki 页面当作原始证据引用

## 不确定项
- 哪些推论证据不足、需要更多查证
- 哪些概念在知识库中未覆盖
- 建议的后续检索方向
```

**Rules:**
- 每次回答必须包含以上五个段落。
- 如果某段落无内容（如 raw-only 下无 Wiki 路径），写「（无）」而不是删掉。
- 原文引用必须逐字复制 Raw Evidence 输出，不得改写。
- 解读部分允许用自己的话概括，但必须忠实于原文。
- Wiki Hits 只能用于解释检索路径和论证结构，不能单独支撑论文断言。
- 不确定项不是可选项——宁可多写也不敢装懂。

## User-Facing Behavior

- Explain progress in plain Chinese.
- **Proactive RAG check**: every session where the knowledge base is involved, run `check_rebuild_rag.py --check` before any query or wiki work. If either raw or wiki index is stale, ask the user before updating the index. Say "新增到索引" or "增量更新" for ordinary new/changed files; say "重建" only for full rebuilds. Do NOT wait for the user to tell you to check.
- **Source-discovery routing**: when the user wants to supplement a topic, first return candidate `wiki/raw/` sources and gaps; do not jump straight to wiki page creation.
- **Deep-reading routing**: when the user asks to ingest, process, or wiki-compile a book, long chapter, theory-heavy paper, or thesis-critical source, route through `deep-reading-to-wiki` before `karpathy-wiki` unless the user explicitly asks for a quick/rough ingest.
- **Prefer `km_query.py`** for queries: it auto-checks both indexes, routes source lookups to raw-only, and uses wiki-first for conceptual/cross-source questions — one command instead of several.
- If any source file cannot be converted, explicitly list it or point to `wiki/raw/_conversion_failures.md`.
- If `SILICONFLOW_API_KEY` and the local private key config are both missing, stop before real RAG indexing/querying and ask the user for the key; do not fake a real index.
- For final answers over the knowledge base, follow the **Answering Template** above: cite source paths, keep evidence and interpretation separate, always flag uncertainties.
- Prefer simple defaults. Ask the user only when a missing choice would change the project structure or data privacy boundary.
