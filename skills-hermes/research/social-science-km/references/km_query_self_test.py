#!/usr/bin/env python3
"""Self-test for the social-science-km km_query.py reference script."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
KM_QUERY = SCRIPT_DIR / "km_query.py"


def load_module():
    spec = importlib.util.spec_from_file_location("km_query_ref", KM_QUERY)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load {KM_QUERY}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_manifest(index_dir: Path, file_hashes: dict[str, str], metadata_mode: str) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / "manifest.json").write_text(
        json.dumps({"file_hashes": file_hashes, "format_version": 2, "metadata_mode": metadata_mode}, ensure_ascii=False),
        encoding="utf-8",
    )
    (index_dir / "chunks.jsonl").write_text("", encoding="utf-8")
    (index_dir / "embeddings.jsonl").write_text("", encoding="utf-8")


def run_py(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, encoding="utf-8", errors="replace")


def main() -> None:
    km = load_module()
    temp_dir = Path(tempfile.mkdtemp(prefix="km-query-test-"))
    try:
        wiki = temp_dir / "wiki"
        raw = wiki / "raw"
        claims = wiki / "claims"
        concepts = wiki / "concepts"
        raw.mkdir(parents=True)
        claims.mkdir(parents=True)
        concepts.mkdir(parents=True)

        (raw / "care.md").write_text("# Care\n\nraw evidence", encoding="utf-8")
        (claims / "claim.md").write_text("---\ntype: claim\n---\n# Claim", encoding="utf-8")
        (concepts / "concept.md").write_text("---\ntype: concept\n---\n# Concept", encoding="utf-8")

        raw_hashes = km.compute_hashes(raw)
        wiki_hashes = km.compute_hashes(wiki, include_dirs=km.WIKI_INDEX_SOURCE_DIRS, exclude_dirs={"raw", "_archive"})
        write_manifest(temp_dir / "检索索引" / "raw", raw_hashes, "enriched_raw")
        write_manifest(temp_dir / "检索索引" / "wiki", wiki_hashes, "wiki")

        status = km.check_staleness(temp_dir)
        if status.stale:
            raise SystemExit(f"Expected fresh indexes, got stale: {status.message}")

        (raw / "new.md").write_text("# New\n\nnew raw evidence", encoding="utf-8")
        status = km.check_staleness(temp_dir)
        if not status.stale or "raw" not in status.message or "新增/改动" not in status.message:
            raise SystemExit(f"Expected raw new/changed stale message, got: {status}")

        raw_mode = km.choose_mode("这段话的原文出处在哪里？", raw_only=False, deep=False, project_root=temp_dir)
        if raw_mode != "raw":
            raise SystemExit(f"Expected raw mode for source lookup, got: {raw_mode}")

        wiki_mode = km.choose_mode("孝与仁的关系是什么？", raw_only=False, deep=False, project_root=temp_dir)
        if wiki_mode != "wiki":
            raise SystemExit(f"Expected wiki mode for conceptual query, got: {wiki_mode}")

        cmd = km.build_query_command(
            project_root=temp_dir,
            query_script=Path("/tmp/query_index.py"),
            question="孝与仁的关系是什么？",
            mode="wiki",
            expand_context=True,
            rerank=False,
            multi_query=False,
            candidates=None,
        )
        joined = " ".join(cmd)
        for marker in ["--wiki-first", "--wiki-index-dir", "检索索引/wiki", "--raw-index-dir", "检索索引/raw", "--expand-context"]:
            if marker not in joined:
                raise SystemExit(f"Wiki command missing {marker}: {joined}")

        result = run_py([sys.executable, str(KM_QUERY), "--help"], SCRIPT_DIR)
        if result.returncode != 0 or "--deep" not in result.stdout or "--raw-only" not in result.stdout:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            raise SystemExit("CLI help test failed")

        print("km_query self-test passed")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
