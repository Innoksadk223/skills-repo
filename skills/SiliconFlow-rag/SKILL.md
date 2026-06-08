---
name: SiliconFlow-rag
description: Build and query local RAG indexes for social-science Markdown collections. Uses SiliconFlow embeddings and optional rerank; supports raw-only retrieval and wiki-first retrieval with karpathy-wiki structure.
---

# SiliconFlow RAG

> Provider: 硅基流动 (SiliconFlow)  
> Embedding endpoint: `POST https://api.siliconflow.cn/v1/embeddings`  
> Rerank endpoint: `POST https://api.siliconflow.cn/v1/rerank`  
> Default embedding: `BAAI/bge-m3`  
> Optional reranker: `Qwen/Qwen3-Reranker-8B`

Use this skill for the retrieval step of a social-science paper knowledge system. It builds local indexes from Markdown, stores embeddings locally, and returns evidence snippets for the agent to answer from.

This skill does not convert source documents and does not build the wiki. Use `markitdown` to produce Markdown in `wiki/raw/`, then use `karpathy-wiki` to build structured pages such as `claims/`, `concepts/`, `entities/`, and `comparisons/`.

## API Contract

The scripts must keep SiliconFlow calls in the documented format.

Embedding requests send text arrays only:

```json
{
  "model": "BAAI/bge-m3",
  "input": ["chunk text"],
  "encoding_format": "float",
  "truncate": "right"
}
```

Rerank requests send a query and a text document array:

```json
{
  "model": "Qwen/Qwen3-Reranker-8B",
  "query": "用户问题",
  "documents": ["candidate text 1", "candidate text 2"],
  "top_n": 6,
  "return_documents": false,
  "instruction": "请根据用户问题判断候选材料是否能提供直接证据、概念解释或论证支持。"
}
```

Do not send wiki graph objects, metadata dictionaries, or raw file paths as API-specific parameters. Wiki enhancement happens locally by converting wiki structure into retrieval text before embedding and by expanding the query before raw retrieval.

## Retrieval Modes

### Raw-only retrieval

Use when the user wants direct evidence from source materials.

```text
question → embedding → raw chunks → optional rerank → evidence
```

### Wiki-first retrieval

Use when a `karpathy-wiki` structure exists and the user asks conceptual, argumentative, cross-source, or thesis-writing questions.

```text
question
→ retrieve wiki index
→ extract titles/frontmatter/wikilinks/claim relations
→ build expanded query locally
→ retrieve raw index
→ optional rerank raw candidates
→ output Wiki Hits + Expanded Query + Raw Evidence
```

Wiki-first retrieval uses two indexes:

```text
检索索引/wiki    # claims/concepts/entities/comparisons/synthesis/queries
检索索引/raw     # wiki/raw original evidence
```

The wiki layer improves recall by finding the relevant concept/claim/objection path; the raw layer provides citable evidence.

## Workflow

1. Confirm `SILICONFLOW_API_KEY` is available in the environment or local private key config before real indexing or querying.
   - On first real use, if the key is missing, ask the user for a SiliconFlow API key before running the scripts.
   - If the user wants to save it, save only to `~/.codex/SiliconFlow-rag/config.json` as `{"SILICONFLOW_API_KEY":"..."}`.
   - Do not put API keys in `rag_config.json`, repo files, skill files, logs, manifests, or examples.
   - Explain that indexing sends chunks to SiliconFlow embeddings; querying sends the question/expanded query; reranking sends candidate snippets.

2. Build or incrementally update the raw index:

```bash
python skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki/raw \
  --index-dir 检索索引/raw
```

3. If the project has `karpathy-wiki` pages, build or incrementally update the wiki index:

```bash
python skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki \
  --index-dir 检索索引/wiki \
  --include-dirs claims,concepts,entities,comparisons,synthesis,queries \
  --exclude-dirs raw,_archive \
  --metadata-mode wiki
```

`--metadata-mode wiki` converts each wiki page into retrieval-friendly text before embedding. For claim pages, this includes title, type, claim_type, core/status/confidence, supports/opposes/limits/depends_on, related concepts/entities/comparisons, sources, `## 命题`, `## 关键证据`, and body wikilinks.

4. Query raw-only mode:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --index-dir 检索索引/raw \
  --question "用户的问题"
```

5. Query wiki-first mode:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "用户的问题"
```

6. Enable reranking only when the user asks for better ordering, precise ranking, rerank mode, or similar wording:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "用户的问题" \
  --rerank
```

7. Context expansion remains available for raw-only and wiki-first raw evidence retrieval:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py \
  --index-dir 检索索引/raw \
  --question "用户的问题" \
  --expand-context \
  --context-window 1
```

8. Use `--stats` to inspect an index:

```bash
python skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引/raw --stats
python skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引/wiki --stats
```

## Config Example

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
- Private API key config: `~/.codex/SiliconFlow-rag/config.json`
- Embedding model: `BAAI/bge-m3`
- Optional rerank model: `Qwen/Qwen3-Reranker-8B`
- Default retrieval: top 6 local vector matches
- Optional rerank retrieval: local candidate top 12, reranked top 6

## Multi-路召回架构 (RAG Norm)

The skill implements a lightweight variant of the RAG retrieval norm internally:
- **Dual Retrieval**: Parallel Vector Similarity (Embedding) + BM25 Lexical search to avoid missing exact matches.
- **RRF (Reciprocal Rank Fusion)**: Both paths are ranked independently and fused using `1/(k+rank)`.
- **Multi-Query (Optional)**: If `--multi-query` is passed, the skill asks an LLM (Qwen2.5-7B-Instruct) to generate 3 additional sub-queries. The retrieval runs all queries against both Vector and BM25, returning the max score for each chunk before RRF fusion.
- **Rerank (Optional)**: Set `--rerank` to refine the RRF Top-K candidates using Qwen3-Reranker-8B. The final output is bounded by `--top-k`.

## Index Maintenance

- When `wiki/raw/` changes materially, update the raw index. If the tool reports only ordinary new/changed files, call this "新增到索引" or "增量更新", not "重建".
- When `claims/`, `concepts/`, `entities/`, `comparisons/`, `synthesis/`, or `queries/` change materially, update the wiki index. If only files changed, call this "增量更新 wiki 索引".
- Use "重建" only for a full rebuild: initial build from an empty/missing index, or automatic fallback caused by changed `metadata_mode`, embedding model, mock/real mode, chunk size, overlap, include/exclude dirs, source dir, or index format.
- After the initial full build, `--incremental` can be used when index settings are unchanged. The script keeps unchanged chunks, adds/updates changed chunks, and removes deleted-file chunks.
- Keep each index directory's `manifest.json`, `chunks.jsonl`, and `embeddings.jsonl` together.
- Do not edit index files by hand. Re-run `build_index.py` instead.

## Answering Rules

- Treat script output as evidence, not as the final answer.
- In wiki-first mode, use `# Wiki Hits` to understand the conceptual/argument path and `# Raw Evidence` for citable evidence.
- Cite source paths shown by the script.
- Do not claim a paper says something unless the raw evidence supports it.
- If retrieval returns weak or empty evidence, say so and suggest updating the relevant index or broadening the question.
- Reranking is optional. If reranking fails, continue with local similarity results and mention the fallback.

## Testing

Run the self-test without a real API key:

```bash
python skills/SiliconFlow-rag/scripts/self_test.py
```

The self-test uses mock embeddings and validates:

- full raw indexing;
- incremental indexing;
- context expansion;
- stats output;
- wiki include/exclude filters;
- wiki metadata-mode retrieval text;
- wiki-first query expansion and raw evidence retrieval.

## Common Pitfalls

- Indexing only `wiki/raw/` when the user asks conceptual or argumentative questions. Build the wiki index too.
- Mixing raw and wiki into one index too early. Prefer two indexes so wiki explains and raw proves.
- Sending metadata objects to SiliconFlow rerank. The API expects `documents` as text strings.
- Treating wiki hits as proof. Wiki pages guide recall; raw snippets provide evidence.
- Forgetting `--exclude-dirs raw,_archive` when building the wiki index.
- Relying on rerank for recall. Rerank only reorders candidates; retrieval and wiki expansion decide what enters the candidate pool.
