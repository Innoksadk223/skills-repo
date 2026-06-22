#!/usr/bin/env python3
"""Static checks for the agent-loop skill package."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        fail("SKILL.md must start with YAML frontmatter")
    try:
        raw = text.split("---\n", 2)[1]
    except IndexError:
        fail("SKILL.md frontmatter is not closed")

    data: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    skill = root / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    meta = frontmatter(text)

    name = meta.get("name", "")
    description = meta.get("description", "")

    if not re.fullmatch(r"[A-Za-z0-9-]+", name):
        fail("name must use only letters, numbers, and hyphens")
    if not description.startswith("Use when "):
        fail('description must start with "Use when "')
    if len(description) > 500:
        fail("description should stay under 500 characters")
    if any(word in description.lower() for word in ("plan", "act", "audit", "verify", "deliver")):
        fail("description should describe triggers, not summarize the workflow")

    lines = text.splitlines()
    if len(lines) > 180:
        fail("SKILL.md should stay under 180 lines")

    for ref in (
        "references/contract-template.md",
        "references/plan-act-audit.md",
        "references/runner-template.py",
    ):
        if not (root / ref).exists():
            fail(f"missing referenced file: {ref}")

    forbidden_shortcuts = ("SendMessage", "CronCreate", "ScheduleWakeup")
    for token in forbidden_shortcuts:
        if token in text:
            fail(f"platform-specific shortcut belongs in references, not SKILL.md: {token}")

    print("OK: agent-loop skill package passes static checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
