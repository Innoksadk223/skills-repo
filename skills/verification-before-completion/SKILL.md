---
name: verification-before-completion
description: Use when about to claim work is complete, correct, fixed, ready, or passing, before committing, handoff, merge, PR, cleanup, or final delivery.
---

# Verification Before Completion

## Purpose

Make completion claims only after checking evidence. This skill also owns final review, review-feedback handling, and branch/work handoff after implementation.

## Gate

Before saying work is complete:

1. State the claim you are about to make.
2. Identify what evidence would prove it.
3. Run, inspect, render, or re-read the relevant artifact.
4. Compare evidence to the requested outcome.
5. Report the actual result, including gaps.

## Evidence Examples

| Claim | Evidence |
| --- | --- |
| Code works | tests, build, lint, or direct reproduction output |
| Bug fixed | original symptom no longer reproduces |
| Document is ready | rendered preview or checklist review |
| Data is correct | row counts, formulas, samples, source comparison |
| Research is supported | sources checked against claims |
| Plan is complete | requirements map to steps and checks |
| Sync is done | file counts, diffs, install preview, or path checks |
| Code is ready for review/merge | tests/checks, diff review, known risks, review findings handled |

## Freshness Rule

Fresh evidence is better than memory. If evidence is stale, partial, or unavailable, say that clearly and narrow the claim.

## Report Shape

```markdown
Verified:
- [claim] -> [evidence]

Not verified:
- [gap or skipped check] -> [reason/risk]
```

## Review Gate

Use before treating non-trivial code or configuration work as ready.

Review request shape:

```markdown
Objective:
Changed files:
Requirements / plan:
What to review for:
- correctness
- regressions
- missing tests
- edge cases
Verification already run:
Known concerns:
```

If a reviewer is available, provide focused context rather than full session history. Reusable templates in this skill directory:

- `code-reviewer.md`
- `code-quality-reviewer-prompt.md`

If no reviewer is available, self-review the diff against the same checklist and clearly label it as self-review.

## Feedback Triage

When receiving review feedback:

1. Read all feedback before changing anything.
2. Restate each item as a technical requirement.
3. Verify each item against the actual artifact.
4. Classify:
   - accept and fix;
   - accept but defer;
   - reject with evidence;
   - needs clarification.
5. Implement accepted items one at a time.
6. Verify each fix and check for regressions.

Do not perform broad refactors while addressing review unless the review item requires it.

## Finish Mode

Use when implementation is complete or paused at a stable checkpoint.

1. Check status: branch, changed files, untracked files.
2. Verify relevant tests/build/checklist.
3. Summarize changes and remaining risks.
4. Offer only appropriate next actions:
   - keep as-is;
   - commit;
   - push;
   - open PR;
   - merge;
   - clean up workspace/branch;
   - discard with explicit confirmation.
5. Perform only the action the user requested or approved.

Never delete a branch, worktree, or local changes until wanted changes are confirmed safe elsewhere.

## When Verification Cannot Run

Do not pretend. Report:

- the command or check you would run;
- why it could not run;
- what weaker evidence exists;
- what risk remains.

## Red Flags

- "Should work."
- "Looks done."
- "Probably fixed."
- Claiming success from a partial check.
- Trusting a generated report without reading artifacts.
- Moving on because the work feels finished.
