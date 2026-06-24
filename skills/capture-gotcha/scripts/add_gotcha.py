#!/usr/bin/env python3
"""capture-gotcha 环境教训管理器：add / search / list / update / check / self-test。add 后自动清理 >7 天条目。"""

import argparse
import re
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ENV_PATH = Path.home() / '.hermes' / 'env.md'
MAX_AGE_DAYS = 7


def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'`+', '', s)
    return re.sub(r'\s+', ' ', s)


def read_env(env_path: Path) -> str:
    if env_path.exists():
        return env_path.read_text(encoding='utf-8')
    return '# 系统编程环境\n'


def build_entry(title: str, scene: str, cause: str, fix: str, entry_date: str | None = None) -> str:
    d = entry_date or str(date.today())
    return f"- **[{d}] {title}**：{scene} → {cause} → {fix}"


def find_similar(text: str, title: str, scene: str) -> bool:
    key1 = normalize(title)
    key2 = normalize(scene)
    body = normalize(text)
    return key1 in body or key2 in body


def auto_clean(env_path: Path, max_days: int = MAX_AGE_DAYS) -> str:
    """删除距今 >max_days 的条目。每次 add 后自动调用。"""
    text = read_env(env_path)
    lines = text.split('\n')
    cutoff = date.today()
    kept = []
    removed = 0
    for line in lines:
        m = re.match(r'- \*\*\[(\d{4}-\d{2}-\d{2})\]', line)
        if m:
            entry_date = date.fromisoformat(m.group(1))
            if (cutoff - entry_date).days > max_days:
                removed += 1
                continue
        kept.append(line)
    if removed:
        env_path.write_text('\n'.join(kept), encoding='utf-8')
        return f'auto_clean: removed {removed} expired entr{"y" if removed == 1 else "ies"} (>{max_days}d)'
    return ''


def add_entry(env_path: Path, title: str, scene: str, cause: str, fix: str,
              entry_date: str | None = None, dry_run: bool = False,
              section: str = '## 常见陷阱') -> str:
    text = read_env(env_path)
    if find_similar(text, title, scene):
        entry = build_entry(title, scene, cause, fix, entry_date)
        return f'SKIP: similar gotcha already exists\n{entry}'

    entry = build_entry(title, scene, cause, fix, entry_date)

    if section not in text:
        text = text.rstrip() + f'\n\n{section}\n'
    idx = text.find(section)
    after = text[idx + len(section):]
    next_heading = re.search(r'\n##\s+', after)
    if next_heading:
        end = idx + len(section) + next_heading.start()
        before, rest = text[:end], text[end:]
    else:
        before, rest = text[:idx + len(section)], after

    if dry_run:
        return f'[dry-run] {entry}'

    new_text = before.rstrip() + '\n\n' + entry + '\n' + rest
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(new_text, encoding='utf-8')

    # auto-clean 无声运行
    clean_msg = auto_clean(env_path)
    out = f'ADDED: {entry}\nFILE: {env_path}'
    if clean_msg:
        out += f'\n{clean_msg}'
    return out


def search_entries(env_path: Path, keyword: str) -> str:
    text = read_env(env_path)
    lines = text.split('\n')
    kw = normalize(keyword)
    results = []
    for i, line in enumerate(lines, 1):
        if line.startswith('- **[') and kw in normalize(line):
            results.append(f'{i}: {line}')
    if not results:
        return f'No entries matching "{keyword}"'
    return f'{len(results)} match(es):\n' + '\n'.join(results)


def list_entries(env_path: Path, section_filter: str | None = None) -> str:
    text = read_env(env_path)
    lines = text.split('\n')
    current_section = ''
    entries: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines, 1):
        if line.startswith('## '):
            current_section = line[3:].strip()
            continue
        if line.startswith('- **['):
            if section_filter and section_filter not in current_section:
                continue
            entries.append((i, current_section, line))
    if not entries:
        return 'No entries found.'
    out = f'{len(entries)} entries:\n'
    for lineno, sec, entry in entries:
        out += f'[{sec}] L{lineno}: {entry}\n'
    return out.rstrip()


def update_entry(env_path: Path, keyword: str, title: str | None = None,
                 cause: str | None = None, fix: str | None = None,
                 section: str | None = None, dry_run: bool = False) -> str:
    """按关键词匹配条目并更新。刷新日期为今天。"""
    text = read_env(env_path)
    lines = text.split('\n')
    kw = normalize(keyword)
    found = False
    today = str(date.today())
    for i, line in enumerate(lines):
        if line.startswith('- **[') and kw in normalize(line):
            m = re.match(r'- \*\*\[(\d{4}-\d{2}-\d{2})\] (.+?)\*\*：(.+) → (.+) → (.+)', line)
            if m:
                new_title = title if title else m.group(2)
                new_cause = cause if cause else m.group(4)
                new_fix = fix if fix else m.group(5)
                lines[i] = f'- **[{today}] {new_title}**：{m.group(3)} → {new_cause} → {new_fix}'
                found = True
                break
    if not found:
        return f'No entry matching "{keyword}" to update.'
    if dry_run:
        return f'[dry-run] {lines[i]}'
    env_path.write_text('\n'.join(lines), encoding='utf-8')
    return f'UPDATED: {lines[i]}'


def check_error(env_path: Path, error_text: str) -> str:
    """喂入原始错误文本，匹配已知教训。将错误 extract 为有意义的词去匹配条目。"""
    text = read_env(env_path)
    norm_error = normalize(error_text)
    lines = text.split('\n')
    # 从错误文本提取 >3 字符的词作为搜索 token
    tokens = [w for w in norm_error.split() if len(w) > 3]
    results = []
    for i, line in enumerate(lines, 1):
        if line.startswith('- **['):
            if any(t in normalize(line) for t in tokens):
                results.append(f'{i}: {line}')
    if not results:
        return 'No known gotcha matches this error. Investigate and consider `add`.'
    return f'{len(results)} match(es):\n' + '\n'.join(results)


def self_test() -> None:
    today = str(date.today())
    with tempfile.TemporaryDirectory() as td:
        env_path = Path(td) / 'env.md'

        # add
        out1 = add_entry(env_path, '路径测试', '读取不存在目录报 ENOENT', '工作目录写错', '改用绝对路径', today)
        assert 'ADDED' in out1, out1

        # dedup
        out2 = add_entry(env_path, '路径测试', '读取不存在目录报 ENOENT', '工作目录写错', '改用绝对路径', today)
        assert 'SKIP' in out2, out2

        text = env_path.read_text(encoding='utf-8')
        assert '## 常见陷阱' in text, text
        assert text.count('路径测试') == 1, text

        # cross-section add
        out3 = add_entry(env_path, 'Git代理', 'curl 不走系统代理', 'Git 没设代理', '配置 http.proxy', today,
                         section='## Git 与 GitHub')
        assert 'ADDED' in out3, out3
        assert '## Git 与 GitHub' in env_path.read_text(encoding='utf-8')

        # search
        out4 = search_entries(env_path, '路径')
        assert 'ENOENT' in out4, out4
        out5 = search_entries(env_path, '不存在这个词')
        assert 'No entries' in out5, out5

        # list
        out6 = list_entries(env_path)
        assert '常见陷阱' in out6, out6
        assert 'Git 与 GitHub' in out6, out6
        out7 = list_entries(env_path, section_filter='Git')
        assert '常见陷阱' not in out7, out7
        assert 'Git 与 GitHub' in out7, out7

        # update
        out8 = update_entry(env_path, 'Git代理', cause='Git 缺少 proxy 配置', fix='git config --global http.proxy http://127.0.0.1:7890')
        assert 'UPDATED' in out8, out8
        assert 'Git 缺少 proxy 配置' in env_path.read_text(encoding='utf-8')

        # check
        out9 = check_error(env_path, 'SSLEOFError: curl 不走系统代理')
        assert 'Git代理' in out9, out9
        out10 = check_error(env_path, 'nothing matches this random string xyzzy')
        assert 'No known gotcha' in out10, out10
        out11 = check_error(env_path, 'ENOENT: 读取不存在目录')
        assert '路径测试' in out11, out11

        # auto_clean: 添加一条旧日期条目再 add 触发清理
        old_text = env_path.read_text(encoding='utf-8')
        old_entry = '- **[2020-01-01] 远古条目**：场景 → 原因 → 解法\n'
        env_path.write_text(old_text.rstrip() + '\n\n' + old_entry)
        out12 = add_entry(env_path, '新条目', '测试自动清理', '逻辑', '解法', today)
        assert 'auto_clean: removed 1' in out12, out12
        final_text = env_path.read_text(encoding='utf-8')
        assert '远古条目' not in final_text, final_text

        # regression: add 不丢已有条目
        count_before = final_text.count('- **[')
        out13 = add_entry(env_path, '回归测试', '验证不丢数据', '逻辑', '解法', today)
        assert 'ADDED' in out13, out13
        assert env_path.read_text(encoding='utf-8').count('- **[') == count_before + 1

    print('SELF_TEST: ok')


def _add_args(parser):
    """共享的 add 参数定义。"""
    parser.add_argument('--title', required=True)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--cause', required=True)
    parser.add_argument('--fix', required=True)
    parser.add_argument('--date', default=None)
    parser.add_argument('--section', default='## 常见陷阱')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--env-path', type=Path, default=ENV_PATH)


def main():
    p = argparse.ArgumentParser(description='capture-gotcha 环境教训管理器')
    p.set_defaults(command='add')
    sub = p.add_subparsers(dest='command')

    a = sub.add_parser('add', help='新增条目（自动清理 >7 天）')
    _add_args(a)

    s = sub.add_parser('search', help='按关键词搜索')
    s.add_argument('keyword')
    s.add_argument('--env-path', type=Path, default=ENV_PATH)

    l = sub.add_parser('list', help='列出所有条目')
    l.add_argument('--section', default=None, help='按区段过滤')
    l.add_argument('--env-path', type=Path, default=ENV_PATH)

    u = sub.add_parser('update', help='更新已有条目')
    u.add_argument('keyword', help='匹配词')
    u.add_argument('--title', default=None)
    u.add_argument('--cause', default=None)
    u.add_argument('--fix', default=None)
    u.add_argument('--section', default=None)
    u.add_argument('--dry-run', action='store_true')
    u.add_argument('--env-path', type=Path, default=ENV_PATH)

    c = sub.add_parser('check', help='用原始错误文本匹配已知教训')
    c.add_argument('error_text', help='原始错误文本')
    c.add_argument('--env-path', type=Path, default=ENV_PATH)

    t = sub.add_parser('self-test', help='自检')

    # 向后兼容：无子命令时自动插入 'add'（子命令总是第一个位置参数）
    known = {'add', 'search', 'list', 'update', 'check', 'self-test'}
    if len(sys.argv) <= 1 or sys.argv[1] in ('-h', '--help') or sys.argv[1].startswith('-') or sys.argv[1] not in known:
        sys.argv.insert(1, 'add')

    args = p.parse_args()

    if args.command == 'self-test':
        self_test()
    elif args.command == 'add':
        # args 可能在主 parser 层或子 parser 层
        env_path = getattr(args, 'env_path', ENV_PATH)
        print(add_entry(env_path, args.title, args.scene, args.cause, args.fix,
                        args.date, args.dry_run, args.section))
    elif args.command == 'search':
        print(search_entries(args.env_path, args.keyword))
    elif args.command == 'list':
        print(list_entries(args.env_path, args.section))
    elif args.command == 'update':
        print(update_entry(args.env_path, args.keyword, args.title, args.cause, args.fix,
                           args.section, args.dry_run))
    elif args.command == 'check':
        print(check_error(args.env_path, args.error_text))


if __name__ == '__main__':
    main()
