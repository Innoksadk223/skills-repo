---
name: social-science-km
description: Coordinate a social-science paper knowledge-management workflow. Use when users want to turn source PDFs or documents into a MarkItDown-processed `raw/` folder, compile them into a `wiki/` knowledge base with karpathy-wiki, and build/query a local RAG index with SiliconFlow-rag.
---

# Social Science Knowledge Management

Use this skill as the coordinator for a three-step social-science paper knowledge system:

1. Convert source documents to Markdown with `markitdown`, writing the processed Markdown into the knowledge-base wiki's `raw/` directory.
2. Compile that `raw/` into a persistent `wiki/` knowledge base with `karpathy-wiki`.
3. Build and query a local RAG index from that `raw/` with `SiliconFlow-rag`.

Do not create a separate `资料md/` layer. In this workflow, `wiki/raw/` is the single bottom-layer text store.

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
│   ├── raw/                          ← markitdown 输出的 Markdown 语料
│   │   ├── <topic>/                  ← 按原始主题/目录组织
│   │   └── _主题索引.md              ← Step 1 生成的语料清单
│   ├── entities/                     ← karpathy-wiki 编译的实体页
│   ├── concepts/                     ← karpathy-wiki 编译的概念页
│   ├── comparisons/                  ← karpathy-wiki 编译的比较页
│   ├── queries/                      ← karpathy-wiki 存档的查询结果
│   ├── synthesis/                    ← karpathy-wiki 综述页
│   ├── qa-log.md                    ← 问答日志（karpathy-wiki 维护）
└── 检索索引/                         ← RAG 本地索引（由 SiliconFlow-rag 维护）
```

Treat `<source-folder>（知识库）/` as the project root when running commands. Set `WIKI_PATH` to `<知识库>/wiki/` so that `karpathy-wiki` operates on the correct wiki directory. `SiliconFlow-rag` indexes `wiki/raw/` (relative to the project root) and stores embeddings in `检索索引/`.

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

Use `karpathy-wiki`. Set `WIKI_PATH` to `<知识库>/wiki/` before running it. Its source layer is `wiki/raw/`, which in this workflow already contains MarkItDown-processed Markdown.

Procedure:

1. Read the installed `karpathy-wiki/SKILL.md` if not already loaded in the conversation.
2. Export `WIKI_PATH=<知识库>/wiki/` (or tell the agent to set this environment variable).
3. Initialize only missing `wiki/` structures according to that skill:
   - `wiki/SCHEMA.md`
   - `wiki/index.md`
   - `wiki/log.md`
   - `wiki/qa-log.md`
   - `wiki/synthesis/`
4. Compile raw content into `wiki/entities/`, `wiki/concepts/`, `wiki/comparisons/`, and `wiki/synthesis/` per karpathy-wiki's workflow.
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

**Parent synthesis**: collect all subagent summaries, identify cross-group connections that no single subagent could see, then create wiki pages (concepts first, then entities, then comparisons). After all pages are created, if cross-domain themes emerge, create a synthesis page in `wiki/synthesis/`. Update index.md and log.md in one pass at the end.

**Pitfall**: subagent file-mutation hazard (karpathy-wiki skill warns about this). Subagents share the parent filesystem — never let them write wiki pages or update navigation. They return structured data; the parent writes.

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

3. **If stale** ("需要更新"): tell the user "RAG 索引有更新，raw 有新增/改动，要不要更新？" and wait for confirmation.
4. **If current** ("已是最新"): say nothing, the index is fine.
5. After user confirms, update:

```bash
cd "<知识库>"
python check_rebuild_rag.py
```

**check_rebuild_rag.py template** — save this as `<知识库>/check_rebuild_rag.py`:

```python
"""
RAG 索引自动刷新脚本
比较 wiki/raw/ 文件内容哈希 vs 检索索引 manifest 中记录的哈希。
用法: python check_rebuild_rag.py         # 检查 + 自动更新（增量）
      python check_rebuild_rag.py --check  # 仅检查
"""
import hashlib, json, os, sys, subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR / "wiki" / "raw"
INDEX_DIR = SCRIPT_DIR / "检索索引"
MANIFEST = INDEX_DIR / "manifest.json"


def find_build_script() -> Path:
    candidates = [
        SCRIPT_DIR / "skills" / "SiliconFlow-rag" / "scripts" / "build_index.py",
        SCRIPT_DIR / "skills-hermes" / "research" / "SiliconFlow-rag" / "scripts" / "build_index.py",
        Path.home() / ".codex" / "skills" / "SiliconFlow-rag" / "scripts" / "build_index.py",
        Path.home() / ".hermes" / "skills" / "research" / "SiliconFlow-rag" / "scripts" / "build_index.py",
        Path("D:/hermes/skills/research/SiliconFlow-rag/scripts/build_index.py"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit("Cannot find SiliconFlow-rag build_index.py; install/update the skill first.")


BUILD_SCRIPT = find_build_script()

SKIP_NAMES = {"_conversion_failures.md", "_conversion_manifest.md", "_主题索引.md"}


def compute_hashes(raw_dir: Path) -> dict[str, str]:
    """Return {relative_path: sha256_hex} for all .md files under raw_dir."""
    hashes = {}
    for f in sorted(raw_dir.rglob("*.md")):
        if f.name in SKIP_NAMES:
            continue
        if any(p.startswith(".") for p in f.relative_to(raw_dir).parts):
            continue
        rel = f.relative_to(raw_dir).as_posix()
        content = f.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")
        hashes[rel] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return hashes


def main():
    check_only = "--check" in sys.argv
    current_hashes = compute_hashes(RAW_DIR)

    if not MANIFEST.exists():
        print("[CHECK] 索引不存在 → 需要构建")
        need_rebuild = True
    else:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        stored_hashes = manifest.get("file_hashes", {})
        new_or_changed = [
            rel for rel, h in current_hashes.items()
            if rel not in stored_hashes or stored_hashes[rel] != h
        ]
        deleted = [rel for rel in stored_hashes if rel not in current_hashes]

        if new_or_changed or deleted:
            detail = []
            if new_or_changed:
                detail.append(f"{len(new_or_changed)} new/changed")
            if deleted:
                detail.append(f"{len(deleted)} deleted")
            print(f"[CHECK] 内容哈希变化 ({', '.join(detail)}) → 需要更新")
            need_rebuild = True
        else:
            print("[CHECK] 索引已是最新（内容哈希一致）→ 跳过")
            need_rebuild = False

    if check_only:
        return

    if need_rebuild:
        print("[BUILD] 更新中（增量模式）...")
        result = subprocess.run(
            [sys.executable, str(BUILD_SCRIPT),
             "--md-dir", str(RAW_DIR),
             "--index-dir", str(INDEX_DIR),
             "--incremental"],
            cwd=str(SCRIPT_DIR),
            capture_output=True, text=True, timeout=600
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"[ERROR] {result.stderr}", file=sys.stderr)
            sys.exit(1)
        print("[DONE] 索引更新完成")


if __name__ == "__main__":
    main()
```

**Pitfalls**:
- `os.walk` can hang on iCloud Drive paths — the script uses `rglob("*.md")` to avoid this.
- Staleness is detected by content hash (SHA256), not mtime. Wiki page creation that touches raw files will NOT trigger false updates — only actual content changes matter.
- Updating uses `--incremental` mode: only new/changed files are re-embedded, keeping unchanged chunks intact. This saves API cost and time.
- If the manifest has no `file_hashes` field (old format_version 1 index), all files will be treated as changed and a full update occurs. After that update, format_version 2 + file_hashes are stored and incremental works normally.

### Query

Query without rerank by default:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引 --question "用户的问题"
```

Use rerank only when the user explicitly asks for better ordering, precise ranking, rerank mode, or use of the rerank model:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引 --question "用户的问题" --rerank
```

### Unified Query (km_query.py)

For daily use, `km_query.py` combines staleness check + context-expanded query into one command. Save `references/km_query.py` as `<知识库>/km_query.py`.

```bash
python km_query.py "亲亲与仁的关系"
```

Behaviour:
- **Staleness check**: compares content hashes against manifest — if raw has changed since last index build, prints a warning and exits (does NOT auto-rebuild).
- **If current**: runs `query_index.py --expand-context` and prints evidence with surrounding context.
- `--skip-check`: skip staleness check, query with current index as-is.
- `--no-context`: disable context expansion for shorter output.

This is the recommended query entry point for agents and daily use — it prevents stale-index answers with zero extra steps.

Validation:

- `检索索引/manifest.json` exists.
- `检索索引/chunks.jsonl` exists.
- `检索索引/embeddings.jsonl` exists.
- Query output contains source paths and evidence snippets.

## Answering Template

When answering a knowledge-base question, the agent MUST follow this structure. Every claim must cite a specific source (RAG snippet path or wiki article). Never fabricate — if evidence is weak, say so.

```markdown
## 检索摘要
- 查询意图：（一句话概括用户想知道什么）
- 命中源文件：X 个（列出文件名）
- 索引状态：当前 / 过期（如过期已提醒用户）

## 证据梳理
（每条证据一个子标题，来自不同源文件时分开展示）

### 观点／发现 A
- 来源：`wiki/raw/xxx/xxx.md`（chunk N）
> 原文引用

解读：（用 1-2 句话说明这段原文与问题的关系）

### 观点／发现 B
- 来源：`wiki/raw/yyy.md`（chunk N）
> 原文引用

解读：...

## 交叉引用
- 概念／观点 X 在 A 和 B 中的异同
- 与 wiki 已有条目的关联：链接到 `wiki/entities/...`、`wiki/concepts/...`、`wiki/comparisons/...` 或 `wiki/synthesis/...`
- 与其他源文件中类似论述的联系（如有）

## 不确定项
- 哪些推论证据不足、需要更多查证
- 哪些概念在知识库中未覆盖
- 建议的后续检索方向
```

**Rules:**
- 每次回答必须包含以上四个段落。
- 如果某段落无内容（如无交叉引用），写「（无）」而不是删掉。
- 原文引用必须逐字复制 RAG 输出，不得改写。
- 解读部分允许用自己的话概括，但必须忠实于原文。
- 不确定项不是可选项——宁可多写也不敢装懂。

## User-Facing Behavior

- Explain progress in plain Chinese.
- **Proactive RAG check**: every session where the knowledge base is involved, run `check_rebuild_rag.py --check` before any query or wiki work. If stale, ask the user before rebuilding. Do NOT wait for the user to tell you to check.
- **Prefer `km_query.py`** for queries: it auto-checks staleness and uses context expansion — one command instead of two.
- If any source file cannot be converted, explicitly list it or point to `wiki/raw/_conversion_failures.md`.
- If `SILICONFLOW_API_KEY` and the local private key config are both missing, stop before real RAG indexing/querying and ask the user for the key; do not fake a real index.
- For final answers over the knowledge base, follow the **Answering Template** above: cite source paths, keep evidence and interpretation separate, always flag uncertainties.
- Prefer simple defaults. Ask the user only when a missing choice would change the project structure or data privacy boundary.
