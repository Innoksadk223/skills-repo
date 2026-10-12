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


def read_store(root, history=False, check=False):
    with locked(root):
        data = snapshot(root)
        counts = measure(data)
        report = {"version": revision(data), "characters": counts, "limit": LIMIT,
                  "ok": all(count <= LIMIT for count in counts.values())}
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
        current = snapshot(root)
        if revision(current) != expected:
            raise StoreError("STALE_VERSION: 内容已变化；重新读取两份文件再合并，本次未写入。")
        staged = {}
        try:
            # Prepare both files before replacing either; temp files contain no old archive.
            for name in NAMES:
                if proposed[name] == current[name]:
                    continue
                fd, temp = tempfile.mkstemp(prefix=".user-profile-", dir=str(root))
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
        root.mkdir(mode=0o700)
        for name in NAMES:
            (root / name).write_bytes(("# " + name + "\n").encode("utf-8"))
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

        with locked(root, exclusive=True):
            before = snapshot(root)
            result = submit(exact, exact, revision(before), code=1)
            assert "BUSY" in result.stderr and snapshot(root) == before
        checks.append("并发目录锁拒绝第二个写入者，原文件不变")

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
        assert not list(root.glob(".user-profile-*")), "Staging files leaked"
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
