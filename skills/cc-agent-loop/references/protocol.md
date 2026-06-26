# CC Agent Loop Protocol

Full AUDIT/VERIFY/OPTIMIZE/FINAL_VERIFY formats, appeal protocol, and recovery routing for Claude Code.

## AUDIT

Audit CC must be the same persistent session for the entire task — one spawn, reused across all rounds via `--resume`.

Prompt:

```text
You are the independent audit Agent. Review only; do not modify deliverables.

Read state/<slug>/state.md, review.md if present, state/inbox.md if present, and appeal.md if present.
First check PLAN quality. On later rounds, close old issues before checking new ones.
Run all six gates: contract / completeness / correctness / reuse_existing / budget / evidence_regression.
Append an AUDIT section to state/<slug>/review.md.

Decision may be PROCEED_TO_VERIFY, CONTINUE_FIX, ESCALATE_REPLAN, or STOP_WITH_BLOCKER.
Any fix_instruction must name the target object, required change, forbidden change, and verification evidence.
Scope suggestions outside the user goal do not count as blocking issues.

STALL_DETECTION: compare this round's issues against prior rounds. If an issue is identical or shares the same root cause as a previously reported issue that was supposedly fixed, flag it here. Use ESCALATE_REPLAN when the same issue class has recurred 2+ rounds — the current decomposition cannot resolve it and the contract needs updating.
```

AUDIT section format:

```md
## AUDIT Round N

DECISION: PROCEED_TO_VERIFY | CONTINUE_FIX | ESCALATE_REPLAN | STOP_WITH_BLOCKER
ISSUE_COUNT: <number>

STALL_DETECTION:
- recurring_issue: NONE | <issue number from prior round>
- similarity: N/A | IDENTICAL | SAME_ROOT_CAUSE | NEW_ISSUE
- rounds_recurring: 0 | <count>
- notes:

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

If `CONTINUE_FIX`, the primary CC follows each `fix_instruction` or writes `appeal.md`.

Appeal format:

```md
## [APPEAL] issue id
original_instruction:
reason:
counter_evidence:
```

Audit CC rules:

- `UPHELD`: instruction stands.
- `OVERRULED`: instruction is removed and does not count as a fix round.
- `CLARIFIED`: rewrite the instruction into a more precise targeted prompt.

Stop on hard limit, blocker, low-value continuation, or two appeal-only rounds with no real fix.

## VERIFY

Same audit CC independently re-executes verification commands for each checklist item after `PROCEED_TO_VERIFY`. The audit CC must not rely on evidence recorded during OBSERVE — it runs the commands itself and records the actual output.

Verify prompt:

```text
Continue as audit Agent. Independently verify each checklist item.
For each item, run the verification command yourself and record the raw output.
Do not rely on evidence recorded during OBSERVE.
Append a VERIFY section to state/<slug>/review.md.
```

VERIFY section format:

```md
## VERIFY

VERDICT: VERIFIED | RETURN_TO_LOOP | STOP_WITH_BLOCKER

CHECKLIST:
1. item:
   verdict: PASS | FAIL
   verification_command: <exact command run>
   actual_output: <raw terminal output or summary>
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

After VERIFY is `VERIFIED`, primary CC appends Baseline to `state.md` without changing deliverables.

Only execute `OPTIMIZE_NOW` when the candidate targets a real optimization (not a correctness issue), gain >=10%, cost is not high, risk is low, behavior does not regress, no new dependency is needed, no user approval is required, and baseline integrity remains checkable.

OPTIMIZE triage format:

```md
## OPTIMIZE Round N

OPTIMIZE_TRIAGE:
- candidate:
- dimension: functionality | conciseness | maintainability | usability
  - functionality: missing necessary features, or unnecessary features to remove
  - conciseness: trim redundancy to improve token efficiency
  - maintainability: naming, structure, reuse
  - usability: beginner-friendly, fewer footguns, less mental overhead
- expected_gain:
- cost:
- risk:
- affects_baseline:
- needs_user_approval:
- decision: OPTIMIZE_NOW | DEFER_TO_INBOX | STOP_OPTIMIZING
- optimize_instruction:
- reason:
```

Final verification:

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
- pending `appeal.md` -> same audit CC rules on appeal.
- Latest AUDIT is `ESCALATE_REPLAN` -> primary CC updates contract (re-decompose steps, adjust scope), then re-enters ACT. Two consecutive `ESCALATE_REPLAN` without progress -> upgrade to USER_GATE.
- `state.md` next points to unfinished fix -> ACT.
- latest AUDIT is `PROCEED_TO_VERIFY` -> VERIFY.
- latest VERIFY is `VERIFIED` and no Baseline in `state.md` -> BASELINE_LOCK.
- Baseline exists and optimization not stopped -> OPTIMIZE_LOOP.
- latest FINAL_VERIFY is `VERIFIED` -> DELIVER.
- blocker, hard limit, appeal deadlock, or low-value continuation -> stop and report.

## DELIVER

Primary CC summarizes from `state.md` and `review.md`: changed, why, checklist result, risks, and next step. Clear `audit_session` from `state.md`. Then delete process files that do not affect the deliverable. Keep only minimal `state/inbox.md` when unresolved items remain.

## Token Budget Reference

Approximate per-phase token costs for the audit CC process:

| Phase | Per-phase cost | Notes |
|-------|---------------|-------|
| AUDIT | ~3K-8K tokens | `--max-turns 5`; each turn ~600-1600 tokens |
| VERIFY | ~2K-6K tokens | `--max-turns 3`; mostly Bash execution |
| FINAL_VERIFY | ~1K-3K tokens | `--max-turns 3`; baseline check only |
| Total (typical) | <20K tokens | Stop condition is checklist completion, not token exhaustion |

Set `--max-turns 5` for AUDIT, 3 for VERIFY/FINAL_VERIFY. If a phase nears its turn cap without resolution, report evidence and escalate — do not blindly raise the cap.

**Prompt cache impact**: `--resume` reloads full conversation history as prefix. When the Anthropic prompt cache is valid (default 5 min TTL), cached prefix tokens cost ~10% of normal input. If expired, cache is rebuilt at 125% of normal input cost. Consecutive phases within minutes benefit most; long gaps may exceed TTL and trigger cache rebuild.
