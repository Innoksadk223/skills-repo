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

### Bulk Ingest Pattern (50+ files, multi-domain)

When the raw corpus is large and spans multiple disciplines, the llm-wiki parallel workflow is essential. Split source files by domain/field into 2–3 groups, spin one `delegate_task` subagent per group, and have each return **structured extraction only** (no file writes). The parent then synthesizes and creates pages.

**Grouping strategy**: split by source directory domain — e.g. classical texts, secondary scholarship, empirical psychology. Keep groups under ~30 files each.

**Subagent prompt structure** (see `references/bulk-ingest-subagent-template.md`):
- Domain context (what this wiki covers)
- Exact file paths to read
- Output format: Entities, Concepts, Cross-references, Key themes
- Explicit instruction: "Only analyze, do NOT create or write any files"

**Parent synthesis**: collect all subagent summaries, identify cross-group connections that no single subagent could see, then create wiki pages (concepts first, then entities, then comparisons). Update index.md and log.md in one pass at the end.

**Pitfall**: subagent file-mutation hazard (llm-wiki skill warns about this). Subagents share the parent filesystem — never let them write wiki pages or update navigation. They return structured data; the parent writes.

Validation:

- `wiki/index.md` exists.
- `wiki/log.md` exists.
- At least one article exists under `wiki/entities/` or `wiki/concepts/` after a successful ingest.

## Step 3: Build Or Query RAG

Use `SiliconFlow-rag`.

Before the first real RAG build or query, make sure `SILICONFLOW_API_KEY` is configured in the environment or saved in the local private config `~/.codex/SiliconFlow-rag/config.json`. If it is missing, ask the user for a SiliconFlow API key, explain that raw Markdown chunks/questions will be sent to SiliconFlow for embeddings, and save it only locally if the user wants reuse. Never write a real key into repository files because the skills repo may be uploaded.

### Initial Build

Build the index after `wiki/raw/` is populated, running from the project root (`<知识库>/`):

```bash
python skills/SiliconFlow-rag/scripts/build_index.py --md-dir wiki/raw --index-dir 检索索引
```

### Proactive Index Refresh (mandatory)

**Every session** where the knowledge base is mentioned, proactively check whether the RAG index is stale before doing any query or wiki work. Do NOT wait for the user to ask.

1. Create a helper script `<知识库>/check_rebuild_rag.py` if it doesn't exist (see template below).
2. Run a check-only scan:

```bash
cd "<知识库>"
python check_rebuild_rag.py --check
```

3. **If stale** ("需要重建"): tell the user "RAG 索引过期了，raw 有更新，要不要重建？" and wait for confirmation.
4. **If current** ("已是最新"): say nothing, the index is fine.
5. After user confirms, rebuild:

```bash
cd "<知识库>"
python check_rebuild_rag.py
```

**check_rebuild_rag.py template** — save this as `<知识库>/check_rebuild_rag.py`:

```python
"""
RAG 索引自动刷新脚本
比较 wiki/raw/ 最新 .md 时间 vs 检索索引构建时间。
用法: python check_rebuild_rag.py         # 检查 + 自动重建
      python check_rebuild_rag.py --check  # 仅检查
"""
import json, os, sys, subprocess
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR / "wiki" / "raw"
INDEX_DIR = SCRIPT_DIR / "检索索引"
MANIFEST = INDEX_DIR / "manifest.json"
BUILD_SCRIPT = Path("D:/hermes/skills/research/SiliconFlow-rag/scripts/build_index.py")


def newest_md_mtime(directory: Path) -> datetime:
    latest = datetime(1970, 1, 1, tzinfo=timezone.utc)
    for f in directory.rglob("*.md"):
        mt = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if mt > latest:
            latest = mt
    return latest


def index_built_at() -> datetime | None:
    if not MANIFEST.exists():
        return None
    with open(MANIFEST) as f:
        data = json.load(f)
    return datetime.fromisoformat(data["created_at"])


def main():
    check_only = "--check" in sys.argv
    raw_time = newest_md_mtime(RAW_DIR)
    index_time = index_built_at()

    if index_time is None:
        print("[CHECK] 索引不存在 → 需要构建")
        need_rebuild = True
    elif raw_time > index_time:
        delta = raw_time - index_time
        mins = int(delta.total_seconds() / 60)
        print(f"[CHECK] raw 比 index 新 {mins} 分钟 → 需要重建")
        need_rebuild = True
    else:
        print("[CHECK] 索引已是最新 → 跳过")
        need_rebuild = False

    if check_only:
        return

    if need_rebuild:
        print("[BUILD] 重建中...")
        result = subprocess.run(
            [sys.executable, str(BUILD_SCRIPT),
             "--md-dir", str(RAW_DIR),
             "--index-dir", str(INDEX_DIR)],
            cwd=str(SCRIPT_DIR),
            capture_output=True, text=True, timeout=600
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"[ERROR] {result.stderr}", file=sys.stderr)
            sys.exit(1)
        print("[DONE] 索引重建完成")


if __name__ == "__main__":
    main()
```

**Pitfalls**:
- `os.walk` can hang on iCloud Drive paths — the script uses `rglob("*.md")` to avoid this.
- File timestamps may get touched during wiki page creation, resulting in false "stale" reports. Use judgment: if no actual new content was added to `raw/`, skip the rebuild.
- Rebuilding sends all chunks to SiliconFlow API (tokens + ~30-60s for typical corpus).

### Query

Query without rerank by default:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引 --question "用户的问题"
```

Use rerank only when the user explicitly asks for better ordering, precise ranking, rerank mode, or use of the rerank model:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引 --question "用户的问题" --rerank
```

Validation:

- `检索索引/manifest.json` exists.
- `检索索引/chunks.jsonl` exists.
- `检索索引/embeddings.jsonl` exists.
- Query output contains source paths and evidence snippets.

## User-Facing Behavior

- Explain progress in plain Chinese.
- **Proactive RAG check**: every session where the knowledge base is involved, run `check_rebuild_rag.py --check` before any query or wiki work. If stale, ask the user before rebuilding. Do NOT wait for the user to tell you to check.
- If any source file cannot be converted, explicitly list it or point to `wiki/raw/_conversion_failures.md`.
- If `SILICONFLOW_API_KEY` and the local private key config are both missing, stop before real RAG indexing/querying and ask the user for the key; do not fake a real index.
- For final answers over the knowledge base, use retrieved evidence and cite source paths from the RAG output or wiki article links.
- Prefer simple defaults. Ask the user only when a missing choice would change the project structure or data privacy boundary.
