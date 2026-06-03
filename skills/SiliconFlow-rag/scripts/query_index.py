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
}
CONFIG_SECTIONS = {"build", "query"}
BUILD_CONFIG_FIELDS = {"md_dir", "model", "chunk_size", "overlap", "batch_size", "sleep"}
QUERY_INT_FIELDS = {"top_k", "candidates", "timeout"}


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

    if args.top_k <= 0:
        raise SystemExit("top_k must be greater than 0")
    if args.candidates <= 0:
        raise SystemExit("candidates must be greater than 0")
    if args.candidates < args.top_k:
        raise SystemExit("candidates must be greater than or equal to top_k")
    if args.timeout <= 0:
        raise SystemExit("timeout must be greater than 0")
    return args


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
    payload = json.dumps({"model": model, "input": [text]}, ensure_ascii=False).encode("utf-8")
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


def siliconflow_rerank(query: str, documents: list[str], model: str, api_key: str, timeout: int) -> list[dict]:
    payload = json.dumps({
        "model": model,
        "query": query,
        "documents": documents,
        "return_documents": False,
    }, ensure_ascii=False).encode("utf-8")
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
    index_dir = Path(args.index_dir).resolve()
    manifest, rows = load_index(index_dir)
    if not rows:
        raise SystemExit(f"Index is empty: {index_dir}")

    mock = bool(manifest.get("mock")) or args.mock
    if mock:
        query_vector = mock_embedding(args.question)
    else:
        api_key = load_api_key(args.api_key_env, args.api_key_file)
        if not api_key:
            raise SystemExit(
                f"Missing {args.api_key_env}. Set it in the environment or save a local private config at "
                f"{DEFAULT_CONFIG_PATH}."
            )
        query_vector = siliconflow_embedding(args.question, manifest.get("embedding_model") or args.embedding_model, api_key, args.timeout)

    scored = []
    for row in rows:
        item = dict(row)
        item["similarity"] = cosine(query_vector, row["embedding"])
        item.pop("embedding", None)
        scored.append(item)
    scored.sort(key=lambda item: item["similarity"], reverse=True)

    rerank_note = None
    candidate_count = args.candidates if args.rerank else args.top_k
    candidates = scored[:candidate_count]
    final = candidates[:args.top_k]

    if args.rerank:
        if mock:
            rerank_note = "Rerank skipped because the index/query is using mock embeddings."
        else:
            api_key = load_api_key(args.api_key_env, args.api_key_file)
            if not api_key:
                rerank_note = f"Rerank skipped because {args.api_key_env} or local private config is missing."
            else:
                try:
                    reranked = siliconflow_rerank(args.question, [item["text"] for item in candidates], args.rerank_model, api_key, args.timeout)
                    reordered = []
                    for result in reranked:
                        idx = result.get("index")
                        if isinstance(idx, int) and 0 <= idx < len(candidates):
                            item = dict(candidates[idx])
                            item["rerank_score"] = result.get("relevance_score")
                            reordered.append(item)
                    if reordered:
                        final = reordered[:args.top_k]
                    else:
                        rerank_note = "Rerank returned no usable results; using local similarity order."
                except Exception as exc:  # keep retrieval usable if optional rerank fails
                    rerank_note = f"Rerank failed; using local similarity order. Reason: {exc}"

    return manifest, final, rerank_note


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
        score = item.get("rerank_score", item.get("similarity"))
        score_name = "rerank" if "rerank_score" in item else "similarity"
        print(f"## Evidence {rank}")
        print(f"- Source: {item['source_path']}")
        print(f"- Chunk: {item['chunk_no']}")
        print(f"- {score_name}: {score:.4f}" if isinstance(score, (int, float)) else f"- {score_name}: {score}")
        print()
        print(item["text"].strip())
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query a local RAG index and print evidence.")
    parser.add_argument("--config", default=None, help="Optional JSON config file for query parameters")
    parser.add_argument("--index-dir", default=None, help="Index directory")
    parser.add_argument("--question", required=True, help="Question to retrieve evidence for")
    parser.add_argument("--top-k", type=int, default=None, help="Number of evidence snippets to output")
    parser.add_argument("--candidates", type=int, default=None, help="Candidate count before optional rerank")
    parser.add_argument("--embedding-model", default=None, help="Fallback embedding model if manifest lacks one")
    parser.add_argument("--rerank", action="store_true", help="Use optional SiliconFlow reranking")
    parser.add_argument("--rerank-model", default=None, help="SiliconFlow rerank model")
    parser.add_argument("--api-key-env", default=None, help="Environment variable containing the API key")
    parser.add_argument("--api-key-file", default=None, help=f"Local private API key config file; default: {DEFAULT_CONFIG_PATH}")
    parser.add_argument("--timeout", type=int, default=None, help="HTTP timeout in seconds")
    parser.add_argument("--mock", action="store_true", help="Use mock query embedding for tests")
    return apply_query_config(parser.parse_args())


if __name__ == "__main__":
    parsed = parse_args()
    manifest_data, evidence, note = retrieve(parsed)
    print_evidence(parsed.question, manifest_data, evidence, note)
