# Config and Index Maintenance

## Config example

Reusable non-secret parameters can go into `rag_config.json`:

```json
{
  "build": {
    "chunk_size": 1200,
    "overlap": 200,
    "batch_size": 16,
    "timeout": 60,
    "sleep": 0
  },
  "query": {
    "top_k": 6,
    "candidates": 12,
    "wiki_top_k": 5,
    "timeout": 60,
    "expand_context": true,
    "context_window": 1,
    "multi_query": false
  }
}
```

Command-line flags override config values.

## Defaults

- Raw input: `wiki/raw/`
- Default index output: `检索索引/`
- Recommended raw index: `检索索引/raw`
- Recommended wiki index: `检索索引/wiki`
- API key env var: `SILICONFLOW_API_KEY`
- Private key config: `~/.hermes/private/SiliconFlow-rag/config.json` preferred; `~/.codex/SiliconFlow-rag/config.json` legacy fallback
- Embedding model: `BAAI/bge-m3`
- Optional rerank model: `Qwen/Qwen3-Reranker-8B`

## Maintenance wording

- When `wiki/raw/` changes materially, update the raw index. If the tool reports ordinary new/changed files, call this "新增到索引" or "增量更新", not "重建".
- When `claims/`, `concepts/`, `entities/`, `comparisons/`, `synthesis/`, or `queries/` change materially, update the wiki index. If only files changed, call this "增量更新 wiki 索引".
- Use "重建" only for a full rebuild: initial build from an empty/missing index, or automatic fallback caused by changed `metadata_mode`, embedding model, mock/real mode, chunk size, overlap, include/exclude dirs, source dir, or index format.

## Index file rules

Keep each index directory's files together:

```text
manifest.json
chunks.jsonl
embeddings.jsonl
```

Do not edit index files by hand. Re-run `build_index.py` instead.
