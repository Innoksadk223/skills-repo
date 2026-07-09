---
name: cc-agent-loop
description: "Use when work has high cost of silent errors, repeated correction, resumable review state, strict evidence requirements, or an explicit /agent-loop request. Separates doing from judging with independent review, persistent session-based resumability, and bounded optimization. This is the Claude Code version."
---

# CC Agent Loop

Separate doing from judging. The primary CC handles PLAN, ACT, fixes, and delivery. An independent CC audit process reviews evidence, writes verdicts, verifies readiness, and controls safe optimization.

Use existing planning first: Plan mode, `writing-plans`, or another suitable planning skill. Auxiliary Q&A-type skills are not excluded from PLAN — use them to stress-test assumptions, explore alternatives, or sharpen the contract before locking it in. If no usable plan exists, write the minimal contract before changing deliverables.

## Use

When independent review is needed before delivery, a failed change would be costly/subtle/hard to notice, the user asks for `/agent-loop` or multi-round review, or work may need recovery after interruption. Skip for one-shot answers, tiny edits, or tasks where a normal check is enough.

## State

| File | Owner | Purpose |
| --- | --- | --- |
| `state.md` | primary CC | contract, progress, evidence, audit session tracker, recovery, baseline, delivery notes |
| `review.md` | audit CC | audit, appeals, verify, optimize triage, final verdict |
| `inbox.md` | primary CC | optional unresolved items across tasks |

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
2. **USER_GATE**: primary CC must not proceed past PLAN until the user confirms the contract. No implicit approval.
3. **ACT**: primary CC executes only contracted work. If the checklist contains testable items (tests, lint, typecheck, build), run the corresponding verification commands and record raw output before handoff.
4. **OBSERVE**: primary CC reads and records real evidence — test output, diffs, logs, file contents — in `state.md` before handing off to audit. Do not rely on the ACT agent self-reported summary. If tests were run in ACT, record the exact commands and raw terminal output, not paraphrased results.
5. **AUDIT**: spawn the audit CC process with a fixed session ID. Generate a UUID, record it in `state.md` `audit_session`. The audit CC checks plan quality first, then all six gates. Writes results to `review.md`.
6. **LOOP**: primary CC follows `CONTINUE_FIX` instructions or writes an evidence-backed appeal. If the audit CC returns `ESCALATE_REPLAN` (stall detected — same issue recurs across rounds), primary CC drafts a contract update (re-decompose steps, adjust scope) and presents it to the user — the contract must not be modified without user confirmation. After user approval, re-enter ACT. Two consecutive `ESCALATE_REPLAN` without progress → report to user and stop.
7. **VERIFY**: audit CC independently re-executes verification commands for each checklist item. Records the actual command and raw output in `review.md`.
8. **BASELINE_LOCK**: primary CC records a baseline without changing deliverables.
9. **OPTIMIZE_LOOP**: mandatory triage after baseline. Pre-scan changed + adjacent files (pre-scan evidence gate applies — see Rules). Triage across four dimensions (see `references/protocol.md`); each dimension gets its own block with `NO_CANDIDATE` + one-line reason if none. **Primary CC zero-candidate review**: reviews `OPTIMIZE_TRIAGE` only when ALL four report `NO_CANDIDATE`; insufficient reasons → reject and re-scan. Primary CC executes `OPTIMIZE_NOW`, audit CC re-verifies. Present `SUGGEST_TO_USER` to user. Skip only when zero candidates and review passes.
10. **FINAL_VERIFY**: audit CC confirms baseline integrity and optimization stop reason.
11. **DELIVER**: primary CC summarizes evidence and presents the deliverable. Session IDs and process files must not be modified or removed without user confirmation — the user decides when to clean up.

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

- **Maker-checker split.** The CC that produces the output must not be the CC process that grades it. The audit CC is an independent process with its own session ID. Self-review is not an audit.
- **Auxiliary agents.** When specialized help is needed (test coverage, external research, parallel exploration, etc.), spawn a one-shot `delegate_task` subagent after user consent; write its output to `state.md` and hand it to the executor. Auxiliary agents do not participate in AUDIT/VERIFY.
- **audit_session tracking.** Record the audit CC session UUID in `state.md` `audit_session` at first spawn. Resume the same session for all subsequent phases — do NOT spawn a new process per phase.
- Primary CC may provide templates and handoff context, but must not write audit findings or final verdicts.
- **Phase gate.** 每次进入新阶段前必须更新 `state.md` 的 `stage` 字段。DELIVER 前核对 stage 路径必须经过 `AUDIT`(PROCEED_TO_VERIFY 或 CONTINUE_FIX 闭环后) + `VERIFY`(VERIFIED) + `FINAL_VERIFY`(VERIFIED);缺任一视为跳步 FAIL,回退到缺失阶段。`USER_GATE` 未获用户确认禁止进入 `ACT`。`BASELINE_LOCK` 前禁止 `OPTIMIZE_LOOP`。audit CC 在 AUDIT 时将"stage 路径不完整"作为 `contract` gate FAIL 的证据。
- Oral PASS is FAIL. Evidence must be file paths, diff summaries, command output, or deliverable paths.
- Scope control is part of strictness. Unrequested features go to notes or `state/inbox.md`, not blocking issues.
- After `BASELINE_LOCK`, pre-scan changed + adjacent files in the skill/module directory, record the file list as evidence, then triage across four dimensions (see `references/protocol.md`); each dimension gets its own block in `OPTIMIZE_TRIAGE`. Pre-scan evidence is mandatory — if the scanned file list is empty or missing, reject and re-scan. Primary CC reviews `OPTIMIZE_TRIAGE` only when ALL four dimensions report `NO_CANDIDATE`; insufficient reasons → reject and re-scan. Execute `OPTIMIZE_NOW` only when gain >=5%, risk is low, no regression, no new deps, no user approval needed. `enrichment` dimension candidates bypass `OPTIMIZE_NOW` — always use `SUGGEST_TO_USER` with user confirmation required.
- On `DELIVER`, summarize key evidence. Do not delete process files or modify `state.md` without user confirmation. Keep `state/inbox.md` when unresolved items remain.

## CC Session Management

### Audit CC Spawn (first phase)

Generate a UUID, record in `state.md`, then spawn:

```bash
AUDIT_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
# Record AUDIT_ID in state.md audit_session

claude -p "You are the independent audit Agent. Review only; do not modify deliverables.
Read state/<slug>/state.md and review.md (if present).
First check PLAN quality. On later rounds, close old issues before checking new ones.
Run all six gates: contract / completeness / correctness / reuse_existing / budget / evidence_regression.
Append AUDIT section to state/<slug>/review.md.
Decision: PROCEED_TO_VERIFY | CONTINUE_FIX | ESCALATE_REPLAN | STOP_WITH_BLOCKER." \
  --session-id "$AUDIT_ID" \
  --allowedTools "Read,Write,Grep,Glob,Bash(grep *,find *,cat *,head *,tail *,pytest *,npm test *,npx *,make *,cargo *,go test *,python -m *,ruff *,mypy *,eslint *,tsc *,prettier *)" \
  --max-turns 5
```

### Audit CC Resume (subsequent phases)

```bash
claude -p "<phase-specific audit prompt>" \
  --resume "$AUDIT_ID" \
  --max-turns 5
```

`--resume` restores the full conversation history. The audit CC remembers prior rounds, issue closures, and appeal rulings.

### Tool Scope

`--allowedTools` is set at spawn time and inherited by all `--resume` calls. CC `--resume` cannot widen tools per phase. The expanded Bash patterns cover both AUDIT (read-only inspection) and VERIFY (running test/lint/typecheck commands). The prompt instruction ("do not modify deliverables") is the guard against touching deliverable files.

## Gotchas

- **Stall detection**: `ESCALATE_REPLAN` is not a softer `STOP_WITH_BLOCKER` — it means the audit CC sees the same issue class recur across fix rounds and the current decomposition cannot resolve it. Primary CC drafts a contract update (re-decompose steps, adjust scope), presents it to the user for confirmation, then re-enters ACT. If the contract is unchanged and ACT is re-entered, it will loop again on the same issue.
- **Evidence trust**: The ACT agent self-reported summary is NOT evidence. Read test output, diffs, and logs yourself.
- **CC --max-turns trap**: 3 turns fails for multi-file ACT in practice. ACT needs 10+ turns; LOOP and OPTIMIZE need 5. The spawn commands use these values — do not reduce them without understanding the cost.
- **CC --session-id requires UUID**: `--session-id "audit-<slug>"` fails. Generate with `python3 -c "import uuid; print(uuid.uuid4())"`.
- **CC -p auto-exits**: No explicit termination needed. Cleanup means clearing the UUID from `state.md`.
- **CC --allowedTools without Write**: The audit process cannot write `review.md` without Write. Add it and trust the prompt to guard deliverables.
- **CC per-file write restriction**: Not supported. The audit prompt instruction ("do not modify deliverables") is the only guard.
- **Self-review is not audit**: A fresh audit process without prior session context starts blind. Always `--resume` or inject prior `review.md`.
- **VERIFY must re-run tests**: Reading OBSERVE evidence is not verification. The audit CC must independently execute the checklist's verification commands and record raw output.
- **Prompt cache TTL affects cost**: CC `--resume` reloads full conversation history as prefix. If the Anthropic prompt cache is valid (default 5 min TTL), cached prefix tokens cost ~10% of normal input. If expired, cache is rebuilt at 125% of normal input cost. Consecutive phases within minutes benefit most; long gaps may exceed TTL and trigger cache rebuild.
- **CC --resume context accumulation**: Each `--resume` reloads full conversation history. Processing time grows with every resume. No hard timeout — let the call complete naturally. If a call hangs, the orchestrator can kill it manually.

For full protocol formats and recovery routing, see `references/protocol.md`.

## Recovery

Before resuming, read `state/<slug>/state.md`, `review.md` if present, and `state/inbox.md` if present.

Route by state:

- `user-confirm` is non-empty -> ask the user first.
- Pending appeal -> resume the same audit CC for ruling.
- Unfinished `next` fix -> apply it, updating the contract first if scope or checklist changed.
- `ESCALATE_REPLAN` -> primary CC drafts contract update, presents to user for confirmation before modifying `state.md`. After approval, re-enter ACT. Two consecutive `ESCALATE_REPLAN` without progress -> report to user and stop.
- `PROCEED_TO_VERIFY` -> send VERIFY to the same audit CC.
- `VERIFIED` without baseline section in `state.md` -> append baseline lock.
- Baseline exists and optimization not started -> OPTIMIZE_LOOP.
- OPTIMIZE changes applied and not yet re-audited -> AUDIT (re-verify the optimization).
- Optimization stopped or ineligible -> send FINAL_VERIFY.
- Final `VERDICT: VERIFIED` -> DELIVER.
- Blocker, hard limit, appeal deadlock, or low-value continuation -> stop and report.

## References

- `references/contract-template.md`: copy when creating `state.md`.
- `references/protocol.md`: full AUDIT/VERIFY/OPTIMIZE/FINAL_VERIFY formats, appeal protocol, optimization triage, and recovery routing.
