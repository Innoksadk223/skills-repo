---
name: using-superpowers
description: Use when starting any conversation or task to check whether relevant skills should guide the work before responding or acting.
---

# Using Method Skills Lightly

## Purpose

Use skills as small tools, not as ceremony. The goal is to pick the least process that protects the result.

## Trigger Rule

At the start of every user request, check whether a skill applies before answering, asking clarifying questions, reading files, or taking action.

You do not need ceremony, but you do need the check.

Use a method skill when the request involves creation, modification, uncertainty, verification, failure, multiple steps, or a named skill/tool. If no skill changes the work, proceed directly and keep the response simple.

## Routing Flow

1. State the real goal in one sentence when it helps.
2. Separate facts from assumptions.
3. Choose only skills that change the next action.
4. Put process skills before domain skills.
5. Use no more than one outer process unless the user explicitly asks for a loop or review.
6. Announce the chosen skills briefly when using them, then work.

## Common Routes

| Situation | Route |
| --- | --- |
| Vague idea or design choice | `brainstorming` |
| Multi-step work or handoff | `writing-plans` |
| Failure, bug, contradiction, or repeated attempt | `systematic-debugging` |
| Correctness can be defined before acting | `test-driven-development` |
| About to claim complete, fixed, ready, or passing | `verification-before-completion` |
| Need isolated workspace, delegated execution, or step-by-step plan execution | `writing-plans` |
| Need code review, review-feedback handling, merge/PR/cleanup, or final handoff | `verification-before-completion` |

## Priority

User instructions outrank skills. Skills guide how to work; they do not override the user's scope, language, safety constraints, or explicit "do not do X" instructions.

## Anti-Overuse

Do not invoke extra skills just because they exist. The check is mandatory; extra process is not. If no skill changes the next action, do the task.

## Folded Capabilities

These former standalone workflow skills are now internal capabilities:

| Former capability | Use through |
| --- | --- |
| executing a written plan | `writing-plans` -> Execution Mode |
| subagent-driven implementation | `writing-plans` -> Delegation Mode |
| git worktree isolation | `writing-plans` -> Isolation Mode |
| requesting code review | `verification-before-completion` -> Review Gate |
| receiving code review | `verification-before-completion` -> Feedback Triage |
| finishing a branch | `verification-before-completion` -> Finish Mode |

## Output Pattern

When skills matter, use a compact route:

```markdown
Task route:
1. skill-name -> why it changes the work
```

If no skill matters, do not produce a route section.
