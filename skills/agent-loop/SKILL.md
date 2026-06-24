---
name: agent-loop
description: Separates doing from judging with independent audit review, state-based resumability, and bounded optimization. Use when work has high cost of silent errors, repeated correction, resumable review state, strict evidence requirements, or an explicit /agent-loop request.
---

# Agent Loop

Separate doing from judging. The main Agent plans, changes, fixes, and delivers; one audit Agent reviews evidence, writes verdicts, verifies readiness, and controls safe optimization.

Use existing planning first: Plan mode, `writing-plans`, or another suitable planning skill. If no usable plan exists, this skill writes the minimal contract before changing deliverables.

## Use

- Independent review is needed before delivery.
- A failed change would be costly, subtle, or hard to notice.
- The user asks for `/agent-loop`, multi-round review, final verification, or bounded optimization.
- Work may need recovery after interruption.

Do not use for one-shot answers, tiny edits, or tasks where a normal check is enough.

## State

| File | Owner | Purpose |
| --- | --- | --- |
| `state.md` | main | contract, progress, evidence, audit session tracker, recovery, baseline, delivery notes |
| `review.md` | audit | audit, appeals, verify, optimize triage, final verdict |
| `inbox.md` | main | optional unresolved items across tasks |

Create `state/<slug>/state.md` before changing deliverables. Use `references/contract-template.md` for the template. Load `references/plan-act-audit.md` only for exact formats, prompts, recovery routing, optimization rules, or downgrade behavior.

## Workflow

1. **PLAN**: reuse an existing plan when available; otherwise write `state.md` contract and checklist before deliverable changes. Present the contract to the user — goal, non-goals, assumptions, stop guardrails, checklist — and wait for explicit approval before ACT.
2. **USER_GATE**: main Agent must not proceed past PLAN until the user confirms the contract. No implicit approval.
3. **ACT**: main Agent executes only contracted work and records evidence.
4. **AUDIT**: spawn the audit Agent. Platform-specific spawn pattern: see Platform Notes below and `references/plan-act-audit.md`. The audit Agent checks plan quality first, then all six gates. Record the session ID in `state.md` `audit_session`.
5. **LOOP**: main Agent follows `CONTINUE_FIX` instructions or writes an evidence-backed appeal.
6. **VERIFY**: audit Agent validates every checklist item.
7. **BASELINE_LOCK**: main Agent records a baseline without changing deliverables.
8. **OPTIMIZE_LOOP**: optional and still owned by the same audit Agent. Do not create a separate optimizer Agent.
9. **FINAL_VERIFY**: audit Agent confirms baseline integrity and optimization stop reason.
10. **DELIVER**: main Agent summarizes evidence, clears `audit_session` from `state.md`, then removes process files that do not affect the deliverable.

## Review

`review.md` must decide `PROCEED_TO_VERIFY`, `CONTINUE_FIX`, or `STOP_WITH_BLOCKER`.

All six gates must pass:

- `contract`: goal, non-goals, assumptions, checklist, handoff, and recovery are checkable.
- `completeness`: the result satisfies the user goal without scope expansion.
- `correctness`: logic, edge cases, structure, and necessary simplicity are acceptable.
- `reuse_existing`: standard library, platform features, project code, or installed dependencies were preferred.
- `budget`: time, tools, agent calls, continuation value, and stop signals are recorded.
- `evidence_regression`: evidence exists and no known behavior was broken.

Second and later audits must close old issues first, then rerun all six gates.

## Instructions

The audit Agent returns targeted prompts to the main Agent:

- `fix_instruction`: target object, required change, forbidden change, and verification command/evidence.
- `optimize_instruction`: same shape, but only for safe optimization after baseline lock.

Only execute `OPTIMIZE_NOW` when expected gain is meaningful, cost is not high, risk is low, behavior does not regress, no new dependency is needed, and no user approval is required. Limited scope expansion is allowed only for a critical or required capability.

## Rules

- **One independent audit Agent per task.** The audit Agent must be a separate process from the main Agent. Role-switch (main Agent posing as auditor) is not an audit. Spawn a new process for each audit phase per the platform-specific pattern in `references/plan-act-audit.md`.
- **Context continuity across phases.** Each audit phase must inherit all prior verdicts: inject the full `review.md` content into the audit prompt. A fresh audit process without prior context starts blind — this is a workflow defect.
- **audit_session tracking.** Record all audit Agent session identifiers in `state.md` `audit_session` for traceability. Each section in `review.md` notes the agent ID that wrote it.
- **Clear on DELIVER.** Only after FINAL_VERIFY passes and evidence is summarized, clear `audit_session` from `state.md`.
- Main Agent may provide templates and handoff context, but must not write audit findings or final verdicts.
- Oral PASS is FAIL. Evidence must be file paths, diff summaries, command output, or deliverable paths.
- Scope control is part of strictness. Unrequested features go to notes or `state/inbox.md`, not blocking issues.
- Optimization candidates and `optimize_instruction` come only from the same audit Agent.
- After `BASELINE_LOCK`, risky, high-cost, scope-expanding, behavior-changing, or approval-needed optimization stops automatic execution.
- On `DELIVER`, summarize key evidence before deleting process state. Keep only the smallest required `state/inbox.md` when unresolved items remain.

## Platform Notes

Audit Agent spawn patterns are platform-specific. See `references/plan-act-audit.md` Platform Notes for per-platform procedures and the correct prompt format.

## Recovery

Before resuming, read `state/<slug>/state.md`, `review.md` if present, and `state/inbox.md` if present.

Route by state:

- `user-confirm` is non-empty -> ask the user first.
- Pending appeal -> resume the same audit Agent for ruling.
- Unfinished `next` fix -> apply it, updating the contract first if scope or checklist changed.
- `PROCEED_TO_VERIFY` -> send VERIFY to the same audit Agent.
- `VERIFIED` without baseline section in `state.md` -> append baseline lock.
- Optimization stopped or ineligible -> send FINAL_VERIFY.
- Final `VERDICT: VERIFIED` -> DELIVER.
- Blocker, hard limit, appeal deadlock, or low-value continuation -> stop and report.

## References

- `references/contract-template.md`: copy when creating `state.md`.
- `references/plan-act-audit.md`: full protocol, exact output formats, prompts, recovery details, optimization, and downgrade behavior.
- `references/runner-template.py`: experimental CLI helper; inspect platform parameters before use. Audit Agent session is tracked via `state.md` `audit_session`.
- `scripts/check_skill.py`: local static check for skill packaging.
