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
        for marker in ["Index Statistics", "Files:", "Chunks:", "Format:"]:
            if marker not in stats_output:
                print(stats_output)
                raise SystemExit(f"Stats test failed: missing '{marker}' in output")

        print("SiliconFlow-rag self-test passed (full + incremental + context + stats)")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
