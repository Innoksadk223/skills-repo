---
name: systematic-debugging
description: Use when encountering any bug, failure, contradiction, unexpected behavior, or repeated failed attempt, before proposing fixes.
---

# Systematic Debugging

## Purpose

Find the cause before changing the solution. This works for code, tools, documents, data, workflows, and reasoning mistakes.

## Core Rule

Do not stack guesses. Make one hypothesis, test it, then decide.

## Flow

1. Capture the exact symptom.
   - Error text, wrong output, missing artifact, broken step, bad assumption, or user-visible mismatch.
2. Reproduce or collect evidence.
   - If reproduction is impossible, gather logs, examples, screenshots, diffs, source text, or before/after states.
3. Check recent changes.
   - Inputs, edits, environment, dependencies, instructions, deadlines, or assumptions.
4. Isolate the boundary.
   - Find where the expected state first becomes wrong.
5. Form one hypothesis.
   - "I think X causes Y because Z."
6. Test the smallest useful inspection or change.
7. Fix the root cause.
8. Verify the original symptom is gone.

## Evidence Map

| Problem type | Useful evidence |
| --- | --- |
| Code/test failure | failing command, stack trace, minimal reproduction |
| Tool failure | full command, cwd, env detail, version, raw error |
| Document mismatch | source text, rendered output, checklist item |
| Data issue | row counts, sample rows, schema, transformation step |
| Reasoning conflict | original claim, source, contradiction, assumption |

## Boundary Tracing

When multiple layers exist, inspect each boundary:

1. What enters this layer?
2. What exits this layer?
3. What changed inside?
4. Is the assumption still valid?

Stop tracing when you find the first layer where good input becomes bad output.

## Three-Fix Rule

After three failed fixes, stop and question the frame:

- Is the architecture or plan wrong?
- Is the evidence misleading?
- Is the requirement misunderstood?
- Is an external dependency involved?

Do not keep adding fixes without a new diagnosis.

## Review Feedback as Debugging

When feedback says something is wrong, treat it as a hypothesis:

1. Restate the claimed issue.
2. Locate the code, artifact, source, or behavior it refers to.
3. Verify whether the issue is real in this context.
4. If real, fix narrowly and verify.
5. If not real, push back with evidence.
6. If unclear, ask one focused question before changing anything.

This prevents blind implementation of bad advice and prevents dismissing valid feedback because it is inconvenient.

## Output Shape

```markdown
Symptom:
Evidence:
Hypothesis:
Test:
Root cause:
Fix:
Verification:
Remaining risk:
```

## Red Flags

- "Just try this."
- "It is probably..."
- Multiple changes before checking any result.
- Explaining a fix before explaining the cause.
- Treating symptom improvement as proof of root cause.
