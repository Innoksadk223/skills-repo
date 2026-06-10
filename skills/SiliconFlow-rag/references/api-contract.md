# API Contract

SiliconFlow calls must keep the expected request shapes. Do not send wiki graph objects, metadata dictionaries, or raw file paths as API-specific parameters.

## Embedding

Endpoint: `POST https://api.siliconflow.cn/v1/embeddings`

```json
{
  "model": "BAAI/bge-m3",
  "input": ["chunk text"],
  "encoding_format": "float",
  "truncate": "right"
}
```

## Rerank

Endpoint: `POST https://api.siliconflow.cn/v1/rerank`

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

## Multi-query

Endpoint: `POST https://api.siliconflow.cn/v1/chat/completions`

Multi-query is off by default. Use `--multi-query` only when recall is weak or the user's wording likely differs from corpus terminology.

```json
{
  "model": "Qwen/Qwen2.5-7B-Instruct",
  "messages": [
    {"role": "system", "content": "Expand the given question into 3 different search queries..."},
    {"role": "user", "content": "用户问题"}
  ]
}
```

## Privacy surface

- Indexing sends chunks to embeddings.
- Querying sends the question to embeddings.
- `--multi-query` sends the question to chat completions.
- `--rerank` sends candidate snippets to rerank.
