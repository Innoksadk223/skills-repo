---
name: SiliconFlow-rag
description: Use when building, updating, inspecting, or querying local JSONL RAG indexes for social-science Markdown collections, including raw evidence retrieval, source discovery for wiki expansion, wiki-first recall from karpathy-wiki pages, and `检索索引/` maintenance.
---

# SiliconFlow RAG

Build local JSONL indexes from Markdown, query them for evidence snippets, and use raw source chunks as the citation basis.

This skill does not convert source documents and does not build the wiki. Use `markitdown` for source conversion and `karpathy-wiki` for structured pages such as `claims/`, `concepts/`, `entities/`, and `comparisons/`.

For user-directed wiki expansion, this skill's role is **source discovery**: return candidate `wiki/raw/` paths, why they matter, key terms, and retrieval limits. It does not create wiki nodes and does not treat wiki hits as proof.

## Load references when needed

- API payloads and privacy surface: [references/api-contract.md](references/api-contract.md)
- Retrieval modes, RRF, multi-query, rerank, evidence boundary: [references/retrieval-architecture.md](references/retrieval-architecture.md)
- Config fields, defaults, index maintenance wording: [references/config-and-maintenance.md](references/config-and-maintenance.md)
- Self-test and syntax checks: [references/testing.md](references/testing.md)

## Safety rules

1. Confirm `SILICONFLOW_API_KEY` is available before real indexing or querying.
2. If the user wants to save the key, prefer `~/.hermes/private/SiliconFlow-rag/config.json` as `{"SILICONFLOW_API_KEY":"..."}`; legacy `~/.codex/SiliconFlow-rag/config.json` remains supported.
3. Keep private key files owner-only readable on POSIX systems, e.g. `chmod 600 ~/.hermes/private/SiliconFlow-rag/config.json`; scripts warn if group/other permissions are open.
4. Never put API keys in `rag_config.json`, repo files, skill files, logs, manifests, or examples.
5. Explain the network surface when relevant: indexing sends chunks to embeddings; querying sends the question to embeddings; `--multi-query` sends the question to chat completions; `--rerank` sends candidate snippets to rerank.

Use `python3` in examples because macOS and many Linux systems no longer provide `python`. If a specific machine only exposes `python`, use that interpreter instead; the scripts are Python 3 scripts (`#!/usr/bin/env python3`).

## Common workflow

### Build or update raw index

```bash
python3 skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki/raw \
  --index-dir 检索索引/raw
```

### Build or update wiki index

Use when `karpathy-wiki` pages exist and the question is conceptual, argumentative, cross-source, or thesis-writing oriented.

```bash
python3 skills/SiliconFlow-rag/scripts/build_index.py \
  --md-dir wiki \
  --index-dir 检索索引/wiki \
  --include-dirs claims,concepts,entities,comparisons,synthesis,queries \
  --exclude-dirs raw,_archive \
  --metadata-mode wiki
```

### Query raw-only mode

```bash
python3 skills/SiliconFlow-rag/scripts/query_index.py \
  --index-dir 检索索引/raw \
  --question "用户的问题"
```

### Query wiki-first mode

```bash
python3 skills/SiliconFlow-rag/scripts/query_index.py \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "用户的问题"
```

### Source discovery for wiki expansion

Use when the user names a direction they want to deepen, such as "补充儿童教育", and the next step is to find which raw files deserve `deep-reading-to-wiki`.

Start from wiki-first if the direction is conceptual or argumentative:

```bash
python3 skills/SiliconFlow-rag/scripts/query_index.py \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "哪些原始资料可以补充儿童教育在孝、亲亲、修身中的作用？"
```

Then broaden with raw-only when source wording may differ from the wiki wording:

```bash
python3 skills/SiliconFlow-rag/scripts/query_index.py \
  --index-dir 检索索引/raw \
  --question "儿童教育 家庭教育 爱敬 积浸 身教 保傅 内则 小学" \
  --multi-query \
  --expand-context \
  --context-window 1
```

Return a shortlist, not a final wiki answer:

| Field | Meaning |
|---|---|
| source path | Candidate `wiki/raw/...md` file. |
| why relevant | Which user intent or wiki gap it may address. |
| key terms | Terms that made the source retrievable. |
| next step | `deep-reading-to-wiki`, direct `karpathy-wiki`, or ignore for weak evidence. |
| limits | Missing context, weak hit, stale index, or needs broader query. |

If fewer than three usable raw sources appear, report that limitation and broaden the query or check index freshness before sending anything to deep reading.

### Optional query modes

Use rerank only when the user asks for better ordering, precise ranking, rerank mode, or similar wording:

```bash
python3 skills/SiliconFlow-rag/scripts/query_index.py \
  --wiki-first \
  --wiki-index-dir 检索索引/wiki \
  --raw-index-dir 检索索引/raw \
  --question "用户的问题" \
  --rerank
```

Use multi-query only when recall is weak or wording mismatch is likely:

```bash
python3 skills/SiliconFlow-rag/scripts/query_index.py \
  --index-dir 检索索引/raw \
  --question "用户的问题" \
  --multi-query
```

Add adjacent chunks when the answer needs local context:

```bash
python3 skills/SiliconFlow-rag/scripts/query_index.py \
  --index-dir 检索索引/raw \
  --question "用户的问题" \
  --expand-context \
  --context-window 1
```

### Inspect index health

```bash
python3 skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引/raw --stats
python3 skills/SiliconFlow-rag/scripts/query_index.py --index-dir 检索索引/wiki --stats
```

## Answering rules

- Treat script output as evidence, not as the final answer.
- In wiki-first mode, use `# Wiki Hits` to understand the conceptual/argument path and `# Raw Evidence` for citable evidence.
- In source-discovery mode, answer with candidate raw files first; do not synthesize final claims before `deep-reading-to-wiki` or `karpathy-wiki`.
- Cite source paths shown by the script.
- Do not claim a paper says something unless raw evidence supports it.
- If retrieval returns weak or empty evidence, say so and suggest updating the relevant index or broadening the question.
- Reranking is optional. If reranking fails, continue with local similarity results and mention the fallback.

## Common pitfalls

- Indexing only `wiki/raw/` when the user asks conceptual or argumentative questions. Build the wiki index too.
- Mixing raw and wiki into one index too early. Prefer two indexes so wiki explains and raw proves.
- Treating wiki hits as proof. Wiki pages guide recall; raw snippets provide evidence.
- Sending a user's topic directly to wiki writing before locating raw sources.
- Forgetting `--exclude-dirs raw,_archive` when building the wiki index.
- Relying on rerank for recall. Rerank only reorders candidates; retrieval and wiki expansion decide what enters the candidate pool.
