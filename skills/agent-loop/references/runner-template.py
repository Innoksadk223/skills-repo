#!/usr/bin/env python3
"""
Agent Loop CLI 调度模板。

实验性参考：使用前必须按当前平台检查 CLI 参数、会话恢复方式和写入路径。
核心约束：主 Agent ACT，独立审查 Agent AUDIT/VERIFY，同系列任务复用同一审查会话。
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


def read_feedback(path: Path) -> dict:
    """Extract routing fields from fixed-format feedback.md."""
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
            for key in ("contract:", "completeness:", "correctness:", "budget:", "evidence_regression:")
        ):
            gate_lines.append(line)

    result["gates_pass"] = len(gate_lines) >= 5 and all("PASS" in line for line in gate_lines)
    return result


def read_optional(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def audit_prompt(round_num: int, task_slug: str, appeal_text: str | None = None) -> str:
    base = f"""你是独立审查员，跨轮存活，只审查不动手修改。

任务目录：state/{task_slug}

立场：默认不信任。主 Agent 的产出在证明正确前视为有问题。不确定就是 CONTINUE_FIX。

范围：只围绕 loop_contract.md、当前轮任务、验收 Checklist、变更证据、预算证据、上轮反馈或上诉审查。不得要求新增用户未要求的功能、runner 自动化、新脚本或复杂模块；范围外建议不得计入 ISSUE_COUNT。

审查步骤：
1. 读 state/{task_slug}/loop_contract.md、progress.md、inbox.md（如有）、上轮 feedback.md/appeal.md（如有）。
2. 先审 PLAN 质量。
3. 第二轮后先验旧账、再查新账。
4. 执行五门审查：contract / completeness / correctness / budget / evidence_regression。
5. 写 state/{task_slug}/feedback.md，严格使用固定格式。

PROCEED_TO_VERIFY 条件：
- ISSUE_COUNT: 0
- PLAN_CHECK verdict PASS
- 五门全 PASS
- VERIFY_HANDOFF.unresolved 为空
- 证据可检查

feedback.md 固定格式：
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
- budget: PASS | FAIL
- evidence_regression: PASS | FAIL

ISSUES:
1. failure_type: logic_error | requirement_gap | missing_edge_case | regression | quality_issue | budget_issue | missing_skill | weak_validation | external_blocker
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
        base += "\n第二轮后要求：先确认旧账闭环，再重新做完整五门审查，不能只写上轮问题已修。\n"
    if appeal_text:
        base += f"\n上诉内容如下，请逐条裁决 UPHELD / OVERRULED / CLARIFIED：\n{appeal_text}\n"
    return base


def verify_prompt(task_slug: str) -> str:
    return f"""你是同一个独立审查员，现在进入 VERIFY。

读取 state/{task_slug}/loop_contract.md、progress.md、feedback.md 和所有证据。
逐项验收 Checklist，输出 state/{task_slug}/final_verify.md：

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
        "DECISION: STOP_WITH_BLOCKER\n"
        "ISSUE_COUNT: 1\n\n"
        "PLAN_CHECK:\n- verdict: FAIL\n- evidence: 审查 Agent CLI 失败\n- notes:\n\n"
        "GATES:\n- contract: FAIL\n- completeness: FAIL\n- correctness: FAIL\n- budget: PASS\n- evidence_regression: FAIL\n\n"
        "ISSUES:\n"
        "1. failure_type: external_blocker\n"
        "   severity: blocker\n"
        f"   evidence: {reason}\n"
        "   fix_instruction: 检查 CLI 可用性、会话参数和写入路径后重试\n\n"
        "APPEALS:\n- item:\n  ruling:\n  reason:\n\n"
        "VERIFY_HANDOFF:\n- checklist_items_ready:\n- evidence_paths:\n- unresolved: 审查 Agent CLI 失败\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent Loop CLI runner template")
    parser.add_argument("--task", default="执行 loop_contract.md 中定义的目标")
    parser.add_argument("--task-slug", default=f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    parser.add_argument("--cleanup", action="store_true", help="完成后清理 state/<slug>/")
    args = parser.parse_args()

    task_dir = STATE_DIR / args.task_slug
    task_dir.mkdir(parents=True, exist_ok=True)
    feedback_file = task_dir / "feedback.md"
    appeal_file = task_dir / "appeal.md"

    global LOG_FILE
    LOG_FILE = task_dir / "loop.log"

    shared_session_file = STATE_DIR / "session_auditor_id.txt"
    if shared_session_file.exists():
        session_id = shared_session_file.read_text(encoding="utf-8").strip()
    else:
        session_id = str(uuid.uuid4())
        shared_session_file.write_text(session_id + "\n", encoding="utf-8")
    (task_dir / "auditor_id.txt").write_text(session_id + "\n", encoding="utf-8")

    log(f"Loop start task={args.task_slug} auditor={session_id}")

    fix_round = 0
    appeal_rounds = 0
    consecutive_appeal_only = 0
    exit_code = 0

    try:
        while True:
            fix_round += 1
            log(f"Round {fix_round}: ACT")
            act_prompt = args.task if fix_round == 1 else f"读取 state/{args.task_slug}/feedback.md 并逐条执行修正指令。"
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
            if audit_result != 0 and not feedback_file.exists():
                write_blocker_feedback(feedback_file, "审查 Agent CLI 进程异常退出")

            if appeal_text and appeal_file.exists():
                appeal_file.unlink()

            feedback = read_feedback(feedback_file)
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
            shutil.rmtree(task_dir)
            log(f"Cleaned {task_dir}")
        elif not args.cleanup:
            log(f"Kept state dir: {task_dir}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
