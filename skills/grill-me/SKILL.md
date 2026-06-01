---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me". When no unresolved branch remains, output an Agent Handoff for writing-plans or execution.
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time.

If a question can be answered by exploring the codebase, explore the codebase instead.

When no unresolved branch remains, output an `Agent Handoff`:

```markdown
## Agent Handoff

Status: pending | approved
Source: grill-me
Objective: One sentence goal
Scope: What to do now
Non-goals: What not to do now
Decisions:
- Confirmed decision

Execution Plan:
1. Executable step

Skills / Tools:
- Required skill or tool

Verification:
- Completion check

Open Questions:
- None or unresolved question

Stop Conditions:
- When the executor must stop and ask the user
```

Use `Status: pending` by default. Use `Status: approved` only when the user explicitly approves the final plan or has already asked to execute that exact plan.
