#!/usr/bin/env python3
"""Build a local RAG index from Markdown files using SiliconFlow embeddings."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://api.siliconflow.cn/v1/embeddings"
DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_CONFIG_PATH = Path.home() / ".codex" / "SiliconFlow-rag" / "config.json"
BUILD_DEFAULTS = {
    "md_dir": "raw",
    "index_dir": "检索索引",
    "model": DEFAULT_MODEL,
    "api_key_env": "SILICONFLOW_API_KEY",
    "api_key_file": None,
    "chunk_size": 1200,
    "overlap": 200,
    "batch_size": 16,
    "timeout": 60,
    "sleep": 0.0,
}
CONFIG_SECTIONS = {"build", "query"}
QUERY_CONFIG_FIELDS = {"top_k", "candidates", "embedding_model", "rerank_model"}
BUILD_INT_FIELDS = {"chunk_size", "overlap", "batch_size", "timeout"}
BUILD_FLOAT_FIELDS = {"sleep"}
SKIP_NAMES = {
    "_conversion_failures.md",
    "_conversion_manifest.md",
    "_主题索引.md",
}


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
    allowed = fields | CONFIG_SECTIONS | QUERY_CONFIG_FIELDS
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


def coerce_float(value: object, key: str) -> float:
    if isinstance(value, bool):
        raise SystemExit(f"{key} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"{key} must be a number") from exc


def load_build_config(config_file: str | None) -> dict:
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

    fields = set(BUILD_DEFAULTS)
    config = top_level_config(data, fields, "top-level build")
    section = data.get("build")
    if section is not None:
        if not isinstance(section, dict):
            raise SystemExit("RAG config key 'build' must be an object")
        config.update(normalize_config(section, fields, "build"))
    return config


def apply_build_config(args: argparse.Namespace) -> argparse.Namespace:
    config = load_build_config(args.config)
    for key, default in BUILD_DEFAULTS.items():
        if getattr(args, key) is None:
            setattr(args, key, config.get(key, default))

    for key in BUILD_INT_FIELDS:
        setattr(args, key, coerce_int(getattr(args, key), key))
    for key in BUILD_FLOAT_FIELDS:
        setattr(args, key, coerce_float(getattr(args, key), key))

    if args.chunk_size <= 0:
        raise SystemExit("chunk_size must be greater than 0")
    if args.overlap < 0:
        raise SystemExit("overlap must be 0 or greater")
    if args.overlap >= args.chunk_size:
        raise SystemExit("overlap must be smaller than chunk_size")
    if args.batch_size <= 0:
        raise SystemExit("batch_size must be greater than 0")
    if args.timeout <= 0:
        raise SystemExit("timeout must be greater than 0")
    if args.sleep < 0:
        raise SystemExit("sleep must be 0 or greater")
    return args


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")


def stable_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def list_markdown_files(md_dir: Path) -> list[Path]:
    files = []
    for path in md_dir.rglob("*.md"):
        if path.name in SKIP_NAMES:
            continue
        if any(part.startswith(".") for part in path.relative_to(md_dir).parts):
            continue
        files.append(path)
    return sorted(files)


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[tuple[int, int, str]]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            newline = normalized.rfind("\n\n", start, end)
            if newline > start + chunk_size // 2:
                end = newline
        snippet = normalized[start:end].strip()
        if snippet:
            chunks.append((start, end, snippet))
        if end >= length:
            break
        start = max(0, end - overlap)
    return chunks


def mock_embedding(text: str, dimensions: int = 64) -> list[float]:
    vector = [0.0] * dimensions
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dimensions
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vector[idx] += sign
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def siliconflow_embeddings(texts: list[str], model: str, api_key: str, timeout: int) -> list[list[float]]:
    payload = json.dumps({"model": model, "input": texts}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
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
    except urllib.error.URLError as exc:
        raise RuntimeError(f"SiliconFlow embedding request failed: {exc.reason}") from exc

    data = body.get("data")
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected embedding response: {body}")
    ordered = sorted(data, key=lambda item: item.get("index", 0))
    return [item["embedding"] for item in ordered]


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


def embed_batches(texts: list[str], args: argparse.Namespace) -> list[list[float]]:
    if args.mock:
        return [mock_embedding(text) for text in texts]

    api_key = load_api_key(args.api_key_env, args.api_key_file)
    if not api_key:
        raise SystemExit(
            f"Missing {args.api_key_env}. Set it in the environment or save a local private config at "
            f"{DEFAULT_CONFIG_PATH}, or use --mock for tests."
        )

    embeddings: list[list[float]] = []
    total = len(texts)
    for start in range(0, total, args.batch_size):
        batch = texts[start:start + args.batch_size]
        embeddings.extend(siliconflow_embeddings(batch, args.model, api_key, args.timeout))
        if args.sleep and start + args.batch_size < total:
            time.sleep(args.sleep)
    return embeddings


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def build_index(args: argparse.Namespace) -> None:
    md_dir = Path(args.md_dir).resolve()
    index_dir = Path(args.index_dir).resolve()
    if not md_dir.is_dir():
        raise SystemExit(f"Markdown directory not found: {md_dir}")

    files = list_markdown_files(md_dir)
    chunks: list[dict] = []
    for file_path in files:
        rel_path = file_path.relative_to(md_dir).as_posix()
        text = read_text(file_path)
        for chunk_no, (start, end, snippet) in enumerate(chunk_text(text, args.chunk_size, args.overlap), start=1):
            chunk_id = stable_id(f"{rel_path}\n{chunk_no}\n{snippet}")
            chunks.append({
                "id": chunk_id,
                "source_path": rel_path,
                "chunk_no": chunk_no,
                "char_start": start,
                "char_end": end,
                "text": snippet,
            })

    if not chunks:
        raise SystemExit(f"No Markdown content found under {md_dir}")

    vectors = embed_batches([chunk["text"] for chunk in chunks], args)
    if len(vectors) != len(chunks):
        raise RuntimeError("Embedding count does not match chunk count")

    index_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(index_dir / "chunks.jsonl", chunks)
    write_jsonl(index_dir / "embeddings.jsonl", [
        {"id": chunk["id"], "embedding": vector}
        for chunk, vector in zip(chunks, vectors)
    ])
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "md_dir": str(md_dir),
        "index_dir": str(index_dir),
        "embedding_model": args.model,
        "api_key_env": args.api_key_env,
        "mock": bool(args.mock),
        "chunk_size": args.chunk_size,
        "overlap": args.overlap,
        "file_count": len(files),
        "chunk_count": len(chunks),
        "format_version": 1,
    }
    (index_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexed {len(chunks)} chunks from {len(files)} files into {index_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local RAG index from Markdown files.")
    parser.add_argument("--config", default=None, help="Optional JSON config file for build parameters")
    parser.add_argument("--md-dir", default=None, help="Markdown source directory")
    parser.add_argument("--index-dir", default=None, help="Index output directory")
    parser.add_argument("--model", default=None, help="SiliconFlow embedding model")
    parser.add_argument("--api-key-env", default=None, help="Environment variable containing the API key")
    parser.add_argument("--api-key-file", default=None, help=f"Local private API key config file; default: {DEFAULT_CONFIG_PATH}")
    parser.add_argument("--chunk-size", type=int, default=None, help="Chunk size in characters")
    parser.add_argument("--overlap", type=int, default=None, help="Chunk overlap in characters")
    parser.add_argument("--batch-size", type=int, default=None, help="Embedding request batch size")
    parser.add_argument("--timeout", type=int, default=None, help="HTTP timeout in seconds")
    parser.add_argument("--sleep", type=float, default=None, help="Sleep between embedding batches")
    parser.add_argument("--mock", action="store_true", help="Use deterministic local mock embeddings for tests")
    return apply_build_config(parser.parse_args())


if __name__ == "__main__":
    build_index(parse_args())
