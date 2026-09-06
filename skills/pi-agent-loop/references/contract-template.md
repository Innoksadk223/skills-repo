# Pi Agent Loop Plan Contract

> PLAN/USER_GATE 时按此清单组装一次 `agent_team plan`。不要复制为强制 runtime 状态文件；TeamState 是结构化事实源，`leader/plan.md` 由 runtime 生成精简恢复视图。

## User-facing Contract

- Goal / observable result:
- Non-goals:
- Assumptions / clarifications:
- Stop conditions:
- Verification authorization and commands:
- Human acceptance entry point:

## Roster

| id | kind | role / reason | permissions | model override | stop condition |
| --- | --- | --- | --- | --- | --- |
| coder | coder | implementation | owned paths only | inherit | two rounds no progress |
| reviewer | reviewer | independent verdict | read-only | inherit | review budget |
| optional | debugger/product/optimizer | explicit reason | read-only | inherit | objective answered |

Reviewer must be unique. Optional experts are registered now only when justified; later additions require amendment.

## Execution DAG

| taskId | coder memberId | objective | dependsOn | ownedPaths | acceptance | relevantPaths |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

Checks:

- IDs unique; dependencies exist; graph acyclic.
- ownedPaths are concrete cwd-relative paths, with no absolute path, `..`, glob, normalized duplicate, or unordered parent/child conflict.
- Each task packet is minimal: objective, constraints, dependency summaries, owned paths, acceptance, relevant paths, output contract.
- Parallel candidates have no dependency relationship, distinct members, and non-overlapping ownership.

## Plan Call

```json
{
  "action": "plan",
  "team": "<team>",
  "plan": {
    "members": [
      {
        "id": "coder",
        "kind": "coder",
        "role": "Coder/Executor",
        "instructions": "Follow the TaskPacket and emit the execution envelope."
      },
      {
        "id": "reviewer",
        "kind": "reviewer",
        "role": "Independent Reviewer",
        "instructions": "Read-only; emit ReviewRound decisions.",
        "tools": ["read", "grep", "find", "ls"]
      }
    ],
    "reviewerId": "reviewer",
    "tasks": [
      {
        "id": "task-a",
        "memberId": "coder",
        "objective": "<result>",
        "constraints": ["<boundary>"],
        "dependsOn": [],
        "ownedPaths": ["src/path"],
        "acceptance": ["<binary check>"],
        "relevantPaths": ["src/path/file.ts"]
      }
    ],
    "acceptance": ["<global binary condition>", "HUMAN_ACCEPT is required"]
  }
}
```

Amendment resends the complete plan plus the exact current revision:

```json
{"action":"plan","team":"<team>","expectedRevision":1,"plan":"<complete replacement object>"}
```

## Loop Checklist

- [ ] USER_GATE approved plan revision
- [ ] Leader manually dispatched READY execution nodes
- [ ] Every Coder report has a valid execution envelope
- [ ] Every SUBMITTED task received an independent ReviewRound
- [ ] FIX_REQUIRED prompts were passed unchanged to the same task's next attempt
- [ ] All required tasks are VERIFIED
- [ ] Required debugger/product/optimizer ExpertRounds are closed, or N/A with reason
- [ ] Reviewer FINAL_VERIFY is VERIFIED
- [ ] Pending requests and known blockers are closed
- [ ] Leader presented completion criteria, evidence, limits, and manual entry
- [ ] User HUMAN_ACCEPT is ACCEPTED

## Recovery Snapshot

Use compact `agent_team status` and record only what the human needs:

- plan revision:
- current task/review/expert IDs and states:
- blockers / pending requests:
- next explicit Leader action:
- never auto-replay:

Use `status full:true` only when the roster, DAG, or exact TaskPacket is needed to recover. Long member prose stays in child Session or the referenced on-demand output.

## Context Policy

Members enable Pi native auto-compaction at startup. The orchestrator sets no custom thresholds, does not invoke compact after settlement, and writes no compaction handoff files. Native compaction or session failure surfaces as `ERROR/INTERRUPTED` without automatic replay. The Leader decides whether to rotate or continue and records any needed handoff summary outside orchestrator state.

## Human Acceptance

```md
STATUS: PENDING_ACCEPT | ACCEPTED | REJECTED
COMPLETION_CRITERIA:
EVIDENCE:
LIMITS:
EXPERIENCE_ENTRY:
USER_FEEDBACK:
```

`FINAL_VERIFY: VERIFIED` never fills ACCEPTED automatically. Contract-external feedback returns to amendment / USER_GATE.
