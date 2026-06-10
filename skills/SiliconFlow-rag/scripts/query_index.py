#!/usr/bin/env python3
"""Query a local RAG index and print evidence for Codex to answer from."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path

EMBEDDING_API_URL = "https://api.siliconflow.cn/v1/embeddings"
RERANK_API_URL = "https://api.siliconflow.cn/v1/rerank"
DEFAULT_RERANK_MODEL = "Qwen/Qwen3-Reranker-8B"
HERMES_CONFIG_PATH = Path.home() / ".hermes" / "private" / "SiliconFlow-rag" / "config.json"
LEGACY_CONFIG_PATH = Path.home() / ".codex" / "SiliconFlow-rag" / "config.json"
DEFAULT_CONFIG_PATH = HERMES_CONFIG_PATH
QUERY_DEFAULTS = {
    "index_dir": "检索索引",
    "top_k": 6,
    "candidates": 12,
    "embedding_model": "BAAI/bge-m3",
    "rerank_model": DEFAULT_RERANK_MODEL,
    "api_key_env": "SILICONFLOW_API_KEY",
    "api_key_file": None,
    "timeout": 60,
    "expand_context": False,
    "context_window": 1,
    "wiki_index_dir": None,
    "raw_index_dir": None,
    "wiki_top_k": 5,
    "wiki_first": False,
    "multi_query": False,
}
CONFIG_SECTIONS = {"build", "query"}
BUILD_CONFIG_FIELDS = {"md_dir", "model", "chunk_size", "overlap", "batch_size", "sleep"}
QUERY_INT_FIELDS = {"top_k", "candidates", "timeout", "context_window", "wiki_top_k"}


def normalize_config(data: dict, fields: set[str], label: str) -> dict:
    config = {}
    unknown = []
    for key, value in data.items():
        normalized = str(key).replace("-", "_")
        if normalized in fields:
            config[normalized] = value
        else:
            unknown.append(str(key))
    if unknown:
        raise SystemExit(f"Unknown {label} config keys: {', '.join(sorted(unknown))}")
    return config


def top_level_config(data: dict, fields: set[str], label: str) -> dict:
    allowed = fields | CONFIG_SECTIONS | BUILD_CONFIG_FIELDS
    unknown = [str(key) for key in data if str(key).replace("-", "_") not in allowed]
    if unknown:
        raise SystemExit(f"Unknown {label} config keys: {', '.join(sorted(unknown))}")
    return normalize_config({
        key: value
        for key, value in data.items()
        if str(key).replace("-", "_") in fields
    }, fields, label)


def coerce_int(value: object, key: str) -> int:
    if isinstance(value, bool):
        raise SystemExit(f"{key} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"{key} must be an integer") from exc


def load_query_config(config_file: str | None) -> dict:
    if not config_file:
        return {}

    config_path = Path(config_file).expanduser()
    if not config_path.exists():
        raise SystemExit(f"RAG config file not found: {config_path}")
    try:
        data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise SystemExit(f"Could not read RAG config: {config_path}. Reason: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"RAG config must be a JSON object: {config_path}")

    fields = set(QUERY_DEFAULTS)
    config = top_level_config(data, fields, "top-level query")
    section = data.get("query")
    if section is not None:
        if not isinstance(section, dict):
            raise SystemExit("RAG config key 'query' must be an object")
        config.update(normalize_config(section, fields, "query"))
    return config


def apply_query_config(args: argparse.Namespace) -> argparse.Namespace:
    config = load_query_config(args.config)
    for key, default in QUERY_DEFAULTS.items():
        if getattr(args, key) is None:
            setattr(args, key, config.get(key, default))

    for key in QUERY_INT_FIELDS:
        setattr(args, key, coerce_int(getattr(args, key), key))

    return args


def validate_query_args(args: argparse.Namespace) -> None:
    if args.top_k <= 0:
        raise SystemExit("top_k must be greater than 0")
    if args.candidates <= 0:
        raise SystemExit("candidates must be greater than 0")
    if args.candidates < args.top_k:
        raise SystemExit("candidates must be greater than or equal to top_k")
    if args.timeout <= 0:
        raise SystemExit("timeout must be greater than 0")
    if args.wiki_top_k <= 0:
        raise SystemExit("wiki_top_k must be greater than 0")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def mock_embedding(text: str, dimensions: int = 64) -> list[float]:
    vector = [0.0] * dimensions
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dimensions
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vector[idx] += sign
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def bm25_tokenize(text: str) -> list[str]:
    """Simple bi-gram tokenizer for fallback BM25."""
    import re
    text = text.lower()
    text = re.sub(r'[^\w\u4e00-\u9fa5]', ' ', text)
    tokens = [w for w in text.split() if w]
    # Create bi-grams for Chinese characters (simple approximation)
    bigrams = []
    for t in tokens:
        if re.search(r'[\u4e00-\u9fa5]', t) and len(t) > 1:
            for i in range(len(t) - 1):
                bigrams.append(t[i:i+2])
        bigrams.append(t)
    return bigrams

def bm25_score(query_tokens: list[str], doc_tokens: list[str], avgdl: float, idf: dict[str, float], k1: float = 1.5, b: float = 0.75) -> float:
    if not doc_tokens: return 0.0
    from collections import Counter
    doc_len = len(doc_tokens)
    doc_tf = Counter(doc_tokens)
    score = 0.0
    for token in query_tokens:
        if token not in doc_tf: continue
        tf = doc_tf[token]
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * (doc_len / avgdl))
        score += idf.get(token, 0.0) * (numerator / denominator)
    return score

def compute_rrf(rank1: int, rank2: int, k: int = 60) -> float:
    score = 0.0
    if rank1 > 0: score += 1.0 / (k + rank1)
    if rank2 > 0: score += 1.0 / (k + rank2)
    return score


def siliconflow_embedding(text: str, model: str, api_key: str, timeout: int) -> list[float]:
    payload = json.dumps({
        "model": model,
        "input": [text],
        "encoding_format": "float",
        "truncate": "right",
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        EMBEDDING_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"SiliconFlow embedding request failed: HTTP {exc.code} {detail}") from exc
    data = body.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"Unexpected embedding response: {body}")
    return sorted(data, key=lambda item: item.get("index", 0))[0]["embedding"]


def siliconflow_rerank(query: str, documents: list[str], model: str, api_key: str, timeout: int, top_n: int | None = None) -> list[dict]:
    payload_data = {
        "model": model,
        "query": query,
        "documents": documents,
        "return_documents": False,
    }
    if top_n:
        payload_data["top_n"] = top_n
    if model.startswith("Qwen/Qwen3-Reranker"):
        payload_data["instruction"] = "请根据用户问题判断候选材料是否能提供直接证据、概念解释或论证支持。"
    payload = json.dumps(payload_data, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        RERANK_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"SiliconFlow rerank request failed: HTTP {exc.code} {detail}") from exc
    results = body.get("results")
    if not isinstance(results, list):
        raise RuntimeError(f"Unexpected rerank response: {body}")
    return results


def siliconflow_multi_query(question: str, api_key: str, timeout: int) -> list[str]:
    """Generate 3 varied search queries using an LLM."""
    payload = json.dumps({
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Expand the given question into 3 different search queries to improve retrieval recall. Output ONLY the 3 queries, one per line. Do not include numbering, bullets, or intro text."},
            {"role": "user", "content": question}
        ]
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        "https://api.siliconflow.cn/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            queries = [q.strip().strip("-*1234567890. ") for q in content.splitlines() if q.strip()]
            return queries[:3] if queries else [question]
    except Exception:
        return [question]



def infer_query_intent(question: str) -> str:
    q = question.lower()
    if any(word in question for word in ["区别", "对比", "辨析", "关系", "是否等同", "异同", "融合"]):
        return "comparison"
    if any(word in question for word in ["是否成立", "为什么", "如何证明", "支持", "反对", "论证", "根据什么"]):
        return "claim"
    if any(word in question for word in ["是什么", "含义", "定义", "概念"]):
        return "concept"
    if any(word in question for word in ["原文", "出处", "哪一段", "引用", "证据"]):
        return "raw"
    if any(word in question for word in ["论文", "题目", "框架", "综述", "怎么写"]):
        return "synthesis"
    if any(word in q for word in ["compare", "difference", "relationship", "integrate", "integration"]):
        return "comparison"
    if any(word in q for word in ["support", "oppose", "argue", "evidence"]):
        return "claim"
    return "general"


def row_page_type(row: dict) -> str:
    source = str(row.get("source_path", ""))
    if source.startswith("claims/"):
        return "claim"
    if source.startswith("concepts/"):
        return "concept"
    if source.startswith("comparisons/"):
        return "comparison"
    if source.startswith("entities/"):
        return "entity"
    if source.startswith("synthesis/"):
        return "synthesis"
    text = str(row.get("text", ""))
    for line in text.splitlines()[:5]:
        if line.startswith("页面类型："):
            return line.split("：", 1)[1].strip()
    return ""


def semantic_type_boost(intent: str, page_type: str) -> float:
    table = {
        "comparison": {"comparison": 0.18, "claim": 0.08, "concept": 0.06},
        "claim": {"claim": 0.18, "comparison": 0.06, "concept": 0.04},
        "concept": {"concept": 0.18, "comparison": 0.06, "claim": 0.04},
        "synthesis": {"claim": 0.10, "comparison": 0.08, "concept": 0.08, "synthesis": 0.04},
    }
    return table.get(intent, {}).get(page_type, 0.0)

def warn_if_private_config_too_open(config_path: Path) -> None:
    """Warn on POSIX systems if a private key file is group/world-readable."""
    if os.name != "posix":
        return
    try:
        mode = config_path.stat().st_mode
    except OSError:
        return
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        print(
            f"Warning: API key config is readable by group/others: {config_path}. "
            "Consider chmod 600.",
            file=sys.stderr,
        )


def candidate_api_key_paths(api_key_file: str | None) -> list[Path]:
    if api_key_file:
        return [Path(api_key_file).expanduser()]
    return [HERMES_CONFIG_PATH, LEGACY_CONFIG_PATH]


def load_api_key(api_key_env: str, api_key_file: str | None) -> str:
    env_value = os.environ.get(api_key_env)
    if env_value:
        return env_value

    config_path = None
    for path in candidate_api_key_paths(api_key_file):
        if path.exists():
            config_path = path
            break
    if config_path is None:
        return ""
    warn_if_private_config_too_open(config_path)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise SystemExit(f"Could not read API key config: {config_path}. Reason: {exc}") from exc

    if isinstance(data, dict):
        for key in (api_key_env, "siliconflow_api_key", "api_key"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    raise SystemExit(f"API key config found but no usable key was present: {config_path}")


def load_index(index_dir: Path) -> tuple[dict, list[dict]]:
    manifest_path = index_dir / "manifest.json"
    chunks_path = index_dir / "chunks.jsonl"
    embeddings_path = index_dir / "embeddings.jsonl"
    for path in (manifest_path, chunks_path, embeddings_path):
        if not path.exists():
            raise SystemExit(f"Missing index file: {path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks = {row["id"]: row for row in read_jsonl(chunks_path)}
    rows = []
    for emb in read_jsonl(embeddings_path):
        chunk = chunks.get(emb["id"])
        if chunk:
            merged = dict(chunk)
            merged["embedding"] = emb["embedding"]
            rows.append(merged)
    return manifest, rows


def retrieve(args: argparse.Namespace) -> tuple[dict, list[dict], str | None]:
    return retrieve_from_index(args, args.index_dir, args.question, args.top_k, args.candidates)


def retrieve_from_index(args: argparse.Namespace, index_dir_value: str, question: str, top_k: int, candidates_count: int, rerank: bool | None = None) -> tuple[dict, list[dict], str | None]:
    index_dir = Path(index_dir_value).resolve()
    manifest, rows = load_index(index_dir)
    if not rows:
        raise SystemExit(f"Index is empty: {index_dir}")

    mock = bool(manifest.get("mock")) or args.mock
    if mock:
        api_key = ""
        queries = [question]
        query_vectors = [mock_embedding(q) for q in queries]
    else:
        api_key = load_api_key(args.api_key_env, args.api_key_file)
        if not api_key:
            raise SystemExit(
                f"Missing {args.api_key_env}. Set it in the environment or save a local private config at "
                f"{HERMES_CONFIG_PATH} (preferred) or {LEGACY_CONFIG_PATH} (legacy)."
            )
        queries = [question]
        if getattr(args, "multi_query", False):
            expanded = siliconflow_multi_query(question, api_key, args.timeout)
            if expanded:
                queries.extend([q for q in expanded if q != question])
        query_vectors = [siliconflow_embedding(q, manifest.get("embedding_model") or args.embedding_model, api_key, args.timeout) for q in queries]

    intent = infer_query_intent(question)
    is_wiki_index = manifest.get("metadata_mode") == "wiki"
    
    doc_tokens_list = [bm25_tokenize(row["text"]) for row in rows]
    avgdl = sum(len(dt) for dt in doc_tokens_list) / max(1, len(rows))
    from collections import Counter
    df = Counter()
    for dt in doc_tokens_list:
        df.update(set(dt))
    N = len(rows)
    idf = {t: math.log(1 + (N - f + 0.5) / (f + 0.5)) for t, f in df.items()}
    
    item_scores = {}
    for row, doc_tokens in zip(rows, doc_tokens_list):
        item = dict(row)
        item_id = item["id"]
        boost = semantic_type_boost(intent, row_page_type(row)) if is_wiki_index else 0.0
        
        max_vec = 0.0
        for qv in query_vectors:
            sim = cosine(qv, row["embedding"])
            if sim > max_vec: max_vec = sim
            
        max_bm25 = 0.0
        for q in queries:
            qt = bm25_tokenize(q)
            score = bm25_score(qt, doc_tokens, avgdl, idf)
            if score > max_bm25: max_bm25 = score
            
        max_vec += boost
        
        item.pop("embedding", None)
        if boost > 0:
            item["semantic_type_boost"] = boost
            item["query_intent"] = intent
        item_scores[item_id] = {"item": item, "vec": max_vec, "bm25": max_bm25}
        
    vec_ranked = sorted(item_scores.values(), key=lambda x: x["vec"], reverse=True)
    bm25_ranked = sorted(item_scores.values(), key=lambda x: x["bm25"], reverse=True)
    
    for rank, score_dict in enumerate(vec_ranked, start=1):
        score_dict["vec_rank"] = rank
    for rank, score_dict in enumerate(bm25_ranked, start=1):
        score_dict["bm25_rank"] = rank
        
    scored = []
    for score_dict in item_scores.values():
        item = score_dict["item"]
        item["similarity"] = score_dict["vec"]
        item["bm25_score"] = score_dict["bm25"]
        item["rrf_score"] = compute_rrf(score_dict.get("vec_rank", 0), score_dict.get("bm25_rank", 0))
        scored.append(item)
        
    scored.sort(key=lambda item: item["rrf_score"], reverse=True)

    use_rerank = args.rerank if rerank is None else rerank
    rerank_note = None
    candidate_count = candidates_count if use_rerank else top_k
    candidates = scored[:candidate_count]
    final = candidates[:top_k]

    if use_rerank:
        if mock:
            rerank_note = "Rerank skipped because the index/query is using mock embeddings."
        else:
            api_key = load_api_key(args.api_key_env, args.api_key_file)
            if not api_key:
                rerank_note = f"Rerank skipped because {args.api_key_env} or local private config is missing."
            else:
                try:
                    reranked = siliconflow_rerank(question, [item["text"] for item in candidates], args.rerank_model, api_key, args.timeout, top_k)
                    reordered = []
                    for result in reranked:
                        idx = result.get("index")
                        if isinstance(idx, int) and 0 <= idx < len(candidates):
                            item = dict(candidates[idx])
                            item["rerank_score"] = result.get("relevance_score")
                            reordered.append(item)
                    if reordered:
                        final = reordered[:top_k]
                    else:
                        rerank_note = "Rerank returned no usable results; using local similarity order."
                except Exception as exc:  # keep retrieval usable if optional rerank fails
                    rerank_note = f"Rerank failed; using local similarity order. Reason: {exc}"

    # --- Context expansion ---
    if args.expand_context and final:
        lookup: dict[tuple[str, int], dict] = {}
        for row in rows:
            key = (row["source_path"], row["chunk_no"])
            lookup[key] = row

        expanded: list[dict] = []
        seen_ids: set[str] = {item["id"] for item in final}
        window = max(1, args.context_window)

        for item in final:
            # Context before
            for offset in range(window, 0, -1):
                prev_key = (item["source_path"], item["chunk_no"] - offset)
                if prev_key in lookup:
                    ctx = dict(lookup[prev_key])
                    if ctx["id"] not in seen_ids:
                        ctx["is_context"] = True
                        ctx["context_for_chunk"] = item["chunk_no"]
                        ctx.pop("embedding", None)
                        expanded.append(ctx)
                        seen_ids.add(ctx["id"])

            # Main result
            item["is_context"] = False
            expanded.append(item)

            # Context after
            for offset in range(1, window + 1):
                next_key = (item["source_path"], item["chunk_no"] + offset)
                if next_key in lookup:
                    ctx = dict(lookup[next_key])
                    if ctx["id"] not in seen_ids:
                        ctx["is_context"] = True
                        ctx["context_for_chunk"] = item["chunk_no"]
                        ctx.pop("embedding", None)
                        expanded.append(ctx)
                        seen_ids.add(ctx["id"])

        final = expanded

    return manifest, final, rerank_note


def extract_expansion_terms(wiki_hits: list[dict], limit: int = 30) -> list[str]:
    terms: list[str] = []
    labels = [
        "标题：", "命题：", "支撑：", "反对：", "限定：", "依赖：",
        "相关概念：", "相关人物：", "相关辨析：", "来源：", "正文链接：",
    ]
    for item in wiki_hits:
        for line in item.get("text", "").splitlines():
            for label in labels:
                if line.startswith(label):
                    value = line[len(label):].strip()
                    for part in value.replace("，", "、").split("、"):
                        term = part.strip().removeprefix("[[").removesuffix("]]")
                        if term and len(term) <= 80 and term not in terms:
                            terms.append(term)
        if len(terms) >= limit:
            break
    return terms[:limit]


def extract_raw_evidence_paths(wiki_hits: list[dict]) -> list[str]:
    paths: list[str] = []
    for item in wiki_hits:
        text = item.get("text", "")
        for marker in ["证据位置：`", "evidence: `"]:
            start = 0
            while True:
                idx = text.find(marker, start)
                if idx == -1:
                    break
                rest = text[idx + len(marker):]
                raw = rest.split("`", 1)[0].strip()
                if raw and raw not in paths:
                    paths.append(raw)
                start = idx + len(marker)
    return paths


def normalize_evidence_path(path: str) -> str:
    cleaned = path.split(":", 1)[0].strip().removeprefix("./")
    return cleaned.removeprefix("wiki/raw/").removeprefix("raw/")


def add_wiki_evidence_hits(raw_hits: list[dict], raw_rows: list[dict], evidence_paths: list[str]) -> list[dict]:
    if not evidence_paths:
        return raw_hits
    targets = {normalize_evidence_path(path) for path in evidence_paths}
    hits = list(raw_hits)
    seen_ids = {item["id"] for item in hits}
    for row in raw_rows:
        source_path = str(row.get("source_path", ""))
        if source_path in targets and row["id"] not in seen_ids:
            item = dict(row)
            item.pop("embedding", None)
            item["wiki_evidence_boost"] = True
            item.setdefault("similarity", 0.0)
            hits.append(item)
            seen_ids.add(item["id"])
    for item in hits:
        source_path = str(item.get("source_path", ""))
        if source_path in targets:
            item["wiki_evidence_boost"] = True
    return hits


def retrieve_wiki_first(args: argparse.Namespace) -> tuple[dict, list[dict], dict, list[dict], str, str | None]:
    if not args.wiki_index_dir or not args.raw_index_dir:
        raise SystemExit("--wiki-first requires --wiki-index-dir and --raw-index-dir")
    wiki_manifest, wiki_hits, wiki_note = retrieve_from_index(args, args.wiki_index_dir, args.question, args.wiki_top_k, max(args.wiki_top_k, args.candidates), rerank=False)
    terms = extract_expansion_terms(wiki_hits)
    expanded_query = args.question
    if terms:
        expanded_query = args.question + "\n" + "\n".join(terms)
    raw_manifest, raw_hits, raw_note = retrieve_from_index(args, args.raw_index_dir, expanded_query, args.top_k, args.candidates)
    _, raw_rows = load_index(Path(args.raw_index_dir).resolve())
    raw_hits = add_wiki_evidence_hits(raw_hits, raw_rows, extract_raw_evidence_paths(wiki_hits))
    note = "; ".join(note for note in [wiki_note, raw_note] if note) or None
    return wiki_manifest, wiki_hits, raw_manifest, raw_hits, expanded_query, note


def print_wiki_first_evidence(question: str, wiki_manifest: dict, wiki_hits: list[dict], raw_manifest: dict, raw_hits: list[dict], expanded_query: str, note: str | None) -> None:
    print("# Wiki-Aware RAG Evidence")
    print()
    print(f"Question: {question}")
    if note:
        print(f"Note: {note}")
    print()
    print("# Wiki Hits")
    print()
    for rank, item in enumerate(wiki_hits, start=1):
        score = item.get("rerank_score", item.get("similarity"))
        print(f"## Wiki Hit {rank}")
        print(f"- Source: {item['source_path']}")
        print(f"- Chunk: {item['chunk_no']}")
        if isinstance(score, (int, float)):
            print(f"- similarity: {score:.4f}")
        if item.get("semantic_type_boost"):
            print(f"- semantic_type_boost: {item['semantic_type_boost']:.4f}")
        print()
        print(item["text"].strip())
        print()
    print("# Expanded Query")
    print()
    print(expanded_query)
    print()
    print("# Raw Evidence")
    print()
    print_evidence(question, raw_manifest, raw_hits, None)


def print_stats(args: argparse.Namespace) -> None:
    """Print index health statistics."""
    from collections import Counter

    index_dir = Path(args.index_dir).resolve()
    manifest_path = index_dir / "manifest.json"
    chunks_path = index_dir / "chunks.jsonl"
    embeddings_path = index_dir / "embeddings.jsonl"

    if not manifest_path.exists():
        raise SystemExit(f"Index not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks = read_jsonl(chunks_path) if chunks_path.exists() else []
    embeddings = read_jsonl(embeddings_path) if embeddings_path.exists() else []

    # Per-file chunk counts
    file_counts: dict[str, int] = {}
    duplicate_chunk_ids: set[str] = set()
    seen_chunk_ids: set[str] = set()
    missing_text = 0
    semantic_metadata_count = 0
    embedding_text_count = 0
    for c in chunks:
        sp = c.get("source_path", "?")
        file_counts[sp] = file_counts.get(sp, 0) + 1
        chunk_id = str(c.get("id", ""))
        if chunk_id in seen_chunk_ids:
            duplicate_chunk_ids.add(chunk_id)
        if chunk_id:
            seen_chunk_ids.add(chunk_id)
        if not str(c.get("text", "")).strip():
            missing_text += 1
        if c.get("semantic_metadata"):
            semantic_metadata_count += 1
        if c.get("embedding_text"):
            embedding_text_count += 1

    embedding_ids = [str(e.get("id", "")) for e in embeddings if e.get("id")]
    embedding_id_set = set(embedding_ids)
    duplicate_embedding_ids = {eid for eid, count in Counter(embedding_ids).items() if count > 1}
    chunk_ids = {str(c.get("id", "")) for c in chunks if c.get("id")}
    missing_embeddings = sorted(chunk_ids - embedding_id_set)
    orphan_embeddings = sorted(embedding_id_set - chunk_ids)
    manifest_chunk_count = manifest.get("chunk_count")
    manifest_file_count = manifest.get("file_count")
    file_hashes = manifest.get("file_hashes") or {}
    top_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    health_issues: list[str] = []
    if not chunks_path.exists():
        health_issues.append(f"missing chunks file: {chunks_path}")
    if not embeddings_path.exists():
        health_issues.append(f"missing embeddings file: {embeddings_path}")
    if manifest_chunk_count != len(chunks):
        health_issues.append(f"manifest chunk_count={manifest_chunk_count} but chunks.jsonl has {len(chunks)}")
    if embeddings and len(embeddings) != len(chunks):
        health_issues.append(f"embeddings.jsonl has {len(embeddings)} rows but chunks.jsonl has {len(chunks)}")
    if manifest_file_count != len(file_counts):
        health_issues.append(f"manifest file_count={manifest_file_count} but chunks cover {len(file_counts)} source files")
    if file_hashes and len(file_hashes) != manifest_file_count:
        health_issues.append(f"file_hashes tracks {len(file_hashes)} files but manifest file_count={manifest_file_count}")
    if missing_embeddings:
        health_issues.append(f"{len(missing_embeddings)} chunk id(s) missing embeddings")
    if orphan_embeddings:
        health_issues.append(f"{len(orphan_embeddings)} embedding id(s) have no chunk")
    if duplicate_chunk_ids:
        health_issues.append(f"{len(duplicate_chunk_ids)} duplicate chunk id(s)")
    if duplicate_embedding_ids:
        health_issues.append(f"{len(duplicate_embedding_ids)} duplicate embedding id(s)")
    if missing_text:
        health_issues.append(f"{missing_text} chunk(s) have empty text")

    print("# Index Statistics")
    print()
    print(f"  Files:           {manifest_file_count if manifest_file_count is not None else '?'}")
    print(f"  Chunks:          {manifest_chunk_count if manifest_chunk_count is not None else len(chunks)}")
    print(f"  Embeddings:      {len(embeddings)}")
    print(f"  Embedding:       {manifest.get('embedding_model', '?')}")
    print(f"  Built:           {manifest.get('created_at', '?')}")
    print(f"  Format:          v{manifest.get('format_version', '?')}")
    print(f"  Mock:            {manifest.get('mock', False)}")
    print(f"  Metadata mode:   {manifest.get('metadata_mode', '?')}")
    print(f"  Include dirs:    {manifest.get('include_dirs') or 'none'}")
    print(f"  Exclude dirs:    {manifest.get('exclude_dirs') or 'none'}")
    print(f"  Chunk size:      {manifest.get('chunk_size', '?')} chars")
    print(f"  Overlap:         {manifest.get('overlap', '?')} chars")
    if file_counts:
        avg = sum(file_counts.values()) / len(file_counts)
        print(f"  Avg chunks/file: {avg:.1f}")
    if semantic_metadata_count or embedding_text_count:
        print(f"  Semantic tags:   {semantic_metadata_count} chunk(s)")
        print(f"  Embedding text:  {embedding_text_count} chunk(s)")
    print()

    if top_files:
        print("## Top Files by Chunk Count")
        for path, count in top_files:
            print(f"  {count:4d}  {path}")

    print()
    print("## Health")
    if health_issues:
        print("  Status: WARN")
        for issue in health_issues:
            print(f"  - {issue}")
    else:
        print("  Status: OK")

    # Hash coverage
    if file_hashes:
        print()
        print(f"  Files tracked by hash: {len(file_hashes)}")
    else:
        print()
        print("  (No file_hashes — index was built with format v1; rebuild for incremental support)")


def print_evidence(question: str, manifest: dict, results: list[dict], rerank_note: str | None) -> None:
    print("# RAG Evidence")
    print()
    print(f"Question: {question}")
    print(f"Index: {manifest.get('index_dir', '')}")
    print(f"Embedding model: {manifest.get('embedding_model', '')}")
    if rerank_note:
        print(f"Note: {rerank_note}")
    print()
    if not results:
        print("No evidence found.")
        return
    for rank, item in enumerate(results, start=1):
        is_ctx = item.get("is_context")
        ctx_for = item.get("context_for_chunk")
        score = item.get("rerank_score", item.get("similarity"))
        score_name = "rerank" if "rerank_score" in item else "similarity"

        if is_ctx:
            print(f"## Evidence {rank} [context for chunk {ctx_for}]")
            print(f"- Source: {item['source_path']}")
            print(f"- Chunk: {item['chunk_no']}")
            print()
        else:
            print(f"## Evidence {rank}")
            print(f"- Source: {item['source_path']}")
            print(f"- Chunk: {item['chunk_no']}")
            if item.get("wiki_evidence_boost"):
                print("- wiki_evidence_boost: true")
            if item.get("semantic_type_boost"):
                print(f"- semantic_type_boost: {item['semantic_type_boost']:.4f}")
            if item.get("semantic_metadata"):
                md = item["semantic_metadata"]
                tags = []
                for key in ["concepts", "claims", "comparisons"]:
                    if md.get(key):
                        tags.append(f"{key}={'/'.join(md[key])}")
                if tags:
                    print("- retrieval_tags: " + "; ".join(tags))
            print(f"- {score_name}: {score:.4f}" if isinstance(score, (int, float)) else f"- {score_name}: {score}")
            print()
        print(item["text"].strip())
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query a local RAG index and print evidence.")
    parser.add_argument("--config", default=None, help="Optional JSON config file for query parameters")
    parser.add_argument("--index-dir", default=None, help="Index directory")
    parser.add_argument("--wiki-index-dir", default=None, help="Wiki-layer index directory for --wiki-first")
    parser.add_argument("--raw-index-dir", default=None, help="Raw evidence index directory for --wiki-first")
    parser.add_argument("--wiki-first", action="store_true", default=None, help="Retrieve wiki hits first, expand the query, then retrieve raw evidence")
    parser.add_argument("--wiki-top-k", type=int, default=None, help="Number of wiki hits to use for query expansion")
    parser.add_argument("--question", default=None, help="Question to retrieve evidence for (omit with --stats)")
    parser.add_argument("--top-k", type=int, default=None, help="Number of evidence snippets to output")
    parser.add_argument("--candidates", type=int, default=None, help="Candidate count before optional rerank")
    parser.add_argument("--embedding-model", default=None, help="Fallback embedding model if manifest lacks one")
    parser.add_argument("--rerank", action="store_true", help="Use optional SiliconFlow reranking")
    parser.add_argument("--rerank-model", default=None, help="SiliconFlow rerank model")
    parser.add_argument("--api-key-env", default=None, help="Environment variable containing the API key")
    parser.add_argument("--api-key-file", default=None, help=f"Local private API key config file; default: {DEFAULT_CONFIG_PATH}")
    parser.add_argument("--timeout", type=int, default=None, help="HTTP timeout in seconds")
    parser.add_argument("--mock", action="store_true", help="Use mock query embedding for tests")
    parser.add_argument("--expand-context", action="store_true", default=None, help="Include adjacent chunks from the same source for each result")
    parser.add_argument("--context-window", type=int, default=None, help="Number of adjacent chunks on each side (default: 1)")
    parser.add_argument("--multi-query", action="store_true", default=None, help="Use LLM to rewrite question into multiple search queries (default: false)")
    parser.add_argument("--no-multi-query", action="store_false", dest="multi_query", help="Disable LLM query rewrite")
    parser.add_argument("--stats", action="store_true", help="Print index statistics instead of querying")
    return apply_query_config(parser.parse_args())


if __name__ == "__main__":
    parsed = parse_args()
    if parsed.stats:
        print_stats(parsed)
    elif parsed.question and parsed.wiki_first:
        validate_query_args(parsed)
        wiki_manifest_data, wiki_hits, raw_manifest_data, raw_evidence, expanded_query, note = retrieve_wiki_first(parsed)
        print_wiki_first_evidence(parsed.question, wiki_manifest_data, wiki_hits, raw_manifest_data, raw_evidence, expanded_query, note)
    elif parsed.question:
        validate_query_args(parsed)
        manifest_data, evidence, note = retrieve(parsed)
        print_evidence(parsed.question, manifest_data, evidence, note)
    else:
        print("Usage: query_index.py --index-dir <dir> --question \"...\" [options]")
        print("       query_index.py --index-dir <dir> --stats")
        raise SystemExit(1)
