---
name: codex-agent-loop
description: "Use when work has high cost of silent errors, repeated correction, resumable review state, strict evidence requirements, or an explicit /agent-loop request. Separates doing from judging with independent review, persistent session-based resumability, and bounded optimization. This is the Codex version."
---

# Codex Agent Loop

Separate doing from judging. The primary Codex handles PLAN, ACT, fixes, and delivery. An audit subagent — spawned within the same Codex session as a child thread — reviews evidence, writes verdicts, verifies readiness, and controls safe optimization.

Use existing planning first: Plan mode, `writing-plans`, or another suitable planning skill. If no usable plan exists, write the minimal contract before changing deliverables.

## Use

When independent review is needed before delivery, a failed change would be costly/subtle/hard to notice, the user asks for `/agent-loop` or multi-round review, or work may need recovery after interruption. Skip for one-shot answers, tiny edits, or tasks where a normal check is enough.

## State

| File | Owner | Purpose |
| --- | --- | --- |
| `state.md` | primary Codex | contract, progress, evidence, session tracker, recovery, baseline, delivery notes |
| `review.md` | audit subagent | audit, appeals, verify, optimize triage, final verdict |
| `inbox.md` | primary Codex | optional unresolved items across tasks |

Create `state/<slug>/state.md` before changing deliverables. Use `references/contract-template.md` for the template. Load `references/protocol.md` for exact AUDIT/VERIFY/OPTIMIZE formats, spawn templates, and recovery routing.

## Workflow

```
PLAN → USER_GATE → ACT → OBSERVE
                        │
          ┌─────────────┘
          ▼
   ┌── AUDIT ←─────────────────┐
   │    │ CONTINUE_FIX         │
   │    ▼                      │
   │  LOOP → ACT → OBSERVE ────┘
   │    │ PROCEED_TO_VERIFY
   │    ▼
   │  VERIFY
   │    │
   │    ▼
   │  BASELINE_LOCK
   │    │
   │    ▼
   │  OPTIMIZE_LOOP ──────────┐
   │    │ triage → execute    │
   │    ▼                     │
   └── AUDIT(re-verify) ──────┘
        │ PROCEED
        ▼
   FINAL_VERIFY → DELIVER
```

两个审查循环：**正确性循环**（AUDIT → LOOP → ACT → AUDIT，修到无 issue）和 **优化循环**（OPTIMIZE_LOOP → AUDIT 复验，确认优化安全）。

1. **PLAN**: reuse an existing plan when available; otherwise write `state.md` contract and checklist before deliverable changes. Present the contract to the user — goal, non-goals, assumptions, stop guardrails, checklist — and wait for explicit approval before ACT.
2. **USER_GATE**: primary Codex must not proceed past PLAN until the user confirms the contract. No implicit approval.
3. **ACT**: primary Codex executes only contracted work. If the checklist contains testable items (tests, lint, typecheck, build), run the corresponding verification commands and record raw output before handoff.
4. **OBSERVE**: primary Codex reads and records real evidence — test output, diffs, logs, file contents — in `state.md` before handing off to audit. Do not rely on the ACT agent self-reported summary. If tests were run in ACT, record the exact commands and raw terminal output, not paraphrased results.
5. **AUDIT**: spawn the audit subagent via natural language prompt within the Codex session. Record the session ID in `state.md` `audit_session`. The audit subagent checks plan quality first, then all six gates. Writes results to `review.md`.
6. **LOOP**: primary Codex follows `CONTINUE_FIX` instructions or writes an evidence-backed appeal. If the audit subagent returns `ESCALATE_REPLAN` (stall detected — same issue recurs across rounds), primary Codex drafts a contract update (re-decompose steps, adjust scope) and presents it to the user — the contract must not be modified without user confirmation. After user approval, re-enter ACT. Two consecutive `ESCALATE_REPLAN` without progress → report to user and stop.
7. **VERIFY**: audit subagent independently re-executes verification commands for each checklist item. Records the actual command and raw output in `review.md`.
8. **BASELINE_LOCK**: primary Codex records a baseline without changing deliverables.
9. **OPTIMIZE_LOOP**: mandatory triage after baseline. Pre-scan changed + adjacent files (pre-scan evidence gate applies — see Rules). Triage across four dimensions (see `references/protocol.md`); each dimension gets its own block with `NO_CANDIDATE` + one-line reason if none. **Primary Codex zero-candidate review**: reviews `OPTIMIZE_TRIAGE` only when ALL four report `NO_CANDIDATE`; insufficient reasons → reject and re-scan. Primary Codex executes `OPTIMIZE_NOW`, audit subagent re-verifies. Present `SUGGEST_TO_USER` to user. Skip only when zero candidates and review passes.
10. **FINAL_VERIFY**: audit subagent confirms baseline integrity and optimization stop reason.
11. **DELIVER**: primary Codex summarizes evidence and presents the deliverable. Session IDs and process files must not be modified or removed without user confirmation — the user decides when to clean up.

## Review

`review.md` must decide `PROCEED_TO_VERIFY`, `CONTINUE_FIX`, `ESCALATE_REPLAN`, or `STOP_WITH_BLOCKER`.

All six gates must pass:

- `contract`: goal, non-goals, assumptions, checklist, handoff, and recovery are checkable.
- `completeness`: the result satisfies the user goal without scope expansion.
- `correctness`: logic, edge cases, structure, and necessary simplicity are acceptable.
- `reuse_existing`: standard library, platform features, project code, or installed dependencies were preferred.
- `budget`: time, tools, agent calls, continuation value, and stop signals are recorded.
- `evidence_regression`: evidence exists and no known behavior was broken.

Second and later audits must close old issues first, then rerun all six gates.

## Rules

- **Maker-checker split.** The Codex thread that produces the output must not be the thread that grades it. The audit subagent is a separate agent thread with its own context. Self-review is not an audit.
- **audit_session tracking.** Record the Codex session ID in `state.md` `audit_session` at first spawn. The audit subagent runs as a child thread within this session — use `codex exec resume "$AUDIT_SESSION_ID"` to resume the session after interruption.
- Primary Codex may provide templates and handoff context, but must not write audit findings or final verdicts.
- Oral PASS is FAIL. Evidence must be file paths, diff summaries, command output, or deliverable paths.
- Scope control is part of strictness. Unrequested features go to notes or `state/inbox.md`, not blocking issues.
- After `BASELINE_LOCK`, pre-scan changed + adjacent files in the skill/module directory, record the file list as evidence, then triage across four dimensions (see `references/protocol.md`); each dimension gets its own block in `OPTIMIZE_TRIAGE`. Pre-scan evidence is mandatory — if the scanned file list is empty or missing, reject and re-scan. Primary Codex reviews `OPTIMIZE_TRIAGE` only when ALL four dimensions report `NO_CANDIDATE`; insufficient reasons → reject and re-scan. Execute `OPTIMIZE_NOW` only when gain >=5%, risk is low, no regression, no new deps, no user approval needed. `enrichment` dimension candidates bypass `OPTIMIZE_NOW` — always use `SUGGEST_TO_USER` with user confirmation required.
- On `DELIVER`, summarize key evidence. Do not delete process files or modify `state.md` without user confirmation. Keep `state/inbox.md` when unresolved items remain.

## Codex Subagent Management

### Audit Subagent Spawn

Codex spawns subagents via natural language prompt — no CLI flag needed. Within the Codex session, instruct:

```text
Spawn a subagent to audit the work. Use the "reviewer" custom agent if available.

The audit subagent must:
- Read state/<slug>/state.md and review.md (if present)
- Check PLAN quality first, then run all six gates
- Append AUDIT section to state/<slug>/review.md
- Decision: PROCEED_TO_VERIFY | CONTINUE_FIX | ESCALATE_REPLAN | STOP_WITH_BLOCKER
- Do NOT modify deliverable files — only write to review.md
```

After spawn, capture the session ID from Codex output or `~/.codex/sessions/`. Record it in `state.md` `audit_session`.

### Custom Audit Agent (recommended)

Define a dedicated audit agent in `~/.codex/agents/reviewer.toml`:

```toml
name = "reviewer"
description = "Independent audit agent for agent-loop review. Read-only."
model = "gpt-5.4"
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = """
Review code like an owner.
Prioritize correctness, security, behavior regressions, and missing test coverage.
Write findings only to review.md. Do not modify deliverable files.
"""
```

`sandbox_mode = "read-only"` prevents the audit subagent from modifying deliverables at the sandbox level — stronger than prompt-only restriction.

### Subagent Steering

Use `/agent` in the CLI to switch between the primary thread and the audit subagent thread. Ask Codex directly to steer the subagent, stop it, or close completed threads.

### Session Resume

If the Codex session is interrupted, resume with the explicit session ID:

```bash
codex exec resume "$AUDIT_SESSION_ID" "Continue the agent-loop workflow."
```

`resume "$AUDIT_SESSION_ID"` restores the full conversation history including all subagent threads. The session ID is stored under `~/.codex/sessions/`.

### Session ID Discovery

```bash
ls -t ~/.codex/sessions/ | head -1
```

Or capture from Codex output at spawn time.

## Gotchas

- **Stall detection**: `ESCALATE_REPLAN` is not a softer `STOP_WITH_BLOCKER` — it means the audit subagent sees the same issue class recur across fix rounds and the current decomposition cannot resolve it. Primary Codex drafts a contract update (re-decompose steps, adjust scope), presents it to the user for confirmation, then re-enters ACT. If the contract is unchanged and ACT is re-entered, it will loop again on the same issue.
- **Evidence trust**: The ACT agent self-reported summary is NOT evidence. Read test output, diffs, and logs yourself.
- **Subagent inherits sandbox**: The audit subagent inherits the parent session's sandbox policy. Set `sandbox_mode = "read-only"` in the custom agent file to prevent deliverable modification — this is stronger than prompt-only restriction.
- **Codex only spawns subagents when asked**: Subagent workflows are not automatic. The primary Codex must explicitly instruct "spawn a subagent" to trigger the audit thread.
- **Self-review is not audit**: A fresh subagent without prior context starts blind. Always resume the session or inject prior `review.md`.
- **VERIFY must re-run tests**: Reading OBSERVE evidence is not verification. The audit subagent must independently execute the checklist's verification commands and record raw output.
- **Session ID precision**: Use `codex exec resume "$AUDIT_SESSION_ID"`, not `--last` — `--last` resumes whatever was most recent, not necessarily the agent-loop session.
- **Codex --resume context accumulation**: Each `codex exec resume` reloads full conversation history. Processing time grows with every resume. No hard timeout — let the call complete naturally. If a call hangs, the orchestrator can kill it manually.

For full protocol formats and recovery routing, see `references/protocol.md`.

## Recovery

Before resuming, read `state/<slug>/state.md`, `review.md` if present, and `state/inbox.md` if present.

Route by state:

- `user-confirm` is non-empty -> ask the user first.
- Pending appeal -> resume the same Codex session and steer the audit subagent for ruling.
- Unfinished `next` fix -> apply it, updating the contract first if scope or checklist changed.
- `ESCALATE_REPLAN` -> primary Codex drafts contract update, presents to user for confirmation before modifying `state.md`. After approval, re-enter ACT. Two consecutive `ESCALATE_REPLAN` without progress -> report to user and stop.
- `PROCEED_TO_VERIFY` -> send VERIFY to the audit subagent.
- `VERIFIED` without baseline section in `state.md` -> append baseline lock.
- Baseline exists and optimization not started -> OPTIMIZE_LOOP.
- OPTIMIZE changes applied and not yet re-audited -> AUDIT (audit subagent re-verifies the optimization).
- Optimization stopped or ineligible -> send FINAL_VERIFY.
- Final `VERDICT: VERIFIED` -> DELIVER.
- Blocker, hard limit, appeal deadlock, or low-value continuation -> stop and report.

## References

- `references/contract-template.md`: copy when creating `state.md`.
- `references/protocol.md`: full AUDIT/VERIFY/OPTIMIZE/FINAL_VERIFY formats, appeal protocol, optimization triage, and recovery routing.
