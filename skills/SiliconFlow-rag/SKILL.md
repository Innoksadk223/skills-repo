---
name: SiliconFlow-rag
description: Build and query a local RAG index for social-science paper Markdown collections. Uses 硅基流动 (SiliconFlow) API for embeddings. Reranking (via Qwen/Qwen3-Reranker-8B) is optional — only enabled when explicitly requested.
---

# SiliconFlow RAG

> **嵌入模型提供商：硅基流动 (SiliconFlow)**
> embedding: `BAAI/bge-m3` · reranker（可选）: `Qwen/Qwen3-Reranker-8B` · API: `https://api.siliconflow.cn/v1/embeddings`

Use this skill for the retrieval step of a social-science paper knowledge system. It indexes Markdown files from `wiki/raw/`, stores embeddings locally in `检索索引/`, and returns evidence snippets to answer from.

This skill does not convert source documents and does not build the wiki. Use `markitdown` to produce Markdown in `wiki/raw/`, then use `karpathy-wiki` for wiki generation.

When used through `social-science-km`, run this skill from the project root `<source-folder>（知识库）/`. In that root, `wiki/raw/` is the Markdown corpus and `检索索引/` is the local index. Do not index the original source folder directly.

## Workflow

1. Confirm `SILICONFLOW_API_KEY` is available in the environment or local private key config before real indexing or querying.
   - On first real use, if the key is missing, ask the user for a SiliconFlow API key before running `build_index.py` or `query_index.py`.
   - After the user provides a key, ask whether to save it for future use. If yes, save it only to `~/.codex/SiliconFlow-rag/config.json` as `{"SILICONFLOW_API_KEY":"..."}`. If no, use it only for the current run/session.
   - Explain that indexing sends Markdown chunks to SiliconFlow for embeddings, and querying sends the user's question for embedding. Reranking, when enabled, also sends candidate snippets.
   - Keep API keys separate from RAG parameter config. Do not put API keys in `rag_config.json`.
   - Do not write the key into repository files, skill files, project files, logs, manifests, or committed examples. The repository version must remain empty of secrets because it may be uploaded.
2. On first RAG parameter setup, if no config file exists and the user has not already provided values, ask whether to use defaults or self-configure.
   - If the user chooses defaults, use the values in the Defaults section and proceed without extra questions.
   - If the user chooses self-configuration, ask the user to fill in the parameters they want to control, especially `chunk_size`, `overlap`, `batch_size`, `top_k`, and `candidates`; keep unspecified values at their defaults.
   - Save reusable non-secret RAG parameters in a local project config such as `rag_config.json`. Do not store API keys in this file.
3. Build or refresh the local index:

```bash
python skills/SiliconFlow-rag/scripts/build_index.py --md-dir wiki/raw --index-dir 检索索引
```

Optional: keep RAG parameters in a local JSON config, then pass it with `--config`. Command-line flags override config values.

```json
{
  "build": {
    "md_dir": "wiki/raw",
    "index_dir": "检索索引",
    "chunk_size": 1200,
    "overlap": 200,
    "batch_size": 16,
    "timeout": 60,
    "sleep": 0
  },
  "query": {
    "index_dir": "检索索引",
    "top_k": 6,
    "candidates": 12,
    "timeout": 60
  }
}
```

```bash
python skills/SiliconFlow-rag/scripts/build_index.py --config rag_config.json
```

**Incremental indexing (recommended after initial full build):**

When you add or modify a few files, use `--incremental` to only re-index changed content — avoids re-embedding everything and saves API cost:

```bash
python skills/SiliconFlow-rag/scripts/build_index.py --md-dir wiki/raw --index-dir 检索索引 --incremental
```

How it works:
- Compares file content hashes (SHA256) against previous manifest
- Only chunks + embeds new or changed files
- Removes chunks from deleted files
- Keeps existing embeddings for unchanged files
- Reports "up to date" if nothing changed
- Falls back to full build if no existing index found

4. Query the index and use the returned evidence to answer the user:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引 --question "用户的问题"
```

```bash
python skills/SiliconFlow-rag/scripts/query_index.py --config rag_config.json --question "用户的问题"
```

5. Enable reranking only when the user explicitly asks for better ordering, precise ranking, rerank mode, or similar wording:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引 --question "用户的问题" --rerank
```

6. Context expansion (optional): include adjacent chunks from the same source file to provide surrounding context for each result:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引 --question "用户的问题" --expand-context
```

Use `--context-window N` to control how many chunks on each side (default: 1). Context chunks are labeled `[context for chunk X]` in the output and do not show similarity/rerank scores.

7. Index statistics: inspect index health and composition without querying:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引 --stats
```

Outputs file count, chunk count, embedding model, build time, format version, per-file chunk distribution, and hash tracking status.

## Defaults

- Markdown input: `wiki/raw/`
- Index output: `检索索引/`
- API key env var: `SILICONFLOW_API_KEY`
- Local private API key config: `~/.codex/SiliconFlow-rag/config.json`
- Private API key config format: `{"SILICONFLOW_API_KEY":"..."}`
- Embedding model: `BAAI/bge-m3`
- Optional rerank model: `Qwen/Qwen3-Reranker-8B`
- Build config: `--config <json>` can set `md_dir`, `index_dir`, `model`, `api_key_env`, `api_key_file`, `chunk_size`, `overlap`, `batch_size`, `timeout`, and `sleep`.
- Query config: `--config <json>` can set `index_dir`, `top_k`, `candidates`, `embedding_model`, `rerank_model`, `api_key_env`, `api_key_file`, `timeout`, `expand_context`, and `context_window`.
- Config format: use top-level keys or nested `build` / `query` sections. Command-line flags have the highest priority.
- Default retrieval: local vector similarity top 6
- Optional rerank retrieval: local candidate top 12, reranked top 6

## Answering Rules

- Treat script output as evidence, not as the final answer.
- Answer from retrieved snippets and cite source paths shown by the script.
- If retrieval returns weak or empty evidence, say so and ask for a broader question or a refreshed index.
- Do not claim a paper says something unless the returned snippet supports it.
- Reranking is an enhancement, not a requirement. If reranking fails, continue with local similarity results and mention the fallback.

## Index Maintenance

- Rebuild the index whenever `wiki/raw/` changes materially.
- After the initial full build, prefer `--incremental` for daily updates — it uses content hashes (SHA256) to detect changes and only re-embeds new/modified files.
- Staleness detection: `social-science-km`'s `check_rebuild_rag.py` compares current file hashes against those stored in `manifest.json` (`file_hashes` field, `format_version: 2`).
- Keep `检索索引/manifest.json`, `chunks.jsonl`, and `embeddings.jsonl` together.
- Do not edit index files by hand. Re-run `build_index.py` instead.

## Testing

Run the self-test without a real API key:

```bash
python skills/SiliconFlow-rag/scripts/self_test.py
```

The self-test uses mock embeddings and validates chunking, index writing, and query output formatting.
