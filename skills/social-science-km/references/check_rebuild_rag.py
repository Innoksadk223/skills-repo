#!/usr/bin/env python3
"""Check and incrementally update social-science-km RAG indexes.

Copy this file to a knowledge-base project root, then run:
  python3 check_rebuild_rag.py --check
  python3 check_rebuild_rag.py

The script keeps raw/wiki index maintenance in one place so agents do not
improvise local rebuild commands.
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
class IndexStatus:
    label: str
    stale: bool
    message: str
    source_dir: Path
    index_dir: Path
    metadata_mode: str
    allowed_metadata_modes: set[str]
    has_sources: bool
    settings_rebuild: bool = False


def path_matches_dir(rel_path: Path, dirs: tuple[str, ...]) -> bool:
    rel = rel_path.as_posix()
    return any(rel == folder or rel.startswith(f"{folder}/") for folder in dirs)


def compute_hashes(
    md_dir: Path,
    include_dirs: tuple[str, ...] = (),
    exclude_dirs: tuple[str, ...] = (),
) -> dict[str, str]:
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


def read_manifest(index_dir: Path) -> dict:
    manifest_path = index_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def describe_delta(label: str, new_or_changed: list[str], deleted: list[str]) -> str:
    parts = []
    if new_or_changed:
        parts.append(f"{len(new_or_changed)} 个新增/改动，需要增量更新索引")
    if deleted:
        parts.append(f"{len(deleted)} 个删除，需要从索引移除对应条目")
    return f"{label} 有" + "；".join(parts)


def graph_hashes(project_root: Path) -> dict[str, str]:
    wiki_dir = project_root / WIKI_DIR_NAME
    return compute_hashes(
        wiki_dir,
        include_dirs=WIKI_INDEX_SOURCE_DIRS,
        exclude_dirs=("raw", "_archive"),
    )


def raw_expected_metadata_mode(project_root: Path) -> str:
    return "enriched_raw" if graph_hashes(project_root) else "plain"


def raw_allowed_metadata_modes(project_root: Path) -> set[str]:
    return {"enriched_raw"} if graph_hashes(project_root) else {"plain", "enriched_raw"}


def check_one(
    project_root: Path,
    label: str,
    source_dir: Path,
    index_dir: Path,
    metadata_mode: str,
    allowed_metadata_modes: set[str] | None = None,
    include_dirs: tuple[str, ...] = (),
    exclude_dirs: tuple[str, ...] = (),
) -> IndexStatus:
    current = compute_hashes(source_dir, include_dirs=include_dirs, exclude_dirs=exclude_dirs)
    manifest = read_manifest(index_dir)
    has_sources = bool(current)
    allowed_metadata_modes = allowed_metadata_modes or {metadata_mode}

    if not current and not manifest:
        return IndexStatus(label, False, f"{label} 无可索引内容", source_dir, index_dir, metadata_mode, allowed_metadata_modes, has_sources)
    if not source_dir.is_dir():
        return IndexStatus(label, True, f"{label} 源目录不存在: {source_dir}", source_dir, index_dir, metadata_mode, allowed_metadata_modes, has_sources)
    if not manifest:
        return IndexStatus(label, True, f"{label} 索引不存在，需要先构建", source_dir, index_dir, metadata_mode, allowed_metadata_modes, has_sources)
    manifest_mode = manifest.get("metadata_mode")
    if manifest_mode not in allowed_metadata_modes:
        modes = "/".join(sorted(allowed_metadata_modes))
        return IndexStatus(
            label,
            True,
            f"{label} 索引 metadata_mode={manifest_mode}，需要按 {modes} 重建",
            source_dir,
            index_dir,
            metadata_mode,
            allowed_metadata_modes,
            has_sources,
            settings_rebuild=True,
        )
    stored = manifest.get("file_hashes")
    if not isinstance(stored, dict):
        return IndexStatus(
            label,
            True,
            f"{label} manifest 缺少 file_hashes，需要重建以支持增量检查",
            source_dir,
            index_dir,
            metadata_mode,
            allowed_metadata_modes,
            has_sources,
            settings_rebuild=True,
        )
    new_or_changed = [rel for rel, digest in current.items() if rel not in stored or stored[rel] != digest]
    deleted = [rel for rel in stored if rel not in current]
    if new_or_changed or deleted:
        return IndexStatus(
            label,
            True,
            describe_delta(label, new_or_changed, deleted),
            source_dir,
            index_dir,
            metadata_mode,
            allowed_metadata_modes,
            has_sources,
        )
    return IndexStatus(label, False, f"{label} 当前", source_dir, index_dir, metadata_mode, allowed_metadata_modes, has_sources)


def check_all(project_root: Path) -> list[IndexStatus]:
    wiki_dir = project_root / WIKI_DIR_NAME
    index_root = project_root / INDEX_DIR_NAME
    return [
        check_one(
            project_root,
            "raw",
            wiki_dir / "raw",
            index_root / RAW_INDEX_NAME,
            raw_expected_metadata_mode(project_root),
            allowed_metadata_modes=raw_allowed_metadata_modes(project_root),
        ),
        check_one(
            project_root,
            "wiki",
            wiki_dir,
            index_root / WIKI_INDEX_NAME,
            "wiki",
            include_dirs=WIKI_INDEX_SOURCE_DIRS,
            exclude_dirs=("raw", "_archive"),
        ),
    ]


def find_script(project_root: Path, *parts: str) -> Path:
    bases = [project_root, *project_root.parents]
    candidates: list[Path] = []
    for base in bases:
        candidates.append(base.joinpath(*parts))
        candidates.append(base / "skills-hermes" / "research" / parts[-3] / parts[-2] / parts[-1] if len(parts) >= 3 else base.joinpath(*parts))
    candidates.extend([
        Path.home().joinpath(".agents", *parts),
        Path.home().joinpath(".codex", *parts),
        Path.home().joinpath(".hermes", *parts),
    ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit(f"Cannot find required script: {'/'.join(parts)}")


def find_build_script(project_root: Path) -> Path:
    return find_script(project_root, "skills", "SiliconFlow-rag", "scripts", "build_index.py")


def find_lint_script(project_root: Path) -> Path | None:
    try:
        return find_script(project_root, "skills", "karpathy-wiki", "scripts", "lint.py")
    except SystemExit:
        return None


def run_wiki_lint(project_root: Path) -> None:
    lint_script = find_lint_script(project_root)
    if lint_script is None:
        print("[LINT] 未找到 karpathy-wiki lint.py，跳过。")
        return
    wiki_dir = project_root / WIKI_DIR_NAME
    if not wiki_dir.is_dir():
        print(f"[LINT] wiki 目录不存在，跳过: {wiki_dir}")
        return
    result = subprocess.run(
        [sys.executable, str(lint_script), str(wiki_dir)],
        cwd=str(project_root),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    summary = result.stdout.strip() or result.stderr.strip()
    if result.returncode != 0:
        print("[LINT] wiki lint 运行失败: " + summary)
    elif summary:
        print("[LINT] " + summary[:1200])


def build_command(status: IndexStatus, build_script: Path, mock: bool) -> list[str]:
    cmd = [
        sys.executable,
        str(build_script),
        "--md-dir",
        str(status.source_dir),
        "--index-dir",
        str(status.index_dir),
        "--metadata-mode",
        status.metadata_mode,
        "--incremental",
    ]
    if status.label == "wiki":
        cmd.extend([
            "--include-dirs",
            ",".join(WIKI_INDEX_SOURCE_DIRS),
            "--exclude-dirs",
            "raw,_archive",
        ])
    if mock:
        cmd.append("--mock")
    return cmd


def apply_updates(project_root: Path, statuses: list[IndexStatus], mock: bool, no_lint: bool) -> int:
    build_script = find_build_script(project_root)
    changed = 0
    for status in statuses:
        if not status.stale:
            continue
        if not status.has_sources and not status.index_dir.exists():
            print(f"[SKIP] {status.label}: 无可索引内容。")
            continue
        if status.label == "wiki" and not no_lint:
            run_wiki_lint(project_root)
        print(f"[UPDATE] {status.message}")
        result = subprocess.run(
            build_command(status, build_script, mock),
            cwd=str(project_root),
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.returncode != 0:
            if result.stderr.strip():
                print(result.stderr.strip(), file=sys.stderr)
            return result.returncode
        changed += 1
    if changed == 0:
        print("RAG 索引状态：当前")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check or update social-science-km RAG indexes.")
    parser.add_argument("--project-root", default=None, help="知识库项目根目录，默认是脚本所在目录")
    parser.add_argument("--check", action="store_true", help="只检查索引是否过期，不执行更新")
    parser.add_argument("--raw-only", action="store_true", help="只检查/更新 raw 索引")
    parser.add_argument("--wiki-only", action="store_true", help="只检查/更新 wiki 索引")
    parser.add_argument("--no-lint", action="store_true", help="更新 wiki 索引前不运行 karpathy-wiki lint")
    parser.add_argument("--mock", action="store_true", help="使用 SiliconFlow-rag 的本地 mock embedding，用于测试")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else PROJECT_ROOT
    statuses = check_all(project_root)
    if args.raw_only:
        statuses = [status for status in statuses if status.label == "raw"]
    if args.wiki_only:
        statuses = [status for status in statuses if status.label == "wiki"]

    stale = [status for status in statuses if status.stale]
    if args.check:
        if not stale:
            print("RAG 索引状态：当前")
            return
        for status in stale:
            print("[WARN] " + status.message)
        sys.exit(1)

    sys.exit(apply_updates(project_root, statuses, mock=args.mock, no_lint=args.no_lint))


if __name__ == "__main__":
    main()
