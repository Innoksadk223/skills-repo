#!/usr/bin/env python3
"""Self-test for SiliconFlow-rag scripts."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[3]
BUILD = SCRIPT_DIR / "build_index.py"
QUERY = SCRIPT_DIR / "query_index.py"


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def run_expect_failure(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode == 0:
        print(result.stdout)
        raise SystemExit("Command unexpectedly succeeded: " + " ".join(command))
    return result


def main() -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="SiliconFlow-rag-test-"))
    try:
        md_dir = temp_dir / "资料md"
        index_dir = temp_dir / "检索索引"
        (md_dir / "urban-studies").mkdir(parents=True)
        (md_dir / "methods").mkdir(parents=True)
        (md_dir / "urban-studies" / "housing.md").write_text(
            "# Housing Inequality\n\nHousing inequality is shaped by rent, migration, welfare policy, and urban governance.\n",
            encoding="utf-8",
        )
        (md_dir / "methods" / "interview.md").write_text(
            "# Interview Methods\n\nSemi-structured interviews help explain how residents interpret policy and daily life.\n",
            encoding="utf-8",
        )
        config_path = temp_dir / "rag_config.json"
        config_path.write_text(
            """{
  "build": {
    "chunk_size": 80,
    "overlap": 10,
    "batch_size": 2
  },
  "query": {
    "top_k": 2,
    "candidates": 3
  }
}
""",
            encoding="utf-8",
        )

        run([
            sys.executable,
            str(BUILD),
            "--config",
            str(config_path),
            "--md-dir",
            str(md_dir),
            "--index-dir",
            str(index_dir),
            "--mock",
        ], ROOT)

        result = run([
            sys.executable,
            str(QUERY),
            "--config",
            str(config_path),
            "--index-dir",
            str(index_dir),
            "--question",
            "What shapes housing inequality?",
            "--mock",
        ], ROOT)

        output = result.stdout
        required = ["# RAG Evidence", "Source:", "similarity", "Housing"]
        missing = [text for text in required if text not in output]
        if missing:
            print(output)
            raise SystemExit(f"Self-test failed; missing output markers: {missing}")

        # --- Query config default: multi-query should stay off unless explicitly enabled ---
        defaults_config_path = temp_dir / "rag_defaults_config.json"
        defaults_config_path.write_text(
            """{
  "build": {
    "chunk_size": 80,
    "overlap": 10,
    "batch_size": 2
  },
  "query": {
    "top_k": 2,
    "candidates": 3
  }
}
""",
            encoding="utf-8",
        )
        result = run([
            sys.executable,
            str(QUERY),
            "--config",
            str(defaults_config_path),
            "--index-dir",
            str(index_dir),
            "--question",
            "What shapes housing inequality?",
            "--mock",
        ], ROOT)
        if "# RAG Evidence" not in result.stdout:
            print(result.stdout)
            raise SystemExit("Default multi-query smoke test failed")

        # --- Unknown config keys should fail loudly ---
        bad_config_path = temp_dir / "rag_bad_config.json"
        bad_config_path.write_text('{"query": {"not_a_valid_key": true}}', encoding="utf-8")
        result = run_expect_failure([
            sys.executable,
            str(QUERY),
            "--config",
            str(bad_config_path),
            "--index-dir",
            str(index_dir),
            "--question",
            "What shapes housing inequality?",
            "--mock",
        ], ROOT)
        if "Unknown query config keys" not in (result.stdout + result.stderr):
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            raise SystemExit("Unknown config key test failed")

        # --- Incremental test: add a new file ---
        (md_dir / "urban-studies" / "rent.md").write_text(
            "# Rent Control\n\nRent control policies limit how much landlords can increase rent each year.\n",
            encoding="utf-8",
        )

        result = run([
            sys.executable,
            str(BUILD),
            "--config",
            str(config_path),
            "--md-dir",
            str(md_dir),
            "--index-dir",
            str(index_dir),
            "--mock",
            "--incremental",
        ], ROOT)

        inc_output = result.stdout
        if "Index updated" not in inc_output:
            print(inc_output)
            raise SystemExit("Incremental test failed: expected 'Index updated' in output")

        # Verify manifest has file_hashes and format_version 2
        import json
        manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("format_version") != 2:
            raise SystemExit(f"Incremental test failed: expected format_version 2, got {manifest.get('format_version')}")
        if "file_hashes" not in manifest:
            raise SystemExit("Incremental test failed: manifest missing file_hashes")
        if len(manifest["file_hashes"]) != 3:
            raise SystemExit(f"Incremental test failed: expected 3 file hashes, got {len(manifest['file_hashes'])}")

        # --- No-op incremental: run again, should report up to date ---
        result = run([
            sys.executable,
            str(BUILD),
            "--config",
            str(config_path),
            "--md-dir",
            str(md_dir),
            "--index-dir",
            str(index_dir),
            "--mock",
            "--incremental",
        ], ROOT)

        if "up to date" not in result.stdout:
            print(result.stdout)
            raise SystemExit("Incremental no-op test failed: expected 'up to date' in output")

        # --- Incremental setting changes should force full rebuild ---
        result = run([
            sys.executable,
            str(BUILD),
            "--config",
            str(config_path),
            "--md-dir",
            str(md_dir),
            "--index-dir",
            str(index_dir),
            "--mock",
            "--incremental",
            "--chunk-size",
            "120",
        ], ROOT)
        if "Incremental settings changed; falling back to full build" not in result.stdout:
            print(result.stdout)
            raise SystemExit("Incremental settings-change test failed: expected full rebuild fallback")

        # Restore original chunk settings for later tests.
        run([
            sys.executable,
            str(BUILD),
            "--config",
            str(config_path),
            "--md-dir",
            str(md_dir),
            "--index-dir",
            str(index_dir),
            "--mock",
        ], ROOT)

        # --- Context expansion test ---
        result = run([
            sys.executable,
            str(QUERY),
            "--config",
            str(config_path),
            "--index-dir",
            str(index_dir),
            "--question",
            "What shapes housing inequality?",
            "--mock",
            "--expand-context",
        ], ROOT)

        ctx_output = result.stdout
        if "[context for chunk" not in ctx_output:
            print(ctx_output)
            raise SystemExit("Context expansion test failed: expected '[context for chunk' in output")

        # --- Stats test ---
        result = run([
            sys.executable,
            str(QUERY),
            "--index-dir",
            str(index_dir),
            "--stats",
        ], ROOT)

        stats_output = result.stdout
        for marker in ["Index Statistics", "Files:", "Chunks:", "Embeddings:", "Metadata mode:", "Health", "Status: OK", "Format:"]:
            if marker not in stats_output:
                print(stats_output)
                raise SystemExit(f"Stats test failed: missing '{marker}' in output")

        # --- Wiki-aware retrieval tests ---
        wiki_root = temp_dir / "wiki"
        raw_dir = wiki_root / "raw"
        claims_dir = wiki_root / "claims"
        concepts_dir = wiki_root / "concepts"
        raw_dir.mkdir(parents=True)
        claims_dir.mkdir(parents=True)
        concepts_dir.mkdir(parents=True)
        (raw_dir / "care.md").write_text(
            "# Care Evidence\n\nLong-term parental care, love, and responsive support explain why filial duties are not based only on biological birth.\n",
            encoding="utf-8",
        )
        (raw_dir / "unrelated.md").write_text(
            "# Transit\n\nUrban transport scheduling has no relation to family ethics.\n",
            encoding="utf-8",
        )
        (claims_dir / "孝的道德基础是良好照料.md").write_text(
            """---
title: 孝的道德基础是良好照料
type: claim
claim_type: support
core: true
status: supported
confidence: medium
supports: [孝为仁之本]
opposes: [孝基于生育事实]
limits: []
depends_on: []
related_concepts: [孝, 照料]
related_entities: [Cline]
related_comparisons: []
sources: [Cline]
---
# 孝的道德基础是良好照料

## 命题
孝的道德基础不是单纯生育事实，而是长期照料、爱与支持。

## 关系
- 支撑：[[孝为仁之本]]
- 反对：[[孝基于生育事实]]

## 关键证据
- [[Cline]]：良好照料比生育事实更能解释孝的道德基础。
  - 证据位置：`raw/care.md:1-2`

## 写作用途
回应孝是否只是血缘义务。
""",
            encoding="utf-8",
        )
        (concepts_dir / "孝.md").write_text(
            "# 孝\n\n[[孝的道德基础是良好照料]] 说明孝与照料相关。\n",
            encoding="utf-8",
        )

        raw_index = temp_dir / "检索索引" / "raw"
        wiki_index = temp_dir / "检索索引" / "wiki"
        run([
            sys.executable,
            str(BUILD),
            "--md-dir",
            str(wiki_root),
            "--index-dir",
            str(wiki_index),
            "--include-dirs",
            "claims,concepts",
            "--exclude-dirs",
            "raw,_archive",
            "--metadata-mode",
            "wiki",
            "--mock",
        ], ROOT)
        run([
            sys.executable,
            str(BUILD),
            "--md-dir",
            str(raw_dir),
            "--index-dir",
            str(raw_index),
            "--metadata-mode",
            "enriched_raw",
            "--mock",
        ], ROOT)
        manifest = json.loads((wiki_index / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("include_dirs") != ["claims", "concepts"]:
            raise SystemExit(f"Wiki index manifest missing include_dirs: {manifest}")
        if manifest.get("metadata_mode") != "wiki":
            raise SystemExit(f"Wiki index manifest missing metadata_mode wiki: {manifest}")
        raw_manifest = json.loads((raw_index / "manifest.json").read_text(encoding="utf-8"))
        if raw_manifest.get("metadata_mode") != "enriched_raw":
            raise SystemExit(f"Raw index manifest missing metadata_mode enriched_raw: {raw_manifest}")
        raw_chunks_text = (raw_index / "chunks.jsonl").read_text(encoding="utf-8")
        if "semantic_metadata" not in raw_chunks_text or "孝的道德基础是良好照料" not in raw_chunks_text:
            print(raw_chunks_text)
            raise SystemExit("Enriched raw test failed: raw chunks missing semantic metadata")
        if "embedding_text" not in raw_chunks_text or "检索增强标签" not in raw_chunks_text:
            print(raw_chunks_text)
            raise SystemExit("Enriched raw test failed: raw chunks missing retrieval-only embedding text")
        chunks_text = (wiki_index / "chunks.jsonl").read_text(encoding="utf-8")
        if "页面类型：claim" not in chunks_text or "相关概念：孝、照料" not in chunks_text:
            print(chunks_text)
            raise SystemExit("Wiki metadata-mode test failed: retrieval text missing claim metadata")
        if "Transit" in chunks_text:
            print(chunks_text)
            raise SystemExit("Wiki include/exclude test failed: raw content appeared in wiki index")

        # --- Evidence path normalization should handle raw/, ./raw/, and wiki/raw/ forms ---
        (claims_dir / "孝的道德基础是良好照料.md").write_text(
            (claims_dir / "孝的道德基础是良好照料.md").read_text(encoding="utf-8").replace(
                "证据位置：`raw/care.md:1-2`",
                "证据位置：`wiki/raw/care.md:1-2`",
            ),
            encoding="utf-8",
        )
        run([
            sys.executable,
            str(BUILD),
            "--md-dir",
            str(wiki_root),
            "--index-dir",
            str(wiki_index),
            "--include-dirs",
            "claims,concepts",
            "--exclude-dirs",
            "raw,_archive",
            "--metadata-mode",
            "wiki",
            "--mock",
        ], ROOT)

        result = run([
            sys.executable,
            str(QUERY),
            "--wiki-index-dir",
            str(wiki_index),
            "--raw-index-dir",
            str(raw_index),
            "--question",
            "孝为什么不是只基于生育事实？",
            "--wiki-first",
            "--mock",
        ], ROOT)
        wiki_output = result.stdout
        for marker in ["# Wiki Hits", "# Expanded Query", "# Raw Evidence", "孝的道德基础是良好照料", "care.md", "wiki_evidence_boost: true", "semantic_type_boost", "retrieval_tags"]:
            if marker not in wiki_output:
                print(wiki_output)
                raise SystemExit(f"Wiki-first test failed: missing '{marker}' in output")

        print("SiliconFlow-rag self-test passed (full + incremental + context + stats + wiki-aware + enriched-raw)")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
