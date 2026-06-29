# Hermes Agent Loop Protocol

Full AUDIT/VERIFY/OPTIMIZE/FINAL_VERIFY formats and recovery routing.

The maker executes deliverable changes and never writes `review.md`. The checker writes `review.md`; Hermes makes the final call.

- **Hermes executor mode**: worker session = maker; checker session = checker. Hermes reads `review.md`.
- **CC executor mode**: CC session = maker; **Hermes itself = checker** and writes `review.md` (Hermes never touches deliverables, so it can audit the CC maker without overlap).

## AUDIT

The checker reviews evidence against all six gates and writes `review.md`. In Hermes executor mode, resume the checker session to do this. In CC executor mode, Hermes performs the audit itself. Hermes then decides whether to proceed.

The checker must compare this round's issues against prior rounds. If an issue is identical or shares the same root cause as a previously reported issue that was supposedly fixed, use `ESCALATE_REPLAN` instead of `CONTINUE_FIX`. The current decomposition cannot resolve a recurring issue — the contract needs updating.

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
```

Proceed only when `ISSUE_COUNT: 0`, plan check passes, all gates pass, and evidence is checkable.

## LOOP

If `CONTINUE_FIX`, Hermes writes `fix_instruction` and delegates the fix to the worker (Hermes executor: resume worker session) or CC (resume session).

## VERIFY

The checker independently re-executes verification commands for each checklist item (Hermes executor: resume the checker session; CC executor: Hermes runs them itself). Must not rely on evidence recorded during OBSERVE.

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

## BASELINE, OPTIMIZE, FINAL_VERIFY

After VERIFY is `VERIFIED`, Hermes appends Baseline to `state.md` without changing deliverables.

Only execute `OPTIMIZE_NOW` when the candidate targets a real optimization (not a correctness issue), gain >=10%, cost is not high, risk is low, behavior does not regress, no new dependency is needed, no user approval is required, and baseline integrity remains checkable.

OPTIMIZE triage format:

```md
## OPTIMIZE Round N

OPTIMIZE_TRIAGE:
- candidate:
- dimension: functionality | conciseness | maintainability | usability | robustness | composability
  - functionality: missing necessary features, or unnecessary features to remove
  - conciseness: trim redundancy to improve token efficiency
  - maintainability: naming, structure, reuse
  - usability: beginner-friendly, fewer footguns, less mental overhead
  - robustness: error paths, dirty input, failure modes
  - composability: clean interfaces, clear boundaries, reusable parts
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

Read `state.md` and `review.md` if present.

- `user-confirm` non-empty -> ask the user.
- `state.md` next points to unfinished fix -> ACT.
- latest AUDIT is `ESCALATE_REPLAN` -> Hermes updates contract (re-decompose steps, adjust scope), then re-enters ACT. Two consecutive `ESCALATE_REPLAN` without progress -> upgrade to USER_GATE.
- latest AUDIT is `PROCEED_TO_VERIFY` -> VERIFY.
- latest VERIFY is `VERIFIED` and no Baseline in `state.md` -> BASELINE_LOCK.
- Baseline exists and optimization not stopped -> OPTIMIZE_LOOP.
- latest FINAL_VERIFY is `VERIFIED` -> DELIVER.
- Blocker, hard limit, or low-value continuation -> stop and report.

## DELIVER

Hermes summarizes from `state.md` and `review.md`: changed, why, checklist result, risks, and next step. Clear all session IDs (`worker_session`, `checker_session`, `cc_session`) from `state.md`. Then delete process files that do not affect the deliverable. Keep only minimal `state/inbox.md` when unresolved items remain.

## Token Budget Reference

Hermes reads `review.md` and makes the final call — no executor spawn overhead for this read step. AUDIT/VERIFY/OPTIMIZE costs are incurred by the executor, shown below.

| Phase | Per-phase cost | Notes |
|-------|---------------|-------|
| Read review.md | ~1K-2K tokens | Hermes reads checker's verdict |
| FINAL_VERIFY | ~1K-2K tokens | Baseline check only |
| Total (typical) | <5K tokens | Hermes overhead only; executor costs separate |

Hermes executor session costs (when used):

| Phase | Session | Per-phase cost | Notes |
|-------|---------|---------------|-------|
| ACT | worker | ~3K-10K tokens | Code execution; no turn limit |
| AUDIT | checker | ~2K-5K tokens | Six-gate review, writes `review.md` |
| LOOP | worker | ~2K-5K tokens | Targeted fixes |
| VERIFY | checker | ~1K-3K tokens | Re-runs verification commands |
| OPTIMIZE | worker | ~2K-5K tokens | Small scope changes |

Two independent cache chains — worker and checker each have their own prompt cache. Tight loops within each chain benefit most.

CC executor session costs (when used). Only ACT/LOOP/OPTIMIZE spawn CC; AUDIT/VERIFY/FINAL_VERIFY are Hermes's own work (the "Hermes overhead" table above):

| Phase | Owner | Per-phase cost | Notes |
|-------|-------|---------------|-------|
| ACT | CC | ~3K-10K tokens | `--max-turns 10`; includes code execution |
| AUDIT | Hermes | ~2K-5K tokens | Hermes audits CC output, writes `review.md`; no CC spawn |
| LOOP | CC | ~2K-5K tokens | `--max-turns 5` per fix round |
| VERIFY | Hermes | ~1K-3K tokens | Hermes re-runs verification commands; no CC spawn |
| OPTIMIZE | CC | ~2K-5K tokens | `--max-turns 5` |

**Prompt cache impact**: CC `--resume` reloads full conversation history as prefix. When the Anthropic prompt cache is valid (default 5 min TTL), cached prefix tokens cost ~10% of normal input. If expired, cache is rebuilt at 125% of normal input cost.
