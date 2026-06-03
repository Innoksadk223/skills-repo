---
name: social-science-rag
description: Build and query a local RAG index for social-science paper Markdown collections. Use when users need semantic search, evidence retrieval, or question answering over a `raw/` folder of MarkItDown-processed Markdown using SiliconFlow embeddings, with optional reranking.
---

# Social Science RAG

Use this skill for the retrieval step of a social-science paper knowledge system. It indexes Markdown files from `wiki/raw/`, stores embeddings locally in `检索索引/`, and returns evidence snippets to answer from.

This skill does not convert source documents and does not build the wiki. Use `markitdown` to produce Markdown in `wiki/raw/`, then use `llm-wiki` for wiki generation.

When used through `social-science-km`, run this skill from the project root `<source-folder>（知识库）/`. In that root, `wiki/raw/` is the Markdown corpus and `检索索引/` is the local index. Do not index the original source folder directly.

## Workflow

1. Confirm `SILICONFLOW_API_KEY` is available in the environment before real indexing or querying.
   - On first real use, if the key is missing, ask the user for a SiliconFlow API key as configuration before running `build_index.py` or `query_index.py`.
   - Explain that indexing sends Markdown chunks to SiliconFlow for embeddings, and querying sends the user's question for embedding. Reranking, when enabled, also sends candidate snippets.
   - It is acceptable to save the key in a local private config for reuse, but never save a real key in the repository skill files. The default private config path is `~/.codex/social-science-rag/config.json` with `{"SILICONFLOW_API_KEY":"..."}`.
   - Do not write the key into repository files, skill files, logs, manifests, or committed examples. The repository version must remain empty of secrets because it may be uploaded.
2. Build or refresh the local index:

```bash
python skills/social-science-rag/scripts/build_index.py --md-dir wiki/raw --index-dir 检索索引
```

3. Query the index and use the returned evidence to answer the user:

```bash
python skills/social-science-rag/scripts/query_index.py --index-dir 检索索引 --question "用户的问题"
```

4. Enable reranking only when the user explicitly asks for better ordering, precise ranking, rerank mode, or similar wording:

```bash
python skills/social-science-rag/scripts/query_index.py --index-dir 检索索引 --question "用户的问题" --rerank
```

## Defaults

- Markdown input: `wiki/raw/`
- Index output: `检索索引/`
- API key env var: `SILICONFLOW_API_KEY`
- Local private API key config: `~/.codex/social-science-rag/config.json`
- Embedding model: `BAAI/bge-m3`
- Optional rerank model: `BAAI/bge-reranker-v2-m3`
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
- Keep `检索索引/manifest.json`, `chunks.jsonl`, and `embeddings.jsonl` together.
- Do not edit index files by hand. Re-run `build_index.py` instead.

## Testing

Run the self-test without a real API key:

```bash
python skills/social-science-rag/scripts/self_test.py
```

The self-test uses mock embeddings and validates chunking, index writing, and query output formatting.
