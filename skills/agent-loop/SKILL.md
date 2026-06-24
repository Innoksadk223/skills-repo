---
name: agent-loop
description: Use when work has high cost of silent errors, repeated correction, resumable review state, strict evidence requirements, or an explicit /agent-loop request. Separates doing from judging with independent review, state-based resumability, and bounded optimization.
---

# Agent Loop

Separate doing from judging. The main Agent plans, changes, fixes, and delivers; one audit Agent reviews evidence, writes verdicts, verifies readiness, and controls safe optimization.

Use existing planning first: Plan mode, `writing-plans`, or another suitable planning skill. If no usable plan exists, this skill writes the minimal contract before changing deliverables.

## Use

When independent review is needed before delivery, a failed change would be costly/subtle/hard to notice, the user asks for `/agent-loop` or multi-round review, or work may need recovery after interruption. Skip for one-shot answers, tiny edits, or tasks where a normal check is enough.

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
3. **ACT**: main Agent executes only contracted work.
4. **OBSERVE**: main Agent reads and records real evidence — test output, diffs, logs, file contents — in `state.md` before handing off to audit. Do not rely on the ACT agent self-reported summary.
5. **AUDIT**: spawn the audit Agent. Platform-specific spawn pattern: see Platform Notes below and `references/plan-act-audit.md`. The audit Agent checks plan quality first, then all six gates. Record the session ID in `state.md` `audit_session`.
6. **LOOP**: main Agent follows `CONTINUE_FIX` instructions or writes an evidence-backed appeal.
7. **VERIFY**: audit Agent validates every checklist item.
8. **BASELINE_LOCK**: main Agent records a baseline without changing deliverables.
9. **OPTIMIZE_LOOP**: mandatory triage after baseline. The audit Agent scans for optimization candidates; if any qualify (`OPTIMIZE_NOW`), the main Agent executes them and the audit Agent re-verifies. Skip only when no candidates exist. Do not create a separate optimizer Agent.
10. **FINAL_VERIFY**: audit Agent confirms baseline integrity and optimization stop reason.
11. **DELIVER**: main Agent summarizes evidence, clears `audit_session` from `state.md`, then removes process files that do not affect the deliverable.

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

- **Maker-checker split.** The agent that produces the output must not be the agent that grades it. In Separate Audit Agent Mode, the audit Agent is an independent process. In Hermes Orchestrator Mode, Hermes is the checker and Claude Code is the maker — this IS a valid split. Self-review (same agent reviewing its own output) is not an audit. Spawn the audit Agent once with a fixed session ID recorded in `state.md` `audit_session`; resume the same session for all subsequent phases.
- **audit_session tracking.** Record the audit Agent session identifier in `state.md` `audit_session` at first spawn. Each section in `review.md` notes the session ID that wrote it.
- **Clear on DELIVER.** Only after FINAL_VERIFY passes and evidence is summarized: (1) terminate the actual audit session to prevent accidental cross-task resumption, (2) clear `audit_session` from `state.md`.
- Main Agent may provide templates and handoff context, but must not write audit findings or final verdicts.
- Oral PASS is FAIL. Evidence must be file paths, diff summaries, command output, or deliverable paths.
- Scope control is part of strictness. Unrequested features go to notes or `state/inbox.md`, not blocking issues.
- After `BASELINE_LOCK`, the audit Agent must triage for optimization candidates. `optimize_instruction` comes only from the audit Agent. Only execute `OPTIMIZE_NOW` when gain ≥10%, risk is low, no regression, no new deps, no user approval needed. Risky, high-cost, or scope-expanding optimization stops automatic execution; report the candidate and skip.
- On `DELIVER`, summarize key evidence before deleting process state. Keep only the smallest required `state/inbox.md` when unresolved items remain.

## Platform Notes

### Hermes Orchestrator Mode

When Hermes is the primary Agent, it handles PLAN + AUDIT + VERIFY in-process. All execution — ACT, fixes, and optimization — is delegated to Claude Code. No separate audit Agent process needed — Hermes is the reviewer.

- **Hermes**: PLAN (contract), AUDIT (review evidence), VERIFY (checklist), DELIVER — never executes deliverable changes
- **Claude Code**: all execution — contracted steps (ACT), fixes (LOOP), and optimization (OPTIMIZE) via `claude -p`

Key differences from standard mode:
- No independent audit Agent spawn; Hermes reviews in-process
- `review.md` simplified — checklist verdicts, issues, summary. Cross-agent handoff fields (agent IDs, VERIFY_HANDOFF, formal appeal protocol) dropped
- Claude Code invoked per step via `terminal(command="claude -p ...")`; stdout captured as evidence

Claude Code invocation: see `references/plan-act-audit.md` Platform Notes → Claude Code for the full invocation template (`-p`, `--allowedTools`, `--max-turns`).

Evidence loop:
1. Hermes writes step → Claude Code executes → stdout captured as evidence
2. OBSERVE: Hermes reads and records evidence in `state.md` — do not trust the executor self-report
3. Hermes audits against contract → writes `review.md`
4. Issues → `fix_instruction` → re-invoke Claude Code → re-audit
5. All gates pass → VERIFY → BASELINE
6. Hermes triages optimization candidates → if any qualify, Claude Code executes → Hermes re-verifies baseline; skip only when no candidates
7. FINAL_VERIFY → DELIVER

**Optimization (post-baseline):** follows Rules § optimization criteria. Hermes triages, writes `optimize_instruction`, Claude Code executes, Hermes re-verifies baseline.

### Separate Audit Agent Mode

Standard protocol where primary Agent and audit Agent are independent processes. The primary Agent handles PLAN + ACT; a separate audit process handles AUDIT + VERIFY + OPTIMIZE + FINAL_VERIFY. The audit Agent is a persistent session identified by `audit_session` in `state.md`; all phases resume the same session — no re-spawn per phase.

#### Common Pattern

1. Primary Agent writes `state.md` contract, gets user approval, executes contracted work (ACT).
2. AUDIT: spawn a headless audit process with a fixed session ID; record the ID in `state.md` `audit_session`.
3. VERIFY / OPTIMIZE / FINAL_VERIFY: **resume the same session** via platform-specific resume mechanism — do not re-spawn.
4. Audit process writes only to `review.md`; never touches deliverable files.
5. DELIVER: primary Agent terminates the audit session AND clears `audit_session` from `state.md` (prevents accidental cross-task resumption).

#### Claude Code as Primary

PLAN + ACT + LOOP: Claude Code executes natively. Fix rounds follow `fix_instruction` → re-invoke Claude Code.

Audit spawn (first phase) — generate a UUID first:
Audit: spawn with `--session-id` (UUID required — generate with `python3 -c "import uuid; print(uuid.uuid4())"`) + `--allowedTools` including `Write` for `review.md` output. Resume all subsequent phases with `--resume "$AUDIT_ID"`. See `references/plan-act-audit.md` Platform Notes → Claude Code for the full spawn template and audit prompt.

DELIVER: `-p` auto-exits. Clear `audit_session` from `state.md` — UUID gone, accidental resumption impossible.

#### Codex as Primary

PLAN + ACT + LOOP: Codex executes natively via `codex exec`. Fix rounds follow `fix_instruction` → re-invoke Codex.

Audit spawn (first phase):
Audit: spawn with `codex exec --yolo --skip-git-repo-check`. Subsequent phases: `codex exec resume --last`. Record session ID in `state.md` `audit_session`. See `references/plan-act-audit.md` Platform Notes → Codex for the full spawn template.

DELIVER: terminate audit session, clear `audit_session` from `state.md`.

#### Cross-Platform Audit

Any primary Agent may use any platform as the audit Agent — Claude Code, Codex, or Hermes. The audit Agent need not match the primary platform. See `references/plan-act-audit.md` Platform Notes for each platform spawn, resume, and cleanup syntax.

## Gotchas

- **Evidence trust**: The ACT agent self-reported summary is NOT evidence. Read test output, diffs, and logs yourself.
- **CC --session-id requires UUID**: `--session-id "audit-<slug>"` fails. Generate with `python3 -c "import uuid; print(uuid.uuid4())"`.
- **CC -p /exit is invalid**: /exit is interactive-only. -p auto-exits. Cleanup means clearing the UUID from state.md.
- **CC --allowedTools without Write**: The audit process cannot write review.md without Write. Add it and trust the prompt to guard deliverables.
- **CC per-file write restriction**: Not supported. The audit prompt instruction ("do not modify deliverables") is the only guard.
- **Codex session persistence**: Use `codex exec resume --last`, not a fresh spawn per phase.
- **Hermes Orchestrator mode**: Hermes reviews Claude Code output in-process. Maker (Claude Code) ≠ checker (Hermes). This IS a valid maker-checker split.
- **Self-review is not audit**: A fresh audit process without prior session context starts blind. Always --resume or inject prior review.md.

For full platform-specific fix instructions, see `references/plan-act-audit.md` Platform Notes.

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
