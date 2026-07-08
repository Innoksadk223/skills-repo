---
name: hermes-agent-loop
description: "Use when work has high cost of silent errors, repeated correction, resumable review state, strict evidence requirements, or an explicit /agent-loop request. Separates doing from judging with independent review, persistent session-based resumability, and bounded optimization. This is the Hermes version."
---

# Hermes Agent Loop

Separate doing from judging. Hermes orchestrates PLAN, USER_GATE, OBSERVE, LOOP decisions, BASELINE, and DELIVER, and never changes deliverables itself. The **maker** (execution) is delegated to an executor mode chosen at PLAN. The **checker** (audit/verify) is an independent session in Hermes executor mode, or Hermes itself in CC executor mode — never the maker. The executor mode must be chosen at PLAN; there is no in-process fallback.

**CRITICAL — do not use `delegate_task` for execution or checking.** `delegate_task` spawns one-shot subagents: the conversation ends when the task completes, and the session cannot be resumed with `--resume`. When the checker finds a gap and LOOP is needed, you must send the fix back to the *same* agent that has prior context — a `delegate_task` subagent is already gone. The executor and checker MUST be persistent sessions spawned via `terminal` (`hermes -z --pass-session-id` for Hermes mode, `claude -p --session-id` for CC mode), so they can be resumed with `--resume` across all phases. Using `delegate_task` breaks LOOP, VERIFY, and OPTIMIZE — the entire multi-round review design depends on session persistence.

Use existing planning first: Plan mode, `writing-plans`, or another suitable planning skill. If no usable plan exists, write the minimal contract before changing deliverables.

## Use

When independent review is needed before delivery, a failed change would be costly/subtle/hard to notice, the user asks for `/agent-loop` or multi-round review, or work may need recovery after interruption. Skip for one-shot answers, tiny edits, or tasks where a normal check is enough.

## Mode Selection

Choose at PLAN. No default — the user must pick one.

- **Hermes executor mode**: Hermes spawns two independent `hermes -z` sessions — a worker (maker: execution) and a checker (audit/verify). Both persist via `--resume`. Use when you want Hermes-native two-agent separation with persistent multi-round memory on both sides.
- **CC executor mode**: Hermes is the orchestrator and the checker; a single CC session is the maker (execution only). Hermes audits and verifies the CC output itself — the maker never reviews its own work. Use for most coding tasks where CC handles code execution.

## State

| File | Owner | Purpose |
| --- | --- | --- |
| `state.md` | Hermes | contract, progress, evidence, executor session tracker, recovery, baseline, delivery notes |
| `review.md` | checker (checker session in Hermes mode; Hermes in CC mode) | audit verdicts, verify, optimize triage, final verdict |
| `inbox.md` | Hermes | optional unresolved items across tasks |

Create `state/<slug>/state.md` before changing deliverables. Use `references/contract-template.md` for the template. Load the executor-mode reference for session management and invocation templates.

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
2. **USER_GATE**: Hermes must not proceed past PLAN until the user confirms the contract. No implicit approval.
3. **ACT**: delegate execution to the chosen executor via a persistent session (`terminal` → `hermes -z --pass-session-id` or `claude -p --session-id`). Do NOT use `delegate_task` — it is one-shot and cannot be resumed. If the checklist contains testable items, run the corresponding verification commands and record raw output before handoff.
4. **OBSERVE**: Hermes reads and records real evidence — test output, diffs, logs, file contents — in `state.md`. Do not rely on the executor self-reported summary. If tests were run in ACT, record the exact commands and raw terminal output, not paraphrased results.
5. **AUDIT**: the checker reviews evidence against all six gates and writes `review.md`. Checker = the checker session (Hermes mode) or Hermes itself (CC mode) — never the maker.
6. **LOOP**: Hermes writes `fix_instruction`, delegates the fix to the executor, re-audits. If the checker returns `ESCALATE_REPLAN` (stall detected — same issue recurs across rounds), Hermes drafts a contract update (re-decompose steps, adjust scope) and presents it to the user — the contract must not be modified without user confirmation. After user approval, re-enter ACT. Two consecutive `ESCALATE_REPLAN` without progress → report to user and stop.
7. **VERIFY**: the checker independently re-executes verification commands for each checklist item. Records the actual command and raw output in `review.md`.
8. **BASELINE_LOCK**: Hermes records a baseline without changing deliverables.
9. **OPTIMIZE_LOOP**: mandatory triage after baseline. Pre-scan changed + adjacent files (pre-scan evidence gate applies — see Rules). Triage across four dimensions (see `references/protocol.md`); each dimension gets its own block with `NO_CANDIDATE` + one-line reason if none. **Hermes zero-candidate review**: reviews `OPTIMIZE_TRIAGE` only when ALL four report `NO_CANDIDATE`; insufficient reasons → reject and re-scan. Delegate `OPTIMIZE_NOW` to executor, checker re-verifies. Present `SUGGEST_TO_USER` to user. Skip only when zero candidates and review passes.
10. **FINAL_VERIFY**: the checker confirms baseline integrity and optimization stop reason.
11. **DELIVER**: Hermes summarizes evidence and presents the deliverable. Session IDs and process files must not be modified or removed without user confirmation — the user decides when to clean up.

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

- **Maker-checker split.** The executor (worker session or CC session) is the maker. The checker is a different session in Hermes mode, or Hermes itself in CC mode — and Hermes never changes deliverables, so it can audit the CC maker without overlap. The maker never reviews its own work. Hermes orchestrates and makes the final call.
- **No `delegate_task` for executor or checker.** `delegate_task` subagents are one-shot — the conversation ends when the task completes and the session cannot be resumed. LOOP, VERIFY, and OPTIMIZE all require sending new instructions to an existing session via `--resume`. Use `terminal` to spawn persistent sessions (`hermes -z --pass-session-id` or `claude -p --session-id`) and resume them with `--resume`. This is non-negotiable: the entire multi-round design breaks without session persistence.
- **Session tracking.** Record executor session IDs in `state.md` at first call. Cleared only with user confirmation on DELIVER.
- Oral PASS is FAIL. Evidence must be file paths, diff summaries, command output, or deliverable paths.
- Scope control is part of strictness. Unrequested features go to notes or `state/inbox.md`, not blocking issues.
- After `BASELINE_LOCK`, pre-scan changed + adjacent files in the skill directory, record the file list as evidence, then triage across four dimensions (see `references/protocol.md`); each dimension gets its own block in `OPTIMIZE_TRIAGE`. Pre-scan evidence is mandatory — if the scanned file list is empty or missing, reject and re-scan. Hermes reviews `OPTIMIZE_TRIAGE` only when ALL four dimensions report `NO_CANDIDATE`; insufficient reasons → reject and re-scan. Execute `OPTIMIZE_NOW` only when gain >=5%, risk is low, no regression, no new deps, no user approval needed. `enrichment` dimension candidates bypass `OPTIMIZE_NOW` — always use `SUGGEST_TO_USER` with user confirmation required.
- On `DELIVER`, summarize key evidence. Do not delete process files or modify `state.md` without user confirmation. Keep `state/inbox.md` when unresolved items remain.

## Hermes Executor Mode

Hermes spawns two independent `hermes -z` sessions — a worker and a checker. Both persist via `--resume` across all phases.

### First call (worker — ACT)

```bash
hermes -z "You are the worker Agent. Read state/<slug>/state.md for the contract.
Execute only the contracted steps. Do not expand scope.
Record what you did and any test output." \
  --pass-session-id
# Capture session ID from output, record in state.md worker_session
```

### First call (checker — AUDIT)

```bash
hermes -z "You are the independent checker Agent. Review only; do not modify deliverables.
Read state/<slug>/state.md and review.md (if present).
First check PLAN quality. On later rounds, close old issues before checking new ones.
Run all six gates. Append AUDIT section to state/<slug>/review.md.
Decision: PROCEED_TO_VERIFY | CONTINUE_FIX | ESCALATE_REPLAN | STOP_WITH_BLOCKER." \
  --pass-session-id
# Capture session ID from output, record in state.md checker_session
```

### Subsequent calls (LOOP, VERIFY, OPTIMIZE, FINAL_VERIFY)

```bash
hermes -z "<fix_instruction / optimize_instruction>" \
  --resume "$WORKER_SESSION_ID"   # worker: LOOP fixes, OPTIMIZE execution
hermes -z "<audit / verify / final_verify instruction>" \
  --resume "$CHECKER_SESSION_ID"  # checker: re-AUDIT, VERIFY, FINAL_VERIFY
```

### Cleanup

Clear `worker_session` and `checker_session` from `state.md` on DELIVER.

For full invocation details and toolset guidance, see `references/hermes-executor-mode.md`.

## CC Executor Mode

Hermes delegates ACT, LOOP, and OPTIMIZE to CC via a persistent `claude -p` session.

### First call (ACT)

Generate a UUID, record in `state.md` `cc_session`, then invoke:

```bash
CC_ID=$(python3 -c "import uuid; print(uuid.uuid4())")

claude -p "You are the execution Agent. Read state/<slug>/state.md for the contract.
Execute only the contracted steps. Do not expand scope.
Record what you did and any test output." \
  --session-id "$CC_ID" \
  --allowedTools "Read,Write,Edit,Bash" \
  --max-turns 10
```

### Subsequent calls (LOOP, OPTIMIZE)

```bash
claude -p "<fix_instruction or optimize_instruction from Hermes>" \
  --resume "$CC_ID" \
  --max-turns 5
```

`--resume` restores full conversation history — CC remembers prior ACT context, files read, and changes made.

### Cleanup

`claude -p` auto-exits when done. Clear `cc_session` from `state.md`.

For full invocation details and `--allowedTools` guidance, see `references/cc-executor-mode.md`.

## Gotchas

- **`delegate_task` is NOT a substitute for persistent sessions**: `delegate_task` subagents are one-shot — the conversation dies on task completion, and you cannot `--resume` them. If you use `delegate_task` for ACT, when the checker finds a gap and LOOP fires, you have no session to resume. The fix instruction would go to a fresh agent with zero prior context — which defeats the entire multi-round design. Always spawn executor and checker via `terminal` (`hermes -z --pass-session-id` or `claude -p --session-id`) so they persist and can be resumed. This is the #1 failure mode when using this skill.
- **Stall detection**: `ESCALATE_REPLAN` is not a softer `STOP_WITH_BLOCKER` — it means the checker sees the same issue class recur across fix rounds and the current decomposition cannot resolve it. The orchestrator drafts a contract update (re-decompose steps, adjust scope, split/merge checklist items), presents it to the user for confirmation, then re-enters ACT. If the contract is unchanged and ACT is re-entered, it will loop again on the same issue.
- **No in-process fallback**: No executor mode chosen at PLAN = workflow cannot proceed. In CC mode Hermes is the checker (it audits the CC maker, not its own execution); it never both executes and reviews the same deliverable.
- **Evidence trust**: Executor self-reported summary is NOT evidence. Read test output, diffs, and logs yourself.
- **VERIFY must re-run tests**: Reading OBSERVE evidence is not verification.
- **Hermes session IDs are auto-generated**: Use `--pass-session-id` to capture them. Unlike CC, you cannot pre-assign a UUID.
- **Hermes executor needs two sessions**: Worker and checker must be separate sessions for clean maker-checker split. Do not use one session for both.
- **Hermes --resume context accumulation**: Each `--resume` reloads full conversation history. Processing time grows with every resume. No hard timeout — let the call complete naturally. If a call hangs, the orchestrator can kill it manually.
- **CC --session-id requires UUID**: Generate with `python3 -c "import uuid; print(uuid.uuid4())"`.
- **CC --max-turns trap**: 3 turns fails for multi-file ACT. ACT needs 10+; LOOP/OPTIMIZE 5. Do not reduce without understanding the cost.
- **CC --allowedTools is set at spawn time**: `--resume` inherits the original tools and cannot widen them per phase.

For full protocol formats, see `references/protocol.md`.

## Recovery

Before resuming, read `state/<slug>/state.md`, `review.md` if present, and `state/inbox.md` if present.

Route by state:

- `user-confirm` is non-empty -> ask the user first.
- Unfinished `next` fix -> apply it, updating the contract first if scope or checklist changed.
- `ESCALATE_REPLAN` -> Hermes drafts contract update, presents to user for confirmation before modifying `state.md`. After approval, re-enter ACT. Two consecutive `ESCALATE_REPLAN` without progress -> report to user and stop.
- `PROCEED_TO_VERIFY` -> send VERIFY to checker.
- `VERIFIED` without baseline section in `state.md` -> append baseline lock.
- Baseline exists and optimization not started -> OPTIMIZE_LOOP.
- OPTIMIZE changes applied and not yet re-audited -> AUDIT (checker re-verifies the optimization).
- Optimization stopped or ineligible -> FINAL_VERIFY.
- Final `VERDICT: VERIFIED` -> DELIVER.
- Blocker, hard limit, or low-value continuation -> stop and report.

## References

- `references/contract-template.md`: copy when creating `state.md`.
- `references/protocol.md`: full AUDIT/VERIFY/OPTIMIZE/FINAL_VERIFY formats and recovery routing.
- `references/hermes-executor-mode.md`: Hermes session management, toolset guidance, two-session workflow.
- `references/cc-executor-mode.md`: CC session management, `--allowedTools` guidance, invocation templates.
