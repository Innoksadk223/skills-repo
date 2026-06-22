---
name: agent-loop
description: Use when work has high cost of silent errors, repeated correction, resumable review state, strict evidence requirements, bounded follow-up improvement, or an explicit /agent-loop request.
---

# Agent Loop

Separate doing from judging. The main Agent plans, executes, and fixes; one audit Agent reviews the contract, evidence, and final readiness.

## When to Use

- The task needs independent review before delivery.
- A failed change would be costly, subtle, or hard to notice.
- The user asks for `/agent-loop`, multi-round audit, final verification, or bounded optimization.
- Work may need recovery after interruption.

Do not use for one-shot answers, tiny edits, or tasks where a normal check is enough.

## Required Files

Create a task directory under `state/<slug>/`:

| File | Owner | Purpose |
| --- | --- | --- |
| `loop_contract.md` | main Agent | Goal, non-goals, assumptions, steps, handoff evidence, checklist, budget, recovery entry |
| `progress.md` | main Agent | done / tried / next / open / user-confirm / cost |
| `feedback.md` | audit Agent | PLAN check, six gates, issues, appeal rulings, verify handoff |
| `final_verify.md` | audit Agent | Checklist verdict before baseline lock |
| `baseline_lock.md` | main Agent | Deliverable fingerprint and rollback entry after VERIFIED |
| `final_deliver_verify.md` | audit Agent | Final verdict after any allowed optimization |

Use `references/contract-template.md` for the contract. Load `references/plan-act-audit.md` when exact formats, prompts, recovery routing, optimization, or downgrade rules are needed.

## Workflow

1. **PLAN**: write `loop_contract.md` and `progress.md` before changing deliverables.
2. **ACT**: main Agent executes only the contracted work and records evidence.
3. **AUDIT**: same audit Agent checks PLAN quality first, then six gates.
4. **LOOP**: main Agent applies `CONTINUE_FIX` instructions or writes an appeal with evidence.
5. **VERIFY**: audit Agent validates every checklist item.
6. **BASELINE_LOCK**: main Agent records a deliverable baseline without changing it.
7. **OPTIMIZE_LOOP**: optional, only from audit Agent instructions that meet the safety gate.
8. **FINAL_VERIFY**: audit Agent confirms baseline integrity and optimization stop reason.
9. **DELIVER**: main Agent summarizes result, then automatically removes process files that do not affect the deliverable.

## Audit Gates

`feedback.md` must decide `PROCEED_TO_VERIFY`, `CONTINUE_FIX`, or `STOP_WITH_BLOCKER`.

All gates must pass before verification:

- `contract`: goal, non-goals, assumptions, checklist, handoff, and recovery entry are checkable.
- `completeness`: the result satisfies the user goal without scope expansion.
- `correctness`: logic, edge cases, structure, and necessary simplicity are acceptable.
- `reuse_existing`: standard library, platform features, project code, or installed dependencies were preferred.
- `budget`: time, tools, agent calls, continuation value, and stop signals are recorded.
- `evidence_regression`: evidence exists and no known behavior was broken.

Second and later audits must close old issues first, then rerun all six gates.

## Hard Rules

- One active audit Agent per conversation/thread. Reuse it for the loop; never persist audit Agent IDs in files.
- The main Agent may send fixed audit templates and handoff context, but must not write audit findings or final verdicts.
- `fix_instruction` must be executable: target object, required change, forbidden change, and verification command/evidence.
- Oral PASS is FAIL. Evidence must be file paths, diff summaries, command output, or deliverable paths.
- Scope control is part of strictness. Unrequested features belong in notes or `state/inbox.md`, not blocking issues.
- Optimization candidates and `optimize_instruction` come only from the same audit Agent.
- After `BASELINE_LOCK`, any risky, high-cost, scope-expanding, behavior-changing, or approval-needed optimization stops automatic execution.
- On `DELIVER`, summarize key evidence before automatically deleting process files. Keep only the smallest required `state/inbox.md` when unresolved items remain.

## Recovery

Before resuming, read:

1. `state/<slug>/loop_contract.md`
2. `state/<slug>/progress.md`
3. `state/inbox.md` if present

Then route by state:

- `user-confirm` is non-empty -> ask the user first.
- pending appeal -> resume the same audit Agent for appeal ruling.
- unfinished `next` fix -> apply the fix, updating contract first if scope or checklist changed.
- `PROCEED_TO_VERIFY` -> send VERIFY to the same audit Agent.
- `VERIFIED` without `baseline_lock.md` -> write baseline lock.
- optimization stopped or ineligible -> send FINAL_VERIFY.
- final `VERDICT: VERIFIED` -> DELIVER.
- blocker, hard limit, appeal deadlock, or low-value continuation -> stop and report.

## References

- `references/contract-template.md`: copy when creating `loop_contract.md`.
- `references/plan-act-audit.md`: full protocol, exact output formats, prompts, recovery details, optimization, and downgrade behavior.
- `references/runner-template.py`: experimental CLI helper; inspect platform parameters before use and never persist audit Agent IDs.
- `scripts/check_skill.py`: local static check for skill packaging.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Starting ACT without a contract | Stop and write `loop_contract.md` plus `progress.md`. |
| Replacing audit with self-review | Use the audit Agent or explicit downgrade protocol from the reference. |
| Creating a new audit Agent each round | Reuse the active audit conversation/thread. |
| Treating optimization as required fixes | Only execute safe `OPTIMIZE_NOW`; otherwise defer or stop. |
| Keeping process files after delivery | Summarize first, then clean process state automatically unless unresolved items must remain. |
