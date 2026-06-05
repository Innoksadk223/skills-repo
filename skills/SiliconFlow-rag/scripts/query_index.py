#!/usr/bin/env python3
"""Query a local RAG index and print evidence for Codex to answer from."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import urllib.error
import urllib.request
from pathlib import Path

EMBEDDING_API_URL = "https://api.siliconflow.cn/v1/embeddings"
RERANK_API_URL = "https://api.siliconflow.cn/v1/rerank"
DEFAULT_RERANK_MODEL = "Qwen/Qwen3-Reranker-8B"
DEFAULT_CONFIG_PATH = Path.home() / ".codex" / "SiliconFlow-rag" / "config.json"
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


def load_api_key(api_key_env: str, api_key_file: str | None) -> str:
    env_value = os.environ.get(api_key_env)
    if env_value:
        return env_value

    config_path = Path(api_key_file).expanduser() if api_key_file else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return ""
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
        query_vector = mock_embedding(question)
    else:
        api_key = load_api_key(args.api_key_env, args.api_key_file)
        if not api_key:
            raise SystemExit(
                f"Missing {args.api_key_env}. Set it in the environment or save a local private config at "
                f"{DEFAULT_CONFIG_PATH}."
            )
        query_vector = siliconflow_embedding(question, manifest.get("embedding_model") or args.embedding_model, api_key, args.timeout)

    scored = []
    for row in rows:
        item = dict(row)
        item["similarity"] = cosine(query_vector, row["embedding"])
        item.pop("embedding", None)
        scored.append(item)
    scored.sort(key=lambda item: item["similarity"], reverse=True)

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
                        term = part.strip()
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
    return cleaned.removeprefix("raw/")


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

    if not manifest_path.exists():
        raise SystemExit(f"Index not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks = read_jsonl(chunks_path) if chunks_path.exists() else []

    # Per-file chunk counts
    file_counts: dict[str, int] = {}
    for c in chunks:
        sp = c.get("source_path", "?")
        file_counts[sp] = file_counts.get(sp, 0) + 1

    top_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    print("# Index Statistics")
    print()
    print(f"  Files:         {manifest.get('file_count', '?')}")
    print(f"  Chunks:        {manifest.get('chunk_count', len(chunks))}")
    print(f"  Embedding:     {manifest.get('embedding_model', '?')}")
    print(f"  Built:         {manifest.get('created_at', '?')}")
    print(f"  Format:        v{manifest.get('format_version', '?')}")
    print(f"  Mock:          {manifest.get('mock', False)}")
    print(f"  Chunk size:    {manifest.get('chunk_size', '?')} chars")
    print(f"  Overlap:       {manifest.get('overlap', '?')} chars")
    if file_counts:
        avg = sum(file_counts.values()) / len(file_counts)
        print(f"  Avg chunks/file: {avg:.1f}")
    print()

    if top_files:
        print("## Top Files by Chunk Count")
        for path, count in top_files:
            print(f"  {count:4d}  {path}")

    # Hash coverage
    hashes = manifest.get("file_hashes")
    if hashes:
        print()
        print(f"  Files tracked by hash: {len(hashes)}")
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
