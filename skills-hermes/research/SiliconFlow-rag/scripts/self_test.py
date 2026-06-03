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
        print("SiliconFlow-rag self-test passed")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
