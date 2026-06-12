---
name: test-driven-development
description: Use before implementing any feature, bugfix, behavior change, process document, generated artifact, or risky edit where success can be checked.
---

# Acceptance-First Work

## Purpose

Define success before doing the work. For code this may be a failing test. For non-code work it may be a checklist, example, render, source comparison, or sample run.

## Core Pattern

1. Name the behavior or outcome.
2. Create the smallest useful check.
3. Confirm the current state fails, lacks, or cannot yet satisfy that check when practical.
4. Make the smallest change that satisfies the check.
5. Run or apply the check again.
6. Refine only after the check passes.

## Code Mode

Use red-green-refactor when the codebase has a practical test path:

- Red: write a focused test and see it fail for the expected reason.
- Green: implement the smallest change that passes.
- Refactor: improve structure while keeping tests green.

If the codebase lacks tests, create the smallest reproducible check: a unit test, script, command, fixture, or manual reproduction with exact steps.

## Non-Code Mode

Use an acceptance check:

| Artifact | Check |
| --- | --- |
| Document | outline requirements, rendered preview, source-to-section checklist |
| Spreadsheet/data | row counts, formulas, sample rows, source comparison |
| Research answer | cited claims, source coverage, contradiction check |
| Plan | each requirement maps to a step and verification |
| Design | target audience, constraints, success criteria, tradeoff choice |

## Check Quality

A good check is:

- specific enough to fail;
- close to what the user cares about;
- cheap enough to run or inspect repeatedly;
- not tied to irrelevant implementation detail.

## Lightweight Exceptions

Exploration may come before checks. If useful work already exists without a prior check, do not delete it by default. Add the missing acceptance check, verify against it, and continue unless the user explicitly wants strict TDD.

## Output Shape

```markdown
Acceptance check:
Current result:
Change:
Verification:
```

## Red Flags

- Starting before knowing how success will be recognized.
- Expanding scope while trying to pass the check.
- Treating "looks fine" as verification.
- Keeping a check vague enough that anything could pass.
