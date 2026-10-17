#!/usr/bin/env python3
"""Bounded Markdown storage for user-profile. Python 3.9+, macOS/Linux."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

LIMIT = 4000
NAMES = ("profile.md", "changes.md")
DEFAULT_ROOT = Path.home() / ".agents" / "user-profile"
HEADERS = {"profile.md": "# 用户画像\n", "changes.md": "# 画像变更\n"}
STAGING_PREFIX = ".user-profile-"


class StoreError(Exception):
    pass


@contextmanager
def locked(root, exclusive=False):
    # Lock the stable directory inode, not files replaced by os.replace().
    fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError:
            raise StoreError("BUSY: 数据目录正被维护，稍后重新读取；不要删锁或目录。")
        yield
    finally:
        os.close(fd)


def snapshot(root):
    result = {}
    for name in NAMES:
        path = root / name
        if not stat.S_ISREG(path.lstat().st_mode):
            raise StoreError("NOT_REGULAR: {} 必须是普通文件，不接受链接。".format(path))
        result[name] = path.read_bytes()
    return result


def revision(data):
    digest = hashlib.sha256()
    for name in NAMES:
        raw = data[name]
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return digest.hexdigest()


def measure(data):
    # Decode bytes directly: do not normalize CRLF or strip trailing whitespace.
    return {name: len(data[name].decode("utf-8")) for name in NAMES}


def enforce(counts):
    over = ["{}: {} > {}".format(name, count, LIMIT)
            for name, count in counts.items() if count > LIMIT]
    if over:
        raise StoreError("OVER_LIMIT: " + "; ".join(over) + "；本次未写入，不输出超限正文。")


def staging_names(root):
    return sorted(path.name for path in root.iterdir() if path.name.startswith(STAGING_PREFIX))


def require_no_staging(names):
    if names:
        raise StoreError("STAGING_REMAINS: {}；先核对用途并按维护说明清理，勿宣称忘记已完成。".format(
            ", ".join(names)))


def initialize(root):
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    with locked(root, exclusive=True):
        require_no_staging(staging_names(root))
        missing = []
        for name in NAMES:
            path = root / name
            try:
                info = path.lstat()
            except FileNotFoundError:
                missing.append(name)
            else:
                if not stat.S_ISREG(info.st_mode):
                    raise StoreError("NOT_REGULAR: {} 必须是普通文件，不接受链接。".format(path))
        for name in missing:
            fd = os.open(str(root / name), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(HEADERS[name].encode("utf-8"))
        return {"ok": True, "created": missing}


def clean_staging(root, names):
    # Explicit names only: a matching prefix is not proof that a file is disposable.
    with locked(root, exclusive=True):
        paths = []
        for name in dict.fromkeys(names):
            if Path(name).name != name or not name.startswith(STAGING_PREFIX):
                raise StoreError("INVALID_STAGING: 只接受已确认的暂存文件名，不接受路径或正式数据。")
            path = root / name
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                raise StoreError("UNSAFE_STAGING: {} 不是当前用户所有的单链接普通文件，未清理。".format(name))
            paths.append(path)
        for path in paths:
            path.unlink()
        return {"ok": True, "removed": [path.name for path in paths]}


def read_store(root, history=False, check=False):
    with locked(root):
        staging = staging_names(root)
        if not check:
            require_no_staging(staging)
        data = snapshot(root)
        counts = measure(data)
        report = {"version": revision(data), "characters": counts, "limit": LIMIT,
                  "ok": all(count <= LIMIT for count in counts.values()) and not staging}
        if staging:
            report["staging_files"] = staging
        if not check:
            enforce(counts)
            report["profile"] = data["profile.md"].decode("utf-8")
            if history:
                report["changes"] = data["changes.md"].decode("utf-8")
        return report


def commit(root, proposed, expected):
    counts = measure(proposed)
    enforce(counts)  # Both candidates pass before any directory/file modification.
    with locked(root, exclusive=True):
        require_no_staging(staging_names(root))
        current = snapshot(root)
        if revision(current) != expected:
            raise StoreError("STALE_VERSION: 内容已变化；重新读取两份文件再合并，本次未写入。")
        staged = {}
        try:
            # Prepare both files before replacing either; temp files contain no old archive.
            for name in NAMES:
                if proposed[name] == current[name]:
                    continue
                fd, temp = tempfile.mkstemp(prefix=STAGING_PREFIX, dir=str(root))
                staged[name] = Path(temp)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(proposed[name])
                    stream.flush()
                    os.fsync(stream.fileno())
            # ponytail: per-file atomic, not a two-file transaction; no journal/backup store.
            for name, temp in staged.items():
                os.replace(str(temp), str(root / name))
            saved = snapshot(root)
            if saved != proposed:
                raise StoreError("VERIFY_FAILED: 写后内容不符，停止重试并检查两份实际文件。")
            return {"ok": True, "changed": bool(staged), "version": revision(saved),
                    "characters": counts, "limit": LIMIT}
        except OSError as exc:
            raise StoreError("WRITE_ERROR: {}；可能部分写入，检查两份实际内容，勿盲目重试。".format(exc))
        finally:
            for temp in staged.values():
                temp.unlink(missing_ok=True)


def self_test(scratch):
    """One CLI-level check using only fabricated data under the supplied scratch root."""
    checks = []
    with tempfile.TemporaryDirectory(prefix="user-profile-test-", dir=str(scratch)) as folder:
        base = Path(folder)
        root = base / "data"
        script = str(Path(__file__).resolve())
        candidates = {name: base / ("next-" + name) for name in NAMES}

        def run(*args, code=0):
            result = subprocess.run(
                [sys.executable, "-B", script, "--data-dir", str(root), *args],
                capture_output=True, text=True, timeout=10)
            assert result.returncode == code, (args, result.returncode, result.stdout, result.stderr)
            return result

        def report(*args, code=0):
            return json.loads(run(*args, code=code).stdout)

        def submit(profile, changes, version, code=0):
            for name, content in zip(NAMES, (profile, changes)):
                candidates[name].write_bytes(content)
            return run("commit", "--expect", version,
                       "--profile-file", str(candidates["profile.md"]),
                       "--changes-file", str(candidates["changes.md"]), code=code)

        def expect_rejected(profile, changes, version, marker):
            before = snapshot(root)
            result = submit(profile, changes, version, code=1)
            assert marker in result.stderr and not result.stdout, result
            assert snapshot(root) == before, "Rejected write modified original data"

        for command in ("read", "check"):
            assert not run(command, code=1).stdout and not root.exists()
        checks.append("普通读取不创建缺失目录")
        assert report("init")["created"] == list(NAMES)
        assert snapshot(root) == {name: text.encode("utf-8") for name, text in HEADERS.items()}
        assert all(stat.S_IMODE((root / name).stat().st_mode) & 0o077 == 0 for name in NAMES)
        checks.append("显式初始化空标题，文件不向其他用户开放")

        initial = report("read")
        assert "profile" in initial and "changes" not in initial
        assert "changes" in report("read", "--history")
        checks.append("默认仅显示画像；历史按需显示")

        text = ("中é🙂 \r\n" * 667)[:3999] + "\n"
        exact = text.encode("utf-8")
        assert len(text) == LIMIT and len(exact) > LIMIT
        small = "# 虚构内容\n".encode("utf-8")
        for profile, changes, label in (
                (exact, small, "画像 4000 可写"),
                (small, exact, "历史 4000 可写"),
                (exact, exact, "两份各 4000 可同时写入")):
            version = report("read")["version"]
            saved = json.loads(submit(profile, changes, version).stdout)
            assert saved["ok"] and snapshot(root) == dict(zip(NAMES, (profile, changes)))
            counts = report("check")["characters"]
            assert counts == {n: len(b.decode("utf-8")) for n, b in zip(NAMES, (profile, changes))}
            checks.append(label)
        checks.append("中文/emoji/空格/CRLF/末尾换行按码点计数，字节原样保存")

        version = report("read")["version"]
        expect_rejected(exact + b"x", small, version, "profile.md: 4001 > 4000")
        checks.append("画像 4001 拒绝；两份原文件不变")
        expect_rejected(small, exact + b"x", version, "changes.md: 4001 > 4000")
        checks.append("历史 4001 拒绝；两份原文件不变")
        expect_rejected(b"\xff", small, version, "utf-8")
        checks.append("无效 UTF-8 拒绝且不修改数据")

        submit(exact, small, version)
        expect_rejected(small, small, version, "STALE_VERSION")
        checks.append("仅历史变化也使旧版本失效；拒绝覆盖")
        version = report("read")["version"]
        submit(small, small, version)
        expect_rejected(exact, small, version, "STALE_VERSION")
        checks.append("画像变化后旧版本拒绝覆盖")

        before = snapshot(root)
        metadata = {name: (root / name).stat() for name in NAMES}
        saved = json.loads(submit(small, small, revision(before)).stdout)
        assert not saved["changed"] and saved["version"] == revision(before)
        assert snapshot(root) == before
        assert all((root / name).stat().st_ino == metadata[name].st_ino and
                   (root / name).stat().st_mtime_ns == metadata[name].st_mtime_ns for name in NAMES)
        checks.append("相同内容提交不重写文件，版本不变")
        assert report("init")["created"] == [] and snapshot(root) == before
        checks.append("重复初始化保留已有内容")

        with locked(root, exclusive=True):
            before = snapshot(root)
            result = submit(exact, exact, revision(before), code=1)
            assert "BUSY" in result.stderr and snapshot(root) == before
            for command in ("read", "init"):
                result = run(command, code=1)
                assert "BUSY" in result.stderr and not result.stdout
        checks.append("并发目录锁拒绝第二个写入者，原文件不变")
        checks.append("读取和初始化遵守目录锁")

        for name in NAMES:
            (root / name).write_bytes(exact + b"x")  # Simulate direct external editing.
            result = run("read", code=1)
            assert not result.stdout and "OVER_LIMIT" in result.stderr
            state = report("check", code=1)
            assert not state["ok"] and state["characters"][name] == LIMIT + 1
            assert "profile" not in state and "changes" not in state
            submit(small, small, state["version"])
        checks.append("读取阻止外部超限；check 不泄漏正文并提供修复版本")
        before = snapshot(root)
        missing = root / "changes.md"
        missing.unlink()
        result = run("read", code=1)
        assert not result.stdout and not missing.exists()
        assert (root / "profile.md").read_bytes() == before["profile.md"]
        checks.append("缺失文件报错，不静默重建")
        result = submit(small, small, revision(before), code=1)
        assert not result.stdout and not missing.exists()
        assert (root / "profile.md").read_bytes() == before["profile.md"]
        checks.append("提交不静默重建缺失文件")
        assert report("init")["created"] == ["changes.md"]
        assert (root / "profile.md").read_bytes() == before["profile.md"]
        assert missing.read_text(encoding="utf-8") == HEADERS["changes.md"]
        checks.append("初始化只补缺失文件，保留另一份数据")
        missing.unlink()
        missing.symlink_to(root / "profile.md")
        assert "NOT_REGULAR" in run("init", code=1).stderr
        assert missing.is_symlink() and (root / "profile.md").read_bytes() == before["profile.md"]
        missing.unlink()
        report("init")
        checks.append("初始化拒绝符号链接且不覆盖目标")

        before = snapshot(root)
        fd, temp = tempfile.mkstemp(prefix=STAGING_PREFIX, dir=str(root))
        orphan = Path(temp)
        secret = b"fictional-private-candidate"
        with os.fdopen(fd, "wb") as stream:
            stream.write(secret)
        for command in ("read", "init"):
            result = run(command, code=1)
            assert "STAGING_REMAINS" in result.stderr and not result.stdout
            assert secret.decode() not in result.stderr
        expect_rejected(small, small, revision(before), "STAGING_REMAINS")
        state = report("check", code=1)
        assert not state["ok"] and state["staging_files"] == [orphan.name]
        assert "profile" not in state and "changes" not in state
        assert secret.decode() not in json.dumps(state)
        checks.append("模拟中断残留阻止正常操作，check 只列名称不泄漏正文")

        unrelated = root / "notes.txt"
        unrelated.write_bytes(b"keep")
        for name in ("profile.md", "notes.txt", "../" + orphan.name, str(orphan)):
            result = run("clean-staging", "--file", orphan.name, "--file", name, code=1)
            assert "INVALID_STAGING" in result.stderr and orphan.read_bytes() == secret
        checks.append("清理预检拒绝正式文件、无关文件和路径，不先删合法项")

        unsafe = root / (STAGING_PREFIX + "unsafe")
        unsafe.symlink_to(root / "profile.md")
        assert "UNSAFE_STAGING" in run("clean-staging", "--file", unsafe.name, code=1).stderr
        assert unsafe.is_symlink()
        unsafe.unlink()
        unsafe.mkdir()
        assert "UNSAFE_STAGING" in run("clean-staging", "--file", unsafe.name, code=1).stderr
        assert unsafe.is_dir()
        unsafe.rmdir()
        os.link(root / "profile.md", unsafe)
        assert "UNSAFE_STAGING" in run("clean-staging", "--file", unsafe.name, code=1).stderr
        unsafe.unlink()
        checks.append("清理拒绝符号链接、目录及硬链接")
        with locked(root, exclusive=True):
            assert "BUSY" in run("clean-staging", "--file", orphan.name, code=1).stderr
            assert orphan.exists()
        checks.append("清理遵守独占锁")
        result = report("clean-staging", "--file", orphan.name, "--file", orphan.name)
        assert result["removed"] == [orphan.name] and not orphan.exists()
        assert snapshot(root) == before and unrelated.read_bytes() == b"keep"
        assert report("read")["ok"] and report("check")["ok"]
        checks.append("明确清理后恢复读取，正式数据和无关文件不变")
        assert not staging_names(root), "Staging files leaked"
    return {"ok": True, "checks": checks, "count": len(checks),
            "temporary_data_removed": not base.exists(), "real_data_used": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_ROOT,
                        help="默认 ~/.agents/user-profile；替代位置须明确授权，不用于绕过容量")
    commands = parser.add_subparsers(dest="command", required=True)
    reader = commands.add_parser("read", help="检查容量并读取画像")
    reader.add_argument("--history", action="store_true", help="同时显示历史，供维护使用")
    commands.add_parser("check", help="仅输出容量、状态及版本，无正文")
    commands.add_parser("init", help="仅在获准后补齐缺失文件，不覆盖已有数据")
    cleaner = commands.add_parser("clean-staging", help="仅清理已确认无恢复用途的指定暂存文件")
    cleaner.add_argument("--file", dest="files", action="append", required=True,
                         help="数据目录内的暂存文件名，可重复指定，不接受路径")
    writer = commands.add_parser("commit", help="提交完整候选文本，容量/版本失败不写入")
    writer.add_argument("--expect", required=True, help="基于 read/check 返回的版本")
    writer.add_argument("--profile-file", required=True, type=Path)
    writer.add_argument("--changes-file", required=True, type=Path)
    tester = commands.add_parser("self-test", help="仅在获准时运行虚构数据自检")
    tester.add_argument("--scratch", required=True, type=Path, help="已有的会话临时目录")
    args = parser.parse_args()
    try:
        root = args.data_dir.expanduser().resolve()
        if args.command == "self-test":
            result = self_test(args.scratch.expanduser())
        elif args.command == "init":
            result = initialize(root)
        elif args.command == "clean-staging":
            result = clean_staging(root, args.files)
        elif args.command == "commit":
            proposed = {"profile.md": args.profile_file.expanduser().read_bytes(),
                        "changes.md": args.changes_file.expanduser().read_bytes()}
            result = commit(root, proposed, args.expect)
        else:
            result = read_store(root, history=getattr(args, "history", False),
                                check=args.command == "check")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    except (StoreError, OSError, UnicodeError) as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
