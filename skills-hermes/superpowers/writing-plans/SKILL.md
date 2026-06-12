---
name: writing-plans
description: Use when there is a spec, requirements, approved design, multi-step task, execution handoff, delegation need, or workspace-isolation need before execution.
---

# Writing Lightweight Plans

## Purpose

Create a plan that is clear enough to execute and short enough to use. This skill also owns plan execution, task delegation, and workspace isolation when those are needed.

## Trigger Rule

Use this before executing work when there is a spec, requirements, approved design, multi-step task, handoff, delegation opportunity, workspace-isolation need, or existing plan to run.

For tiny work, the plan may be a compact checklist in the conversation. For larger or interruptible work, write the plan to a file.

## Planning Flow

1. Write the goal in one sentence.
2. Name assumptions that affect execution.
3. Define scope and non-goals.
4. Identify dependencies and ordering.
5. Break work into observable steps.
6. Add verification for each major output.
7. Add stop conditions: when to pause and ask.

## Mode Selection

| Need | Mode |
| --- | --- |
| Just organize work | Planning Mode |
| Execute an existing plan locally | Execution Mode |
| Split independent tasks across agents | Delegation Mode |
| Protect current workspace from risky edits | Isolation Mode |

Use the lightest mode that handles the risk.

## Plan Template

```markdown
# Action Plan: [name]

Goal: [one sentence]

Assumptions:
- [only assumptions that change execution]

Scope:
- [what will be done]

Non-goals:
- [what will not be done]

Steps:
1. [action] -> [expected output/evidence]
2. [action] -> [expected output/evidence]

Verification:
- [check or command]
- [artifact review]

Stop Conditions:
- [missing input]
- [unexpected risk]
- [scope change]
```

## Step Quality

Good steps are:

- Specific: the actor knows what to do.
- Observable: the output can be seen or checked.
- Small enough to complete without losing context.
- Ordered only where dependency requires it.

Avoid vague steps like "handle errors", "clean up", or "make it better" unless they include concrete criteria.

## Handoff Rules

If someone else will execute the plan, include:

- exact files or artifacts when known;
- required tools or skills;
- expected evidence;
- what not to touch;
- how to report blockers.

## Execution Mode

Use when a plan already exists and the user wants it carried out.

1. Read the plan once and restate the goal.
2. Review it critically before acting.
3. If a step is unclear or risky, pause and ask.
4. Execute one step or one safe batch at a time.
5. Run that step's verification before marking it done.
6. Update the plan checklist if a plan file is being tracked.
7. Stop when blocked, verification fails repeatedly, or the plan no longer matches reality.

Execution report:

```markdown
Completed:
- [step] -> [evidence]

Remaining:
- [step]

Blocked:
- [issue / needed input]
```

## Delegation Mode

Use only when tasks are independent and delegation is allowed by the user/platform.

1. Keep the critical path local unless delegation is clearly safe.
2. Give each worker a narrow goal and owned files/responsibility.
3. Say what the worker must not touch.
4. Require verification evidence and changed file paths.
5. Review worker output before integrating or claiming completion.

Worker handoff:

```markdown
Goal:
Owned files / responsibility:
Do not touch:
Context:
Required checks:
Return:
- Changed files
- Summary
- Verification evidence
- Risks or blockers
```

Reusable templates in this skill directory:

- `implementer-prompt.md`
- `spec-reviewer-prompt.md`

## Isolation Mode

Use when risky edits, parallel work, or unrelated user changes make isolation valuable.

1. Check git status and current branch.
2. Detect whether the environment already provides an isolated workspace.
3. Prefer native workspace/worktree tools when available.
4. If manually using git worktrees, verify project-local worktree directories are ignored before creating them.
5. Run project setup and a clean baseline check when practical.
6. Do not delete or clean up a worktree unless it was created for this task or the user explicitly approves.

Isolation report:

```markdown
Workspace:
Branch:
Baseline check:
Cleanup owner:
```

## Save Policy

Save the plan to a file only when the user asks, the plan is long, or work will continue later. Otherwise keep it in the conversation.
