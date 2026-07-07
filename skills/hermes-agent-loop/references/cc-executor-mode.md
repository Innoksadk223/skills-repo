# CC Executor Mode

Detailed CC session management for Hermes Orchestrator Mode.

The CC session is the **maker** — it executes ACT, LOOP fixes, and OPTIMIZE, nothing else. **Hermes is the checker**: it performs AUDIT, VERIFY, and FINAL_VERIFY and writes `review.md` itself. Hermes never changes deliverables, so auditing the CC maker keeps the maker-checker split intact. The CC maker never reviews its own work.

## Session Lifecycle

CC runs in a persistent session across ACT, LOOP, and OPTIMIZE — one UUID, resumed per phase. Hermes captures stdout as evidence after each call.

### First Call (ACT)

Generate a UUID, record in `state.md` `cc_session`:

```bash
CC_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
# Record CC_ID in state.md cc_session

claude -p "You are the execution Agent. Read state/<slug>/state.md for the contract.
Execute only the contracted steps. Do not expand scope.
Record what you did and any test output." \
  --session-id "$CC_ID" \
  --allowedTools "Read,Write,Edit,Bash" \
  --max-turns 10
```

### Subsequent Calls (LOOP, OPTIMIZE)

Resume the same session:

```bash
claude -p "<fix_instruction or optimize_instruction from Hermes>" \
  --resume "$CC_ID" \
  --max-turns 5
```

`--resume` restores full conversation history — CC remembers prior ACT context, files read, and changes made. No need to re-inject `state.md` per call.

### Cleanup

`claude -p` auto-exits when done. Do NOT clear `cc_session` from `state.md` — only the user can authorize cleanup.

## --allowedTools Guidance

`--allowedTools` is set at spawn time and inherited by all `--resume` calls. CC `--resume` cannot widen tools per phase.

### Recommended tool set for executor:

```
Read,Write,Edit,Bash
```

This covers all execution phases:
- ACT: needs Read + Write + Edit + Bash (write code, run tests)
- LOOP: needs the same (apply fixes)
- OPTIMIZE: needs the same (modify code)

### If the executor needs restricted scope:

```
Read,Write,Bash(pytest *,npm test *,make *)
```

Only restrict when the task has clear boundaries. Over-restriction causes CC to fail silently on needed operations.

## Evidence Capture

After each CC call:

1. Read the stdout output
2. Read the actual deliverable files (do not trust CC self-report)
3. Run verification commands yourself (Hermes executes, not CC)
4. Record all evidence in `state.md`

## CC Turn Budget

| Phase | --max-turns | Notes |
|-------|------------|-------|
| ACT | 10 | Code writing + test execution |
| LOOP | 5 | Targeted fixes |
| OPTIMIZE | 5 | Small scope changes |

If CC reaches max turns without completing, increase the next call's `--max-turns` or simplify the instruction. Do not blindly re-run with the same parameters.

## Prompt Cache Considerations

`--resume` reloads full conversation history as prefix. Benefits:

- CC retains context across phases without re-injecting `state.md`
- Anthropic prompt cache (default 5 min TTL) makes cached prefix tokens ~10% of normal input cost
- Consecutive phases within minutes benefit most

Risks:

- Long gaps (user confirmation, OPTIMIZE rounds) may exceed TTL → cache rebuild at 125% of normal input cost
- Token budget estimates that ignore cache are conservative for tight loops but optimistic for gap-heavy flows
