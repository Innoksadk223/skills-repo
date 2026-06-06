#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

ENV_PATH = Path.home() / '.hermes' / 'env.md'
SECTION_TITLE = '## 常见陷阱'


def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'`+', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s


def ensure_section(text: str) -> str:
    if SECTION_TITLE in text:
        return text
    text = text.rstrip() + f'\n\n{SECTION_TITLE}\n'
    return text


def split_section(text: str):
    marker = SECTION_TITLE
    idx = text.find(marker)
    if idx == -1:
        text = ensure_section(text)
        idx = text.find(marker)
    after = text[idx + len(marker):]
    next_heading = re.search(r'\n##\s+', after)
    if next_heading:
        end = idx + len(marker) + next_heading.start()
    else:
        end = len(text)
    return text[:idx], text[idx:end], text[end:]


def build_entry(title: str, scene: str, cause: str, fix: str, entry_date: str | None = None) -> str:
    d = entry_date or str(date.today())
    return f"- **[{d}] {title}**：{scene} → {cause} → {fix}"


def section_has_similar(section: str, title: str, scene: str) -> bool:
    key1 = normalize(title)
    key2 = normalize(scene)
    body = normalize(section)
    return key1 in body or key2 in body


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--title', required=True)
    p.add_argument('--scene', required=True)
    p.add_argument('--cause', required=True)
    p.add_argument('--fix', required=True)
    p.add_argument('--date', default=None)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ENV_PATH.exists():
        text = ENV_PATH.read_text(encoding='utf-8')
    else:
        text = '# 系统编程环境\n'

    text = ensure_section(text)
    before, section, after = split_section(text)

    entry = build_entry(args.title, args.scene, args.cause, args.fix, args.date)

    if section_has_similar(section, args.title, args.scene):
        print('SKIP: similar gotcha already exists')
        print(entry)
        return

    section = section.rstrip() + '\n\n' + entry + '\n'
    new_text = before + section + after

    if args.dry_run:
        print(entry)
        return

    ENV_PATH.write_text(new_text, encoding='utf-8')
    print('ADDED:', entry)
    print('FILE:', ENV_PATH)


if __name__ == '__main__':
    main()
