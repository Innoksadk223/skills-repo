#!/usr/bin/env python3
"""
Agent Loop CLI 调度模板。

实验性参考：只覆盖 ACT/AUDIT/VERIFY 路由。完整交付仍必须回到 SKILL.md 的 BASELINE_LOCK、OPTIMIZE_LOOP、FINAL_VERIFY 和 DELIVER。
使用前必须按当前平台检查 CLI 参数、会话恢复方式和写入路径；审查会话只在当前进程内续接，不写入 state 或仓库文件。
"""

import argparse
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

STATE_DIR = Path("state")
CLAUDE_BIN = "claude"
MAX_FIX_ROUNDS = 3
MAX_CONSECUTIVE_APPEAL_ONLY = 2
LOG_FILE: Path | None = None


def log(message: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
    print(line)
    if LOG_FILE is not None:
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def read_review(path: Path) -> dict:
    """Extract latest routing fields from fixed-format review.md."""
    if not path.exists():
        return {"decision": "UNKNOWN", "issues": 0, "gates_pass": False}

    result = {"decision": "UNKNOWN", "issues": 0, "gates_pass": False}
    gate_lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DECISION:"):
            decision = line.split(":", 1)[1].strip()
            if decision in {"PROCEED_TO_VERIFY", "CONTINUE_FIX", "STOP_WITH_BLOCKER"}:
                result["decision"] = decision
        elif line.startswith("ISSUE_COUNT:"):
            try:
                result["issues"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("- ") and any(
            key in line
            for key in (
                "contract:",
                "completeness:",
                "correctness:",
                "reuse_existing:",
                "budget:",
                "evidence_regression:",
            )
        ):
            gate_lines.append(line)

    result["gates_pass"] = len(gate_lines) >= 6 and all("PASS" in line for line in gate_lines)
    return result


def read_optional(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def audit_prompt(round_num: int, task_slug: str, appeal_text: str | None = None) -> str:
    base = f"""你是独立审查员，跨轮存活，只审查不动手修改。

任务目录：state/{task_slug}

立场：默认不信任。主 Agent 的产出在证明正确前视为有问题。不确定就是 CONTINUE_FIX。

范围：只围绕 state.md、当前轮任务、验收 Checklist、变更证据、预算证据、上轮 review 或上诉审查。不得要求新增用户未要求的功能、runner 自动化、新脚本或复杂模块；范围外建议不得计入 ISSUE_COUNT。

审查步骤：
1. 读 state/{task_slug}/state.md、review.md（如有）、state/inbox.md（如有）、appeal.md（如有）。
2. 先审 PLAN 质量。
3. 第二轮后先验旧账、再查新账。
4. 执行六门审查：contract / completeness / correctness / reuse_existing / budget / evidence_regression。
5. 追加 AUDIT 段落到 state/{task_slug}/review.md，严格使用固定格式。
每条 fix_instruction 必须是给主 Agent 的定向 prompt：写明目标文件/对象、要改什么、不得改什么、完成后如何验证；不得写成泛泛建议。

PROCEED_TO_VERIFY 条件：
- ISSUE_COUNT: 0
- PLAN_CHECK verdict PASS
- 六门全 PASS
- VERIFY_HANDOFF.unresolved 为空
- 证据可检查

review.md 的 AUDIT 段落固定格式：
## AUDIT Round N

DECISION: PROCEED_TO_VERIFY | CONTINUE_FIX | STOP_WITH_BLOCKER
ISSUE_COUNT: <number>

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

APPEALS:
- item:
  ruling: UPHELD | OVERRULED | CLARIFIED
  reason:

VERIFY_HANDOFF:
- checklist_items_ready:
- evidence_paths:
- unresolved:
"""
    if round_num > 1:
        base += "\n第二轮后要求：先确认旧账闭环，再重新做完整六门审查，不能只写上轮问题已修。\n"
    if appeal_text:
        base += f"\n上诉内容如下，请逐条裁决 UPHELD / OVERRULED / CLARIFIED：\n{appeal_text}\n"
    return base


def verify_prompt(task_slug: str) -> str:
    return f"""你是同一个独立审查员，现在进入 VERIFY。

读取 state/{task_slug}/state.md、review.md 和所有证据。
逐项验收 Checklist，追加 VERIFY 段落到 state/{task_slug}/review.md：

## VERIFY

VERDICT: VERIFIED | RETURN_TO_LOOP | STOP_WITH_BLOCKER

CHECKLIST:
1. item:
   verdict: PASS | FAIL
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
"""


def run_cli(prompt: str, session_id: str, resume: bool) -> int:
    args = [CLAUDE_BIN, "-p", prompt, "--resume" if resume else "--session-id", session_id]
    result = subprocess.run(args, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        log(f"CLI failed: {result.stderr[:300]}")
    return result.returncode


def write_blocker_feedback(path: Path, reason: str) -> None:
    path.write_text(
        "## AUDIT Round blocker\n\n"
        "DECISION: STOP_WITH_BLOCKER\n"
        "ISSUE_COUNT: 1\n\n"
        "PLAN_CHECK:\n- verdict: FAIL\n- evidence: 审查 Agent CLI 失败\n- notes:\n\n"
        "GATES:\n- contract: FAIL\n- completeness: FAIL\n- correctness: FAIL\n- reuse_existing: PASS\n- budget: PASS\n- evidence_regression: FAIL\n\n"
        "ISSUES:\n"
        "1. failure_type: external_blocker\n"
        "   severity: blocker\n"
        f"   evidence: {reason}\n"
        "   fix_instruction: 目标对象：runner CLI 配置、当前 task state 写入路径、CLI 会话参数。检查并修正 CLAUDE_BIN、--session-id/--resume 参数、state/<slug>/review.md 写入权限与路径；不得新增依赖、不得写入审查 Agent ID、不得扩大 runner 覆盖范围。完成后运行 `python -m py_compile skills/agent-loop/references/runner-template.py`、`git diff --check -- skills/agent-loop/references/runner-template.py`，并确认 repo/main 副本 `diff -qr` 为 0。\n\n"
        "APPEALS:\n- item:\n  ruling:\n  reason:\n\n"
        "VERIFY_HANDOFF:\n- checklist_items_ready:\n- evidence_paths:\n- unresolved: 审查 Agent CLI 失败\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent Loop CLI runner template")
    parser.add_argument("--task", default="执行 state.md 中定义的目标")
    parser.add_argument("--task-slug", default=f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    parser.add_argument("--cleanup", action="store_true", help="完成后清理 state/<slug>/")
    args = parser.parse_args()

    task_dir = STATE_DIR / args.task_slug
    task_dir.mkdir(parents=True, exist_ok=True)
    review_file = task_dir / "review.md"
    appeal_file = task_dir / "appeal.md"

    global LOG_FILE
    LOG_FILE = task_dir / "loop.log"

    session_id = str(uuid.uuid4())

    log(f"Loop start task={args.task_slug} auditor_scope=current-process")

    fix_round = 0
    appeal_rounds = 0
    consecutive_appeal_only = 0
    exit_code = 0

    try:
        while True:
            fix_round += 1
            log(f"Round {fix_round}: ACT")
            act_prompt = args.task if fix_round == 1 else f"读取 state/{args.task_slug}/review.md 并逐条执行修正指令。"
            act_result = subprocess.run([CLAUDE_BIN, "-p", act_prompt], capture_output=True, text=True, timeout=600)
            if act_result.returncode != 0:
                log(f"ACT failed: {act_result.stderr[:300]}")

            appeal_text = read_optional(appeal_file)
            if appeal_text:
                appeal_rounds += 1
                consecutive_appeal_only += 1
            else:
                consecutive_appeal_only = 0

            log(f"Round {fix_round}: AUDIT")
            audit_result = run_cli(audit_prompt(fix_round, args.task_slug, appeal_text), session_id, resume=fix_round > 1)
            if audit_result != 0 and not review_file.exists():
                write_blocker_feedback(review_file, "审查 Agent CLI 进程异常退出")

            if appeal_text and appeal_file.exists():
                appeal_file.unlink()

            feedback = read_review(review_file)
            decision = feedback["decision"]
            log(f"DECISION={decision} ISSUES={feedback['issues']} GATES_PASS={feedback['gates_pass']}")

            if decision == "UNKNOWN":
                exit_code = 1
                break
            if decision == "STOP_WITH_BLOCKER":
                exit_code = 1
                break
            if decision == "PROCEED_TO_VERIFY":
                log("VERIFY")
                verify_result = run_cli(verify_prompt(args.task_slug), session_id, resume=True)
                log("VERIFY complete; continue BASELINE_LOCK/OPTIMIZE_LOOP/FINAL_VERIFY/DELIVER by SKILL.md")
                exit_code = 0 if verify_result == 0 else 1
                break

            if consecutive_appeal_only >= MAX_CONSECUTIVE_APPEAL_ONLY:
                log("Stop: appeal deadlock")
                break
            if fix_round >= MAX_FIX_ROUNDS + appeal_rounds:
                log("Stop: hard round limit")
                break

            log("Continue LOOP")
    finally:
        if args.cleanup and task_dir.exists():
            log(f"Cleaning {task_dir}")
            shutil.rmtree(task_dir)
            LOG_FILE = None
            print(f"Cleaned {task_dir}")
        elif not args.cleanup:
            log(f"Kept state dir: {task_dir}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
