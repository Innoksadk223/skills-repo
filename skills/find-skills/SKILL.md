---
name: find-skills
description: >-
  Helps discover and install skills from the Vercel `npx skills` ecosystem.
  Use when the user asks "find a skill for X", "is there a skill that can...",
  or expresses interest in extending agent capabilities.
---

# Find Skills

This skill bridges to the Vercel `npx skills` ecosystem — the open agent skills
package manager. Use it to discover and install skills from
[skills.sh](https://skills.sh/).

> **Note:** These are **not** Hermes native skills. They install for other AI
> agents (Claude Code, Codex, Copilot, Cursor, etc.). Hermes has its own skill
> system (`skill_manage` / `skill_view` / `skills_list`). This skill is for
> discovering the broader ecosystem.
>
> **Hermes auto-discovery:** Skills installed globally (`-g` flag) land in
> `~/.agents/skills/`. Hermes auto-discovers them from there — they show up
> in `skills_list` with no extra steps. Claude Code and Hermes get auto-symlinked.
> **Codex does NOT get auto-symlinked** — needs manual step.

## When to Use

- User asks "how do I do X" where X might be a common task with an existing skill
- User says "find a skill for X" or "is there a skill for X"
- User wants to extend agent capabilities beyond what Hermes native skills offer
- User wants to search for tools, templates, or workflows

## Key Commands

```bash
# Search for skills
npx skills find [query]

# Install a skill (global, no prompts)
npx skills add <owner/repo@skill> -g -y

# Check for updates
npx skills check

# Update all skills
npx skills update
```

**Browse all skills:** https://skills.sh/

## Workflow

### Step 1: Understand What They Need
Identify the domain (React, testing, design, deployment) and specific task.

### Step 2: Check the Leaderboard
https://skills.sh/ — top skills include:
- `vercel-labs/agent-skills` — React, Next.js, web design (100K+ installs)
- `anthropics/skills` — Frontend design, document processing (100K+ installs)

### Step 3: Search
```bash
npx skills find [query]
```

Examples:
- "how to make React app faster" → `npx skills find react performance`
- "help with PR reviews" → `npx skills find pr review`
- "need to create a changelog" → `npx skills find changelog`

### Step 4: Verify Quality
- Prefer 1K+ installs, be cautious under 100
- Trust official sources (vercel-labs, anthropics, microsoft)
- Check GitHub stars on the source repo

### Step 5: Present Options
Include: skill name & description, install count & source, install command, skills.sh link.

### Step 6: Install
```bash
npx skills add <owner/repo@skill> -g -y
```

## Post-Install: Symlink to All Agents

### Where skills land

`npx skills add <repo> -g -y` installs skill files to **`~/.agents/skills/<name>/`**.
Then it auto-creates symlinks for **supported agents** (Claude Code, Hermes, Copilot, Cursor, etc.).
**Codex is NOT auto-symlinked** — needs manual step.

### Symlink pattern

Each agent's skills directory uses the same relative path back to the shared source:

| Agent | Skills dir | Symlink target |
|-------|-----------|----------------|
| Claude Code | `.claude/skills/` | `../../.agents/skills/<name>` |
| Codex | `.codex/skills/` | `../../.agents/skills/<name>` |
| Hermes | `.hermes/skills/` | `../../.agents/skills/<name>` |

### Full symlink workflow

Run this after any `npx skills add -g` to make sure all 3 agents are covered:

```bash
cd ~

for skill in <skill1> <skill2> ...; do
  # Claude Code (usually auto-done, but safe to check)
  [ ! -e ".claude/skills/$skill" ] && \
    ln -s "../../.agents/skills/$skill" ".claude/skills/$skill"

  # Codex (NEEDS manual)
  [ ! -e ".codex/skills/$skill" ] && \
    ln -s "../../.agents/skills/$skill" ".codex/skills/$skill"

  # Hermes — check for native skill conflict first
  if [ ! -e ".hermes/skills/$skill" ]; then
    if [ -z "$(ls -d .hermes/skills/*/$skill 2>/dev/null)" ]; then
      ln -s "../../.agents/skills/$skill" ".hermes/skills/$skill"
    else
      echo "⚠ Hermes 已有原生 $skill （在分类子目录中），跳过 symlink"
    fi
  fi
done
```

> **Hermes native skill conflict:** Hermes stores native skills under category
> subdirectories (e.g. `.hermes/skills/<category>/<skill-name>/`).
> A top-level symlink `~/.hermes/skills/<skill-name> -> ~/.agents/skills/<skill-name>`
> does NOT overwrite the categorized version — Hermes loads both. To avoid confusion,
> check with `ls -d .hermes/skills/*/$skill` before symlinking. If a native version
> exists, prefer it (it's tailored for Hermes) and skip the symlink.

### Quick check: which skills need symlinks

```bash
# Comm list: Claude Code has, Codex doesn't
comm -23 <(ls -1 .claude/skills/ | sort) <(ls -1 .codex/skills/ | sort)

# List all skills in shared storage
ls ~/.agents/skills/

# Check symlink status in each agent
for agent in .claude .codex .hermes; do
  echo "=== $agent ==="
  for f in "$agent/skills/"*; do
    [ -L "$f" ] && echo "🔗 $(basename $f)" || true
  done
done
```

### One-liner: symlink everything from ~/.agents/skills/ to Codex

```bash
cd .codex/skills
for d in ../../.agents/skills/*/; do
  name=$(basename "$d")
  [ ! -e "$name" ] && ln -s "../../.agents/skills/$name" "$name"
done
```

## Pitfalls & Troubleshooting

### Codex not auto-symlinked

`npx skills add -g` auto-symlinks to most supported agents but **skips Codex**.
Always check and manually symlink:
```bash
cd .codex/skills
for d in ../../.agents/skills/*/; do
  name=$(basename "$d")
  [ ! -e "$name" ] && ln -s "../../.agents/skills/$name" "$name"
done
```

### git clone fails

`npx skills add` uses `git clone` over HTTPS. If git over HTTPS fails but the
network is otherwise reachable (ping works, GitHub API responds), install manually:

1. Find the repo and skill name via skills.sh or `npx skills find [query]`
2. Check the SKILL.md path via GitHub API:
   ```bash
   curl -sL "https://api.github.com/repos/<owner>/<repo>/contents/.claude/skills/<skill-name>"
   ```
3. Download the zipball and extract only needed files:
   ```bash
   curl -sL -o /tmp/skill.zip "https://api.github.com/repos/<owner>/<repo>/zipball/main"
   python3 -c "
   import zipfile, os
   with zipfile.ZipFile('/tmp/skill.zip', 'r') as z:
       for name in z.namelist():
           if '/.claude/skills/<skill>/' in name or '/src/' in name:
               z.extract(name, '/tmp/extracted')
   "
   ```
4. Copy SKILL.md + scripts/data to `.claude/skills/<skill>/`
5. Repeat for other agents (`.codex/`, etc.)

### Skill has internal symlinks for scripts/data

Some skills (notably from `nextlevelbuilder/*` repos) use symlinks inside the skill
directory to share scripts/data across sub-skills. When installing manually, resolve
these by copying the actual files into the skill dir directly instead of recreating symlinks.

## Common Categories

| Category        | Example Queries                          |
| --------------- | ---------------------------------------- |
| Web Development | react, nextjs, typescript, css, tailwind |
| Testing         | testing, jest, playwright, e2e           |
| DevOps          | deploy, docker, kubernetes, ci-cd        |
| Documentation   | docs, readme, changelog, api-docs        |
| Code Quality    | review, lint, refactor, best-practices   |
| Design          | ui, ux, design-system, accessibility     |
| Productivity    | workflow, automation, git                |

> **Support file:** `references/symlink-agents.md` — condensed cheatsheet for
> cross-agent symlinking workflow.
