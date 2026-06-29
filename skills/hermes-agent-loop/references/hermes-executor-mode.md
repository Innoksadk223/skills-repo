# Hermes Executor Mode

Detailed two-session workflow for Hermes Agent Loop.

## Architecture

Hermes orchestrates two independent `hermes -z` sessions:

- **Worker session**: executes ACT, LOOP fixes, OPTIMIZE changes. Persistent via `--resume`.
- **Checker session**: performs AUDIT, VERIFY, FINAL_VERIFY. Persistent via `--resume`.

Both sessions are Hermes instances with their own context. The worker never sees the checker's reasoning; the checker never sees the worker's internal process. Communication flows through `state.md` and `review.md` files, orchestrated by the Hermes parent.

**Do NOT use `delegate_task` to create these sessions.** `delegate_task` spawns one-shot subagents — the conversation ends when the task completes, and the session cannot be resumed with `--resume`. When the checker finds a gap and LOOP fires, you need to send the fix instruction to the *same* worker that has all the prior context. A `delegate_task` subagent is already gone. Use `terminal` to invoke `hermes -z --pass-session-id` directly, capture the session ID, and use `--resume "$SESSION_ID"` for all subsequent calls. This is non-negotiable — without persistent sessions, LOOP/VERIFY/OPTIMIZE cannot function.

## Session Lifecycle

### Worker — First Call (ACT)

```bash
hermes -z "You are the worker Agent. Read state/<slug>/state.md for the contract.
Execute only the contracted steps. Do not expand scope.
Record what you did and any test output." \
  --pass-session-id
```

Capture the session ID from output. Record in `state.md` as `worker_session`.

### Checker — First Call (AUDIT)

```bash
hermes -z "You are the independent checker Agent. Review only; do not modify deliverables.
Read state/<slug>/state.md and review.md (if present).
First check PLAN quality. On later rounds, close old issues before checking new ones.
Run all six gates: contract / completeness / correctness / reuse_existing / budget / evidence_regression.
Append AUDIT section to state/<slug>/review.md.
Decision: PROCEED_TO_VERIFY | CONTINUE_FIX | ESCALATE_REPLAN | STOP_WITH_BLOCKER." \
  --pass-session-id
```

Capture the session ID from output. Record in `state.md` as `checker_session`.

### Subsequent Calls (LOOP, VERIFY, OPTIMIZE, FINAL_VERIFY)

Worker (for fixes and optimization execution):
```bash
hermes -z "<fix_instruction or optimize_instruction>" \
  --resume "$WORKER_SESSION_ID"
```

Checker (for re-audit, verify, final verify):
```bash
hermes -z "<audit / verify / final_verify instruction>" \
  --resume "$CHECKER_SESSION_ID"
```

`--resume` restores full conversation history. The worker remembers prior ACT context, files read, and changes made. The checker remembers prior audit rounds, issue closures, and verdicts.

### Cleanup

Clear `worker_session` and `checker_session` from `state.md` on DELIVER. Session IDs no longer recorded anywhere — accidental resumption impossible.

## Toolset Guidance

Hermes `-z` inherits the profile's configured toolsets. Control scope with `-t` / `--toolsets`:

### Worker (needs full execution capability)

```bash
hermes -z "<instruction>" \
  -t terminal,file,web \
  --pass-session-id
```

### Checker (needs read + test execution, not write to deliverables)

```bash
hermes -z "<instruction>" \
  -t terminal,file \
  --pass-session-id
```

The checker's prompt instruction ("do not modify deliverables") is the primary guard. Toolset restriction is secondary — the checker needs `terminal` to run verification commands and `file` to read evidence and write `review.md`.

## Session ID Discovery

`--pass-session-id` includes the session ID in the agent's system prompt. After the call completes, find the session ID:

```bash
# Most recent session
hermes sessions list 2>&1 | head -5
```

Or capture from the output when `--pass-session-id` echoes it.

## Evidence Capture

After each worker or checker call:

1. Read the stdout output
2. Read the actual deliverable files (do not trust self-report)
3. Run verification commands yourself (Hermes parent executes, not the worker)
4. Record all evidence in `state.md`

## Comparison with CC Executor Mode

| Aspect | Hermes executor | CC executor |
|-------|----------------|-------------|
| Sessions | Two (worker + checker) | One CC (maker) + Hermes (checker) |
| Maker-checker | Fully separated — two hermes sessions | CC is maker; Hermes is checker (Hermes never touches deliverables) |
| Session ID | Auto-generated, captured via `--pass-session-id` | UUID, pre-assigned via `--session-id` |
| Turn limit | None — Hermes decides when to stop | `--max-turns` (ACT 10, LOOP/OPTIMIZE 5) |
| Tool control | `-t` / `--toolsets` | `--allowedTools` |
| Multi-round memory | Both sessions persist via `--resume` | Single session persists via `--resume` |

## Prompt Cache Considerations

`--resume` reloads full conversation history as prefix. Two sessions means two independent cache chains:

- Worker cache: benefits from tight ACT → LOOP → OPTIMIZE loops
- Checker cache: benefits from tight AUDIT → VERIFY → FINAL_VERIFY loops
- Cross-session gaps (worker finishes, then checker starts) do not affect each other's cache
- Long gaps (user confirmation between phases) may exceed cache TTL for either session
