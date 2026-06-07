---
name: social-science-km
description: Coordinate a social-science paper knowledge-management workflow. Use when users want to turn source documents into a processed `raw/` folder using MinerU for PDFs and MarkItDown for other formats, compile them into a `wiki/` knowledge base with karpathy-wiki, and build/query a local RAG index with SiliconFlow-rag.
---

# Social Science Knowledge Management

Use this skill as the coordinator for a three-step social-science paper knowledge system:

1. Convert source documents to Markdown in the knowledge-base wiki's `raw/` directory: use MinerU first for all PDF files, especially scanned PDFs, 古籍/影印本, papers, tables, formulas, and complex layouts; use `markitdown` only as the lightweight first pass for non-PDF sources; if MarkItDown fails, returns empty output, or produces obvious乱码/garbled text, retry that file with MinerU.
2. Compile that `raw/` into a persistent, graph-readable `wiki/` knowledge base with `karpathy-wiki`, including `claims/` argument nodes when the corpus contains thesis, theory, objections, limitations, or evidence logic.
3. Build and query two local RAG indexes with `SiliconFlow-rag`: `检索索引/raw` for source evidence and `检索索引/wiki` for wiki-first recall expansion.

Do not create a separate `资料md/` layer. In this workflow, `wiki/raw/` is the single bottom-layer text store. `wiki/claims`, `wiki/concepts`, `wiki/entities`, and `wiki/comparisons` are graph-readable knowledge layers, not replacements for raw evidence.

## Directory Contract

Always keep the source folder and the knowledge-base folder as siblings. If the source folder is `03-心理学文献/`, create or use `03-心理学文献（知识库）/` beside it as the project root for all processed outputs.

Use this fixed directory contract:

```
<source-folder>/                      ← 原始文档。只读，永不修改或删除
<source-folder>（知识库）/
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

Treat `<source-folder>（知识库）/` as the project root when running commands. Set `WIKI_PATH` to `<知识库>/wiki/` so that `karpathy-wiki` operates on the correct wiki directory. `SiliconFlow-rag` builds two indexes relative to the project root: `wiki/raw/` → `检索索引/raw`, and graph-readable wiki pages → `检索索引/wiki`.

Do not place `raw/`, `wiki/`, or `检索索引/` beside the source folder's parent directory, and do not put the knowledge-base folder inside the source folder. Keeping source and knowledge-base folders as siblings prevents converted Markdown, wiki files, and index files from being scanned again as source material.

## Step 1: Convert Sources To Raw Markdown

Use `mineru-document-extractor` for PDFs and any MarkItDown failure/fallback cases. Use the `markitdown` skill and Microsoft MarkItDown CLI only for non-PDF sources that convert cleanly.

Dependency note: this workflow requires both the MinerU skill and the MinerU MCP. The skill is already installed; the MinerU MCP still needs to be installed/configured from https://mineru.net/ecosystem so agents can call MinerU directly.

Procedure:

1. Load/read both relevant skills when needed: `mineru-document-extractor` for PDFs and fallback extraction; `markitdown` for non-PDF document conversion.
2. Check the active Python environment with `python -m markitdown --version`; install `markitdown` and needed optional dependencies only if missing and only for non-PDF conversion.
3. Recursively scan the source folder for convertible files such as PDF, DOCX, PPTX, XLSX, HTML, TXT, Markdown, and common document formats.
4. Route conversions by file type:
   - **PDF (`.pdf`) → MinerU first**. Do not use MarkItDown as the default PDF path. Real test case: a 37-page scanned classical-text PDF (`荀子集解（王先谦） 天论篇.pdf`) produced empty/near-empty MarkItDown output because there was no text layer, while MinerU OCR extracted usable Markdown. MinerU preserves layouts, tables, formulas, OCR, and scanned/影印 content better.
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
- After all batches finish, the parent must check for missing source files, duplicate outputs, failed conversions, and MarkItDown outputs that still look garbled before moving to Step 2.

Validation: every source file is either represented by one `.md` output under `wiki/raw/` or listed in `_conversion_failures.md` with the attempted tools and error.

Validation:

- `wiki/raw/` exists.
- At least one `.md` file exists under `wiki/raw/`, unless all conversions failed.
- PDF entries in `wiki/raw/` were produced by MinerU unless explicitly noted otherwise.
- Any MarkItDown failure/乱码 fallback is either successfully replaced by MinerU output or recorded in `wiki/raw/_conversion_failures.md`.
- `wiki/raw/_conversion_failures.md` exists when any file failed after all fallback attempts.

## Step 2: Build Wiki

Use `karpathy-wiki`. Set `WIKI_PATH` to `<知识库>/wiki/` before running it. Its source layer is `wiki/raw/`, which in this workflow already contains Markdown processed by MinerU and/or MarkItDown.

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
4. Compile raw content into `wiki/claims/`, `wiki/concepts/`, `wiki/entities/`, `wiki/comparisons/`, and lightweight `wiki/synthesis/` per karpathy-wiki's workflow.
   - Use `claims/` for theses, support propositions, objections, limitations, and bridge claims.
   - Use `synthesis/` only as route maps, reading order, current state, and gaps; do not keep long durable evidence banks there.
5. Update `wiki/index.md` and append to `wiki/log.md` after ingest.
6. Preserve factual disagreements with source attribution instead of smoothing them away.

### Bulk Ingest Pattern (50+ files, multi-domain)

When the raw corpus is large and spans multiple disciplines, the karpathy-wiki parallel workflow is essential. Split source files by domain/field into 2–3 groups, spin one `delegate_task` subagent per group, and have each return **structured extraction only** (no file writes). The parent then synthesizes and creates pages.

**Grouping strategy**: split by source directory domain — e.g. classical texts, secondary scholarship, empirical psychology. Keep groups under ~30 files each.

**Subagent prompt structure** (use `references/bulk-ingest-subagent-template.md` — copy and fill in placeholders):
- Domain context (what this wiki covers)
- Exact file paths to read
- Output format: Entities, Concepts, Cross-references, Key themes
- Explicit instruction: "Only analyze, do NOT create or write any files"

**Parent synthesis**: collect all subagent summaries, identify cross-group connections that no single subagent could see, then create wiki pages in this order: claims and concepts first, then entities and comparisons, then only lightweight synthesis route maps if cross-domain themes emerge. Update index.md and log.md in one pass at the end.

**Pitfall**: subagent file-mutation hazard (karpathy-wiki skill warns about this). Subagents share the parent filesystem — never let them write wiki pages or update navigation. They return structured data; the parent writes.

Validation:

- `wiki/index.md` exists.
- `wiki/log.md` exists.
- At least one article exists under `wiki/entities/` or `wiki/concepts/` after a successful ingest.

## Step 3: Build Or Query RAG

Use `SiliconFlow-rag`.

Before the first real RAG build or query, make sure `SILICONFLOW_API_KEY` is configured in the environment or saved in the local private config `~/.codex/SiliconFlow-rag/config.json`. If it is missing, ask the user for a SiliconFlow API key, explain that raw Markdown chunks/questions will be sent to SiliconFlow for embeddings, wiki-page retrieval text will be sent when building the wiki index, and rerank sends candidate snippets. Never write a real key into repository files because the skills repo may be uploaded.

### Initial Build

Build both indexes after `wiki/raw/` and graph-readable wiki pages are populated, running from the project root (`<知识库>/`):

```bash
python skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki/raw \
  --index-dir 检索索引/raw

python skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki \
  --index-dir 检索索引/wiki \
  --include-dirs claims,concepts,entities,comparisons,synthesis,queries \
  --exclude-dirs raw,_archive \
  --metadata-mode wiki
```

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

### Query

Default to wiki-first for conceptual, argumentative, cross-source, or thesis-writing questions:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "用户的问题"
```

Use raw-only only when the user explicitly wants direct source snippets without wiki expansion:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --index-dir 检索索引/raw \
  --question "用户的问题"
```

Use rerank only when the user explicitly asks for better ordering, precise ranking, rerank mode, or use of the rerank model:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "用户的问题" \
  --rerank
```

### Unified Query (km_query.py)

For daily use, `km_query.py` should combine dual-index staleness checks + wiki-first query into one command.

```bash
python km_query.py "亲亲与仁的关系"
```

Behaviour:
- **Staleness check**: checks both raw and wiki manifests; if either is stale, prints a warning and exits unless the user has confirmed an index update. Use "增量更新/新增到索引" wording for ordinary new/changed files; reserve "重建" for forced full rebuilds caused by settings/model/index-format changes.
- **If current**: runs `query_index.py --wiki-first` and prints `# Wiki Hits`, `# Expanded Query`, and `# Raw Evidence`.
- `--raw-only`: run raw-only query against `检索索引/raw`.
- `--skip-check`: skip staleness check, query with current indexes as-is.
- `--rerank`: enable SiliconFlow rerank for raw evidence candidates.

This is the recommended query entry point for agents and daily use — it prevents stale-index answers while using wiki structure for recall.

Validation:

- `检索索引/raw/manifest.json`, `chunks.jsonl`, and `embeddings.jsonl` exist.
- `检索索引/wiki/manifest.json`, `chunks.jsonl`, and `embeddings.jsonl` exist when wiki pages exist.
- Wiki-first query output contains `# Wiki Hits`, `# Expanded Query`, `# Raw Evidence`, source paths, and evidence snippets.

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
- **Prefer `km_query.py`** for queries: it auto-checks both indexes and uses wiki-first retrieval by default — one command instead of several.
- If any source file cannot be converted, explicitly list it or point to `wiki/raw/_conversion_failures.md`.
- If `SILICONFLOW_API_KEY` and the local private key config are both missing, stop before real RAG indexing/querying and ask the user for the key; do not fake a real index.
- For final answers over the knowledge base, follow the **Answering Template** above: cite source paths, keep evidence and interpretation separate, always flag uncertainties.
- Prefer simple defaults. Ask the user only when a missing choice would change the project structure or data privacy boundary.
