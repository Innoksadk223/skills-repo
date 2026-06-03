---
name: social-science-km
description: Coordinate a social-science paper knowledge-management workflow. Use when users want to turn source PDFs or documents into a MarkItDown-processed `raw/` folder, compile them into a `wiki/` knowledge base with llm-wiki, and build/query a local RAG index with SiliconFlow-rag.
---

# Social Science Knowledge Management

Use this skill as the coordinator for a three-step social-science paper knowledge system:

1. Convert source documents to Markdown with `markitdown`, writing the processed Markdown into the knowledge-base wiki's `raw/` directory.
2. Compile that `raw/` into a persistent `wiki/` knowledge base with `llm-wiki`.
3. Build and query a local RAG index from that `raw/` with `SiliconFlow-rag`.

Do not create a separate `资料md/` layer. In this workflow, `wiki/raw/` is the single bottom-layer text store.

## Directory Contract

Always keep the source folder and the knowledge-base folder as siblings. If the source folder is `03-心理学文献/`, create or use `03-心理学文献（知识库）/` beside it as the project root for all processed outputs.

Use this fixed directory contract:

```
<source-folder>/                      ← 原始文档。只读，永不修改或删除
<source-folder>（知识库）/
├── wiki/                             ← $WIKI_PATH（llm-wiki 项目根）
│   ├── SCHEMA.md                     ← llm-wiki 初始化生成的结构与规范
│   ├── index.md                      ← 知识库内容目录
│   ├── log.md                        ← 操作日志
│   ├── raw/                          ← markitdown 输出的 Markdown 语料
│   │   ├── <topic>/                  ← 按原始主题/目录组织
│   │   └── _主题索引.md              ← Step 1 生成的语料清单
│   ├── entities/                     ← llm-wiki 编译的实体页
│   ├── concepts/                     ← llm-wiki 编译的概念页
│   ├── comparisons/                  ← llm-wiki 编译的比较页
│   └── queries/                      ← llm-wiki 存档的查询结果
└── 检索索引/                         ← RAG 本地索引（由 SiliconFlow-rag 维护）
```

Treat `<source-folder>（知识库）/` as the project root when running commands. Set `WIKI_PATH` to `<知识库>/wiki/` so that `llm-wiki` operates on the correct wiki directory. `SiliconFlow-rag` indexes `wiki/raw/` (relative to the project root) and stores embeddings in `检索索引/`.

Do not place `raw/`, `wiki/`, or `检索索引/` beside the source folder's parent directory, and do not put the knowledge-base folder inside the source folder. Keeping source and knowledge-base folders as siblings prevents converted Markdown, wiki files, and index files from being scanned again as source material.

## Step 1: Convert Sources To Raw Markdown

Use the `markitdown` skill and Microsoft MarkItDown CLI.

Procedure:

1. Check the active Python environment with `python -m markitdown --version`; install `markitdown` and needed optional dependencies such as `markitdown[pdf]` only if missing.
2. Recursively scan the source folder for convertible files such as PDF, DOCX, PPTX, XLSX, HTML, TXT, and common document formats supported by MarkItDown.
3. Convert each file to `<知识库>/wiki/raw/<source-folder-name>/...` while preserving the relative directory structure when possible.
4. Existing Markdown sources may be copied into `<知识库>/wiki/raw/<source-folder-name>/...` as processed Markdown without changing their content.
5. Do not overwrite original files.
6. If conversion fails or output is empty, record the source path, target path, and error in `wiki/raw/_conversion_failures.md` and tell the user.
7. Generate or update `wiki/raw/_主题索引.md` with a concise file list and rough topic grouping when enough filenames or headings are available.

Validation:

- `wiki/raw/` exists.
- At least one `.md` file exists under `wiki/raw/`, unless all conversions failed.
- `wiki/raw/_conversion_failures.md` exists when any file failed.

## Step 2: Build Wiki

Use `llm-wiki`. Set `WIKI_PATH` to `<知识库>/wiki/` before running it. Its source layer is `wiki/raw/`, which in this workflow already contains MarkItDown-processed Markdown.

Procedure:

1. Read the installed `llm-wiki/SKILL.md` if not already loaded in the conversation.
2. Export `WIKI_PATH=<知识库>/wiki/` (or tell the agent to set this environment variable).
3. Initialize only missing `wiki/` structures according to that skill:
   - `wiki/SCHEMA.md`
   - `wiki/index.md`
   - `wiki/log.md`
4. Compile raw content into `wiki/entities/`, `wiki/concepts/`, and `wiki/comparisons/` per llm-wiki's workflow.
5. Update `wiki/index.md` and append to `wiki/log.md` after ingest.
6. Preserve factual disagreements with source attribution instead of smoothing them away.

Validation:

- `wiki/index.md` exists.
- `wiki/log.md` exists.
- At least one article exists under `wiki/entities/` or `wiki/concepts/` after a successful ingest.

## Step 3: Build Or Query RAG

Use `SiliconFlow-rag`.

Before the first real RAG build or query, make sure `SILICONFLOW_API_KEY` is configured in the environment or saved in the local private config `~/.codex/SiliconFlow-rag/config.json`. If it is missing, ask the user for a SiliconFlow API key, explain that raw Markdown chunks/questions will be sent to SiliconFlow for embeddings, and save it only locally if the user wants reuse. Never write a real key into repository files because the skills repo may be uploaded.

Build or refresh the index after `wiki/raw/` changes, running from the project root (`<知识库>/`):

```bash
python skills-hermes/research/SiliconFlow-rag/scripts/build_index.py --md-dir wiki/raw --index-dir 检索索引
```

Query without rerank by default:

```bash
python skills-hermes/research/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引 --question "用户的问题"
```

Use rerank only when the user explicitly asks for better ordering, precise ranking, rerank mode, or use of the rerank model:

```bash
python skills-hermes/research/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引 --question "用户的问题" --rerank
```

Validation:

- `检索索引/manifest.json` exists.
- `检索索引/chunks.jsonl` exists.
- `检索索引/embeddings.jsonl` exists.
- Query output contains source paths and evidence snippets.

## User-Facing Behavior

- Explain progress in plain Chinese.
- If any source file cannot be converted, explicitly list it or point to `wiki/raw/_conversion_failures.md`.
- If `SILICONFLOW_API_KEY` and the local private key config are both missing, stop before real RAG indexing/querying and ask the user for the key; do not fake a real index.
- For final answers over the knowledge base, use retrieved evidence and cite source paths from the RAG output or wiki article links.
- Prefer simple defaults. Ask the user only when a missing choice would change the project structure or data privacy boundary.
