#!/usr/bin/env python3
"""
KM unified query interface.

Copy this file to a knowledge-base project root, then run:
  python3 km_query.py "你的问题"
  python3 km_query.py "原文出处在哪里？" --raw-only
  python3 km_query.py "用于论文写作的精确证据" --deep
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
WIKI_DIR_NAME = "wiki"
INDEX_DIR_NAME = "检索索引"
RAW_INDEX_NAME = "raw"
WIKI_INDEX_NAME = "wiki"
WIKI_INDEX_SOURCE_DIRS = ("claims", "concepts", "entities", "comparisons", "debates", "synthesis", "queries")
SKIP_NAMES = {"_conversion_failures.md", "_conversion_manifest.md", "_主题索引.md"}


@dataclass
class StalenessStatus:
    stale: bool
    message: str
    raw_stale: bool = False
    wiki_stale: bool = False


def project_path(project_root: Path, *parts: str) -> Path:
    return project_root.joinpath(*parts)


def path_matches_dir(rel_path: Path, dirs: set[str] | tuple[str, ...]) -> bool:
    rel = rel_path.as_posix()
    return any(rel == folder or rel.startswith(f"{folder}/") for folder in dirs)


def compute_hashes(
    md_dir: Path,
    include_dirs: tuple[str, ...] | set[str] | None = None,
    exclude_dirs: tuple[str, ...] | set[str] | None = None,
) -> dict[str, str]:
    """Return {relative_path: sha256_hex} for Markdown files under md_dir."""
    include_dirs = include_dirs or ()
    exclude_dirs = exclude_dirs or ()
    hashes: dict[str, str] = {}
    if not md_dir.is_dir():
        return hashes
    for path in sorted(md_dir.rglob("*.md")):
        rel_path = path.relative_to(md_dir)
        if path.name in SKIP_NAMES:
            continue
        if any(part.startswith(".") for part in rel_path.parts):
            continue
        if include_dirs and not path_matches_dir(rel_path, include_dirs):
            continue
        if exclude_dirs and path_matches_dir(rel_path, exclude_dirs):
            continue
        content = path.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")
        hashes[rel_path.as_posix()] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return hashes


def index_manifest(index_dir: Path) -> dict:
    manifest_path = index_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def compare_hashes(current: dict[str, str], stored: dict[str, str]) -> tuple[list[str], list[str]]:
    new_or_changed = [
        rel for rel, digest in current.items()
        if rel not in stored or stored[rel] != digest
    ]
    deleted = [rel for rel in stored if rel not in current]
    return new_or_changed, deleted


def describe_delta(label: str, new_or_changed: list[str], deleted: list[str]) -> str:
    parts = []
    if new_or_changed:
        parts.append(f"{len(new_or_changed)} 个新增/改动")
    if deleted:
        parts.append(f"{len(deleted)} 个删除")
    return f"{label} 有" + "、".join(parts)


def check_one_index(
    source_dir: Path,
    index_dir: Path,
    label: str,
    include_dirs: tuple[str, ...] | None = None,
    exclude_dirs: tuple[str, ...] | None = None,
    expected_metadata_mode: str | None = None,
    allowed_metadata_modes: set[str] | None = None,
) -> tuple[bool, str]:
    current = compute_hashes(source_dir, include_dirs=include_dirs, exclude_dirs=exclude_dirs)
    manifest = index_manifest(index_dir)
    if not current and not manifest:
        return False, ""
    if not source_dir.is_dir():
        return True, f"{label} 源目录不存在: {source_dir}"
    if not manifest:
        return True, f"{label} 索引不存在，需要先构建"
    manifest_mode = manifest.get("metadata_mode")
    if allowed_metadata_modes and manifest_mode not in allowed_metadata_modes:
        modes = "/".join(sorted(allowed_metadata_modes))
        return True, f"{label} 索引 metadata_mode={manifest_mode}，需要按 {modes} 重建"
    if expected_metadata_mode and manifest_mode != expected_metadata_mode:
        return True, f"{label} 索引 metadata_mode={manifest.get('metadata_mode')}，需要按 {expected_metadata_mode} 重建"
    stored = manifest.get("file_hashes")
    if not isinstance(stored, dict):
        return True, f"{label} manifest 缺少 file_hashes，需要重建以支持增量检查"
    new_or_changed, deleted = compare_hashes(current, stored)
    if new_or_changed or deleted:
        return True, describe_delta(label, new_or_changed, deleted)
    return False, ""


def graph_hashes(project_root: Path) -> dict[str, str]:
    wiki_dir = project_path(project_root, WIKI_DIR_NAME)
    return compute_hashes(
        wiki_dir,
        include_dirs=WIKI_INDEX_SOURCE_DIRS,
        exclude_dirs=("raw", "_archive"),
    )


def raw_expected_metadata_mode(project_root: Path) -> str:
    """Default build mode: plain before graph pages, enriched_raw after graph pages."""
    return "enriched_raw" if graph_hashes(project_root) else "plain"


def raw_allowed_metadata_modes(project_root: Path) -> set[str]:
    """Before graph pages exist, both plain and enriched_raw are valid."""
    return {"enriched_raw"} if graph_hashes(project_root) else {"plain", "enriched_raw"}


def check_staleness(project_root: Path) -> StalenessStatus:
    wiki_dir = project_path(project_root, WIKI_DIR_NAME)
    index_root = project_path(project_root, INDEX_DIR_NAME)

    raw_stale, raw_msg = check_one_index(
        source_dir=wiki_dir / "raw",
        index_dir=index_root / RAW_INDEX_NAME,
        label="raw",
        allowed_metadata_modes=raw_allowed_metadata_modes(project_root),
    )
    wiki_stale, wiki_msg = check_one_index(
        source_dir=wiki_dir,
        index_dir=index_root / WIKI_INDEX_NAME,
        label="wiki",
        include_dirs=WIKI_INDEX_SOURCE_DIRS,
        exclude_dirs=("raw", "_archive"),
        expected_metadata_mode="wiki",
    )

    messages = [msg for msg in [raw_msg, wiki_msg] if msg]
    return StalenessStatus(
        stale=bool(raw_stale or wiki_stale),
        message="；".join(messages),
        raw_stale=raw_stale,
        wiki_stale=wiki_stale,
    )


def find_query_script(project_root: Path) -> Path:
    bases = [project_root, *project_root.parents]
    candidates: list[Path] = []
    for base in bases:
        candidates.extend([
            base / "skills" / "SiliconFlow-rag" / "scripts" / "query_index.py",
            base / "skills-hermes" / "research" / "SiliconFlow-rag" / "scripts" / "query_index.py",
        ])
    candidates.extend([
        Path.home() / ".agents" / "skills" / "SiliconFlow-rag" / "scripts" / "query_index.py",
        Path.home() / ".codex" / "skills" / "SiliconFlow-rag" / "scripts" / "query_index.py",
        Path.home() / ".hermes" / "skills" / "SiliconFlow-rag" / "scripts" / "query_index.py",
        Path.home() / ".hermes" / "skills" / "research" / "SiliconFlow-rag" / "scripts" / "query_index.py",
        Path("D:/hermes/skills/research/SiliconFlow-rag/scripts/query_index.py"),
    ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit("Cannot find SiliconFlow-rag query_index.py; install/update the skill first.")


def find_lint_script(project_root: Path) -> Path | None:
    bases = [project_root, *project_root.parents]
    candidates: list[Path] = []
    for base in bases:
        candidates.extend([
            base / "skills" / "karpathy-wiki" / "scripts" / "lint.py",
            base / "skills-hermes" / "research" / "karpathy-wiki" / "scripts" / "lint.py",
        ])
    candidates.extend([
        Path.home() / ".agents" / "skills" / "karpathy-wiki" / "scripts" / "lint.py",
        Path.home() / ".codex" / "skills" / "karpathy-wiki" / "scripts" / "lint.py",
        Path.home() / ".hermes" / "skills" / "karpathy-wiki" / "scripts" / "lint.py",
    ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def raw_lookup_intent(question: str) -> bool:
    lowered = question.lower()
    raw_markers = ["原文", "出处", "哪一段", "引用", "证据", "页码", "source", "quote", "citation", "passage"]
    return any(marker in question or marker in lowered for marker in raw_markers)


def choose_mode(question: str, raw_only: bool, deep: bool, project_root: Path) -> str:
    if raw_only:
        return "raw"
    wiki_manifest = project_path(project_root, INDEX_DIR_NAME, WIKI_INDEX_NAME, "manifest.json")
    if deep and wiki_manifest.exists():
        return "wiki"
    if raw_lookup_intent(question):
        return "raw"
    if wiki_manifest.exists():
        return "wiki"
    return "raw"


def build_query_command(
    project_root: Path,
    query_script: Path,
    question: str,
    mode: str,
    expand_context: bool,
    rerank: bool,
    multi_query: bool,
    candidates: int | None,
) -> list[str]:
    index_root = project_path(project_root, INDEX_DIR_NAME)
    cmd = [sys.executable, str(query_script)]
    if mode == "wiki":
        cmd.extend([
            "--wiki-first",
            "--wiki-index-dir", str(index_root / WIKI_INDEX_NAME),
            "--raw-index-dir", str(index_root / RAW_INDEX_NAME),
        ])
    else:
        cmd.extend(["--index-dir", str(index_root / RAW_INDEX_NAME)])
    cmd.extend(["--question", question])
    if expand_context:
        cmd.append("--expand-context")
    if rerank:
        cmd.append("--rerank")
    if multi_query:
        cmd.append("--multi-query")
    if candidates:
        cmd.extend(["--candidates", str(candidates)])
    return cmd


def run_wiki_lint(project_root: Path) -> str:
    lint_script = find_lint_script(project_root)
    if lint_script is None:
        return "未找到 karpathy-wiki lint.py，已跳过 wiki lint。"
    wiki_dir = project_path(project_root, WIKI_DIR_NAME)
    if not wiki_dir.is_dir():
        return f"wiki 目录不存在，已跳过 wiki lint: {wiki_dir}"
    result = subprocess.run(
        [sys.executable, str(lint_script), str(wiki_dir)],
        cwd=str(project_root),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if result.returncode != 0:
        return "wiki lint 运行失败: " + (result.stderr.strip() or result.stdout.strip())
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return "wiki lint 输出不是 JSON，已跳过摘要。"
    findings = report.get("findings") or {}
    if not findings:
        return "wiki lint: 未发现结构问题。"
    severe = [key for key in ["broken_links", "source_drift", "claim_structure", "frontmatter"] if key in findings]
    if severe:
        return "wiki lint: 发现需优先处理的问题: " + ", ".join(severe)
    return "wiki lint: 发现一般问题: " + ", ".join(sorted(findings))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query a social-science KM RAG project.")
    parser.add_argument("question", nargs="?", help="用户问题；配合 --check 可省略")
    parser.add_argument("--project-root", default=None, help="知识库项目根目录，默认是 km_query.py 所在目录")
    parser.add_argument("--check", action="store_true", help="只检查 raw/wiki 索引是否过期，不执行查询")
    parser.add_argument("--skip-check", action="store_true", help="跳过索引新旧检查，直接查询当前索引")
    parser.add_argument("--raw-only", action="store_true", help="只查 raw evidence 索引，不使用 wiki-first")
    parser.add_argument("--no-context", action="store_true", help="不补相邻 chunk")
    parser.add_argument("--rerank", action="store_true", help="启用 rerank 精排")
    parser.add_argument("--multi-query", action="store_true", help="启用多查询改写以提高召回")
    parser.add_argument("--deep", action="store_true", help="精读/写作档：wiki-first + multi-query + rerank + context")
    parser.add_argument("--candidates", type=int, default=None, help="rerank 前候选数；--deep 默认 20，普通默认由 query_index.py 决定")
    parser.add_argument("--timeout", type=int, default=120, help="查询命令超时时间（秒）")
    parser.add_argument("--no-lint", action="store_true", help="索引过期时不运行 wiki lint 摘要")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else PROJECT_ROOT

    if not args.question and not args.check:
        raise SystemExit("用法: python3 km_query.py \"你的问题\" [--raw-only|--deep|--skip-check]")

    status = StalenessStatus(False, "")
    if not args.skip_check:
        status = check_staleness(project_root)
        if status.stale:
            print(f"[WARN] RAG 索引过期：{status.message}")
            if status.wiki_stale and not args.no_lint:
                print("[LINT] " + run_wiki_lint(project_root))
            print("[HINT] 先运行增量更新脚本补入索引；确认要临时查询旧索引时再加 --skip-check。")
            sys.exit(1)

    if args.check:
        print("RAG 索引状态：当前")
        return

    assert args.question is not None
    mode = choose_mode(args.question, raw_only=args.raw_only, deep=args.deep, project_root=project_root)
    query_script = find_query_script(project_root)
    cmd = build_query_command(
        project_root=project_root,
        query_script=query_script,
        question=args.question,
        mode=mode,
        expand_context=not args.no_context,
        rerank=args.rerank or args.deep,
        multi_query=args.multi_query or args.deep,
        candidates=args.candidates or (20 if args.deep else None),
    )
    print(f"[MODE] {'wiki-first' if mode == 'wiki' else 'raw-only'}")
    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=args.timeout,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
