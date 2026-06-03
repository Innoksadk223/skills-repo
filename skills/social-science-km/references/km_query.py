#!/usr/bin/env python3
"""
KM 统一查询接口 — 一条命令完成「过期检查 + 查询」
用法: python km_query.py "你的问题"
      python km_query.py "你的问题" --skip-check  # 跳过过期检查
      python km_query.py "你的问题" --no-context   # 不加上下文
"""
import hashlib, json, sys, subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR / "wiki" / "raw"
INDEX_DIR = SCRIPT_DIR / "检索索引"
MANIFEST = INDEX_DIR / "manifest.json"
QUERY_SCRIPT = Path("D:/hermes/skills/research/SiliconFlow-rag/scripts/query_index.py")

SKIP_NAMES = {"_conversion_failures.md", "_conversion_manifest.md", "_主题索引.md"}


def compute_hashes(raw_dir: Path) -> dict[str, str]:
    """Return {relative_path: sha256_hex} for all .md files under raw_dir."""
    hashes: dict[str, str] = {}
    for f in sorted(raw_dir.rglob("*.md")):
        if f.name in SKIP_NAMES:
            continue
        if any(p.startswith(".") for p in f.relative_to(raw_dir).parts):
            continue
        rel = f.relative_to(raw_dir).as_posix()
        content = f.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")
        hashes[rel] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return hashes


def check_staleness() -> tuple[bool, str]:
    """Return (is_stale, message)."""
    if not MANIFEST.exists():
        return True, "索引不存在，请先构建: python check_rebuild_rag.py"
    if not RAW_DIR.is_dir():
        return True, f"raw 目录不存在: {RAW_DIR}"

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    stored_hashes = manifest.get("file_hashes", {})
    current_hashes = compute_hashes(RAW_DIR)

    new_or_changed = [
        rel for rel, h in current_hashes.items()
        if rel not in stored_hashes or stored_hashes[rel] != h
    ]
    deleted = [rel for rel in stored_hashes if rel not in current_hashes]

    if new_or_changed or deleted:
        parts = []
        if new_or_changed:
            parts.append(f"{len(new_or_changed)} 个文件新增/变更")
        if deleted:
            parts.append(f"{len(deleted)} 个文件删除")
        return True, f"索引过期（{', '.join(parts)}），请先重建: python check_rebuild_rag.py"
    return False, ""


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    skip_check = "--skip-check" in flags
    no_context = "--no-context" in flags

    if not args:
        print("用法: python km_query.py \"你的问题\" [--skip-check] [--no-context]")
        sys.exit(1)

    question = args[0]

    if not skip_check:
        stale, msg = check_staleness()
        if stale:
            print(f"[WARN] {msg}")
            print("[HINT] 添加 --skip-check 可跳过此检查直接查询（使用当前索引）")
            sys.exit(1)

    cmd = [
        sys.executable, str(QUERY_SCRIPT),
        "--index-dir", str(INDEX_DIR),
        "--question", question,
    ]
    if not no_context:
        cmd.append("--expand-context")

    result = subprocess.run(
        cmd, cwd=str(SCRIPT_DIR),
        capture_output=True, text=True, timeout=120,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
