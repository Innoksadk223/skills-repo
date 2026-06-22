# Agent Loop Protocol

`SKILL.md` keeps the short rules. Load this file only when exact state shape, prompts, recovery routing, optimization, or downgrade behavior is needed.

## Files

Mandatory per task:

- `state/<slug>/state.md` - main Agent writes contract, progress, evidence, baseline, delivery notes.
- `state/<slug>/review.md` - audit Agent writes audit, appeal rulings, verify, optimize, final verdict.

Optional:

- `state/inbox.md` - main Agent writes unresolved cross-task items.
- `state/<slug>/appeal.md` - main Agent writes evidence-backed appeals.

The audit Agent never writes `state.md`; the main Agent never writes audit verdicts in `review.md`.

## PLAN

PLAN is the ACT gate. Reuse Plan mode, `writing-plans`, or another suitable planning skill first. If no usable plan exists, copy `references/contract-template.md` to `state/<slug>/state.md`.

`state.md` must contain: goal, completion criteria, non-goals, assumptions, plan source, steps, checklist, progress, evidence slots, recovery route, budget/cost, and audit Agent scope.

Second and later rounds write only a Plan Delta in `state.md` when goal, scope, checklist, handoff, or recovery changes.

## ACT

Main Agent:

- reads `state.md` and latest `review.md`;
- executes only contracted work;
- records evidence and cost in `state.md`;
- writes `state/inbox.md` only for user confirmation, blockers, hard limits, low-value pauses, or deferred risks;
- does not change submitted deliverables while the audit Agent is reviewing them.

## AUDIT

Audit Agent must be the same active audit Agent for the conversation/thread. Do not persist audit Agent IDs in files.

Prompt:

```text
You are the independent audit Agent. Review only; do not modify deliverables.

Read state/<slug>/state.md, review.md if present, state/inbox.md if present, and appeal.md if present.
First check PLAN quality. On later rounds, close old issues before checking new ones.
Run all six gates: contract / completeness / correctness / reuse_existing / budget / evidence_regression.
Append an AUDIT section to state/<slug>/review.md.

Decision may be PROCEED_TO_VERIFY, CONTINUE_FIX, or STOP_WITH_BLOCKER.
Any fix_instruction must name the target object, required change, forbidden change, and verification evidence.
Scope suggestions outside the user goal do not count as blocking issues.
```

AUDIT section:

```md
## AUDIT Round N

DECISION: PROCEED_TO_VERIFY | CONTINUE_FIX | STOP_WITH_BLOCKER
ISSUE_COUNT: <number>

PLAN_CHECK:
- verdict: PASS | FAIL
- evidence:
- notes:

GATES:
- contract: PASS | FAIL
- completeness: PASS | FAIL
- correctness: PASS | FAIL
- reuse_existing: PASS | FAIL
- budget: PASS | FAIL
- evidence_regression: PASS | FAIL

ISSUES:
1. failure_type: logic_error | requirement_gap | missing_edge_case | regression | quality_issue | reinventing_existing | budget_issue | missing_skill | weak_validation | external_blocker
   severity: blocker | major | minor
   evidence:
   fix_instruction:

APPEALS:
- item:
  ruling: UPHELD | OVERRULED | CLARIFIED
  reason:

VERIFY_HANDOFF:
- checklist_items_ready:
- evidence_paths:
- unresolved:
```

Proceed only when `ISSUE_COUNT: 0`, plan check passes, all gates pass, unresolved is empty, and evidence is checkable.

## LOOP and Appeals

If `CONTINUE_FIX`, the main Agent follows each `fix_instruction` or writes `appeal.md`.

Appeal format:

```md
## [APPEAL] issue id
original_instruction:
reason:
counter_evidence:
```

Audit Agent rules:

- `UPHELD`: instruction stands.
- `OVERRULED`: instruction is removed and does not count as a fix round.
- `CLARIFIED`: rewrite the instruction into a more precise targeted prompt.

Stop on hard limit, blocker, low-value continuation, or two appeal-only rounds with no real fix.

## VERIFY

Same audit Agent validates checklist items after `PROCEED_TO_VERIFY`. Append to `review.md`:

```md
## VERIFY

VERDICT: VERIFIED | RETURN_TO_LOOP | STOP_WITH_BLOCKER

CHECKLIST:
1. item:
   verdict: PASS | FAIL
   evidence:

OPEN_ISSUES:
- failure_type:
  evidence:
  fix_instruction:

DELIVERABLE_SUMMARY:
- changed:
- why:
- risks_or_limits:
- user_should_know:
```

`VERIFIED` routes to BASELINE_LOCK. `RETURN_TO_LOOP` routes to LOOP. `STOP_WITH_BLOCKER` routes to report.

## BASELINE, OPTIMIZE, FINAL_VERIFY

After VERIFY is `VERIFIED`, main Agent appends Baseline to `state.md` without changing deliverables.

Optimization is optional and controlled by the same audit Agent. It is not a second audit and does not get a separate optimizer Agent.

Only execute `OPTIMIZE_NOW` when expected gain is >=10%, cost is not high, risk is low, behavior does not regress, no new dependency is needed, no user approval is required, and baseline integrity remains checkable. Limited scope expansion is allowed only for `critical_capability`; otherwise defer to `state/inbox.md` or stop.

Append optimization decisions to `review.md`:

```md
## OPTIMIZE Round N

OPTIMIZE_TRIAGE:
- candidate:
- lens: critical_capability | human_usability | agent_efficiency | workflow_smoothness | recovery_delivery_experience
- expected_gain:
- cost:
- risk:
- affects_baseline:
- needs_user_approval:
- decision: OPTIMIZE_NOW | DEFER_TO_INBOX | STOP_OPTIMIZING
- optimize_instruction:
- reason:
```

`critical_capability` means adding a key or required function. It may modestly exceed the user's stated request when needed for the deliverable to be genuinely useful or complete.

Final verification appends:

```md
## FINAL_VERIFY

VERDICT: VERIFIED | RETURN_TO_BASELINE | STOP_WITH_BLOCKER

BASELINE:
- integrity: PASS | FAIL
- evidence:

OPTIMIZATION:
- rounds:
- stop_reason:
- unresolved:

DELIVERABLE_SUMMARY:
- changed:
- why:
- risks_or_limits:
- user_should_know:
```

## RESUME

Read `state.md`, latest `review.md`, and `state/inbox.md` if present.

- `user-confirm` non-empty -> ask the user.
- pending `appeal.md` -> same audit Agent rules on appeal.
- `state.md` next points to unfinished fix -> ACT.
- latest AUDIT is `PROCEED_TO_VERIFY` -> VERIFY.
- latest VERIFY is `VERIFIED` and no Baseline in `state.md` -> BASELINE_LOCK.
- Baseline exists and optimization not stopped -> OPTIMIZE_LOOP.
- latest FINAL_VERIFY is `VERIFIED` -> DELIVER.
- blocker, hard limit, appeal deadlock, or low-value continuation -> stop and report.

## DELIVER

Main Agent summarizes from `state.md` and `review.md`: changed, why, checklist result, risks, and next step. Then delete process files that do not affect the deliverable. Keep only minimal `state/inbox.md` when unresolved items remain.

## Platform Notes

Kanban or CLI adapters may persist tasks/results, but not audit Agent identity. If no subagent or CLI reviewer is available, explicitly downgrade to local role-switch review in `review.md`.
