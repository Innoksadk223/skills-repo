#!/usr/bin/env python3
"""
Agent Loop 调度脚本模板 — PLAN → ACT → AUDIT → LOOP → VERIFY。

职责：
  1. 维护迭代循环，直到触发终止条件
  2. 每轮：主 Agent 执行（可对误判指令提 APPEAL）→ 审查 Agent 独立验证 → 路由决策
  3. 终止条件：PROCEED_TO_VERIFY / STOP_WITH_BLOCKER / 改进<10% / 3轮硬上限 / 连续2轮仅上诉死锁

用法：
  python loop_runner.py --contract state/loop_contract.md --task "任务描述"

平台：
  - Claude Code: 用 CronCreate 定时触发本脚本
  - Hermes / 通用: 本脚本驱动 CLI 会话（--session-id + --resume）
  - 关键: 审查 Agent 跨轮持久存活，不每轮新建
"""

import argparse
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from datetime import datetime

STATE_DIR = Path("state")
LOG_FILE = None  # 由 main() 在创建任务目录后设置
CLAUDE_BIN = "claude"
MAX_FIX_ROUNDS = 3
MAX_CONSECUTIVE_APPEAL_ONLY = 2  # 连续仅上诉轮数上限，防死锁


def log(msg: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def read_feedback(feedback_file: Path) -> dict:
    """从 feedback.md 提取 DECISION / ISSUE_COUNT / IMPROVEMENT。"""
    if not feedback_file.exists():
        return {"decision": "UNKNOWN", "issues": 0, "improvement": None}
    lines = feedback_file.read_text().split("\n")
    result = {"decision": "UNKNOWN", "issues": 0, "improvement": None}
    for line in lines:
        if line.startswith("DECISION:"):
            raw = line.split(":", 1)[1].strip()
            if raw in ("PROCEED_TO_VERIFY", "CONTINUE_FIX", "STOP_WITH_BLOCKER"):
                result["decision"] = raw
        elif line.startswith("ISSUE_COUNT:"):
            try:
                result["issues"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("IMPROVEMENT:"):
            val = line.split(":", 1)[1].strip()
            if val != "N/A" and "%" in val:
                try:
                    num = val.split("%")[0].strip()
                    result["improvement"] = float(num) / 100
                except (ValueError, IndexError):
                    pass
    return result


def read_appeal(appeal_file: Path) -> str | None:
    """读取上诉文件内容，无上诉返回 None。"""
    if appeal_file.exists():
        return appeal_file.read_text()
    return None


def build_audit_prompt(round_num: int, contract_path: str, prev_feedback: dict, appeal_text: str | None = None) -> str:
    """构建审查 Agent 的完整 prompt（含四维度+输出格式+上诉裁决）。"""
    if round_num == 1:
        return f"""你是独立审查员，跨轮存活，只审查不动手修改。

## 立场：严格审查
主 Agent 的产出在证明正确前默认视为有问题。你的工作是深度审查：
- 确实没问题 → 给 PASS 并附每条维度的审查证据
- 发现问题 → 写清修正指令
- 不确定 → CONTINUE_FIX（不是 PROCEED_TO_VERIFY）

## PROCEED_TO_VERIFY 可操作标准(全部满足才给)
1. 证据闭环: 每条Checklist在报告中有文件路径+命令输出证据。无证据=FAIL
2. 四维全覆盖: 需求核对/问题分析/质量审查/回归检查各≥1行记录
3. 边界可核验: 指定边界场景有实际测试命令及输出，至少1个边界输入
4. 修正闭环: 上轮修正指令有文件级变更证据(diff或内容引用)，首轮自动通过
5. 零未解决问题: ISSUE_COUNT=0，无未归类怀疑项

## 审查四维度
1. 需求核对 — 逐条对照 {contract_path} Checklist，不光检查"有没有"还要"对不对""全不全"。口头无证据=FAIL
2. 问题分析 — 根因分析，标注 failure_type (logic_error|requirement_gap|missing_edge_case|regression|quality_issue|missing_skill|weak_validation|external_blocker)
3. 质量审查 — 结构/健壮性/可维护性，主动跑linter，构造边界输入
4. 回归检查 — 改动是否破坏已有功能，主动补充回归测试

## 输出格式(写入 state/feedback.md)
DECISION: PROCEED_TO_VERIFY | CONTINUE_FIX | STOP_WITH_BLOCKER
ISSUE_COUNT: N
PREV_ISSUE_COUNT: 0
IMPROVEMENT: N/A
(公式: (PREV_ISSUE_COUNT-ISSUE_COUNT)/PREV_ISSUE_COUNT×100%)

## 1. 需求核对
| 验收项 | 状态 | 证据 |
(逐条核对)

## 2. 问题分析
## 3. 质量审查
## 4. 回归检查

## 修正指令(仅 CONTINUE_FIX)
### 指令 N: [标题]
**failure_type**: [类型]
**位置**: file:line
**修正**: [可直接执行的操作]"""
    else:
        base = f"""审查 Round {round_num}。主 Agent 已逐条执行你上一轮的非上诉修正指令。
本轮变更: 见 state/ 目录中修改的文件。
请重新四维审查（标准与首轮一致），更新 ISSUE_COUNT、PREV_ISSUE_COUNT={prev_feedback.get('issues', 0)}、IMPROVEMENT，写入 state/feedback.md。
IMPROVEMENT = (PREV_ISSUE_COUNT - ISSUE_COUNT) / max(PREV_ISSUE_COUNT, 1) * 100%"""
        if appeal_text:
            base += f"""

## 上诉裁决(必须)
主 Agent 对以下修正指令提出上诉。请逐条裁决：
{appeal_text}

裁决格式（写回 feedback.md 的独立小节）：
## 上诉裁决
| 指令 | 裁决 | 理由 |
|------|------|------|
| 指令 N: [标题] | UPHELD / OVERRULED / CLARIFIED | [理由] |

- UPHELD: 原修正指令成立，主 Agent 必须执行
- OVERRULED: 同意主 Agent，撤回该指令
- CLARIFIED: 原指令表述不清，重写为更精确的修正指令（另附）
"""
        return base


def run_act(task: str, feedback: dict) -> None:
    """ACT: 主 Agent 执行。实际使用时替换为真正的 Agent 调用。"""
    if feedback.get("decision") == "CONTINUE_FIX":
        prompt = f"根据 state/feedback.md 中的修正指令执行本轮 ACT，逐条修改，产出更新到 state/"
    else:
        prompt = task
    log(f"ACT prompt: {prompt[:100]}...")
    result = subprocess.run(
        [CLAUDE_BIN, "-p", prompt],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        log(f"ACT 失败: {result.stderr[:200]}")


def run_audit(round_num: int, contract_path: str, prev_feedback: dict, session_id: str, feedback_file: Path, appeal_text: str | None = None) -> None:
    """AUDIT: 独立审查 Agent。首轮创建会话，后续恢复同一会话。"""
    prompt = build_audit_prompt(round_num, contract_path, prev_feedback, appeal_text)

    if round_num == 1:
        log(f"创建审查会话 {session_id}")
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--session-id", session_id],
            capture_output=True, text=True, timeout=600,
        )
    else:
        log(f"恢复审查会话 {session_id}")
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--resume", session_id],
            capture_output=True, text=True, timeout=600,
        )

    if result.returncode != 0:
        log(f"AUDIT 失败 (exit={result.returncode}): {result.stderr[:200]}")
        # 审计 Agent 崩溃时 feedback.md 可能未写入，写入降级裁决防止无限循环
        if not feedback_file.exists():
            feedback_file.write_text(
                "DECISION: STOP_WITH_BLOCKER\nISSUE_COUNT: 1\n"
                "PREV_ISSUE_COUNT: 0\nIMPROVEMENT: N/A\n"
                "## 阻塞原因: 审查 Agent CLI 进程异常退出\n"
            )


def main():
    parser = argparse.ArgumentParser(description="Agent Loop 调度器")
    parser.add_argument("--contract", default="state/loop_contract.md")
    parser.add_argument("--task", default="执行 loop_contract.md 中定义的目标")
    parser.add_argument("--task-slug", default=None, help="任务唯一标识，默认自动生成 task-YYYYMMDD-HHMMSS")
    parser.add_argument("--cleanup", action="store_true", help="任务完成后自动清理 state/<slug>/ 目录")
    args = parser.parse_args()

    # 任务隔离：每次运行独立 state/<slug>/ 目录
    if args.task_slug is None:
        args.task_slug = f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    task_dir = STATE_DIR / args.task_slug
    task_dir.mkdir(parents=True, exist_ok=True)

    feedback_file = task_dir / "feedback.md"
    appeal_file = task_dir / "appeal.md"
    log_file = task_dir / "loop.log"

    session_id = str(uuid.uuid4())  # 唯一会话 ID，并行安全

    # 重定向 log() 输出到任务目录
    global LOG_FILE
    LOG_FILE = log_file
    log(f"Loop 启动, task={args.task_slug}, session={session_id}")

    fix_round = 0
    appeal_rounds = 0
    consecutive_appeal_only = 0
    prev_feedback = {}
    exit_code = 0

    try:
        while True:
            fix_round += 1
            log(f"=== Round {fix_round} ===")

            # ACT: 主 Agent 执行（含上诉标记）
            appeal_text = read_appeal(appeal_file)
            has_appeal = appeal_text is not None
            if has_appeal:
                log(f"本轮含上诉: {appeal_text[:100]}...")
            run_act(args.task, prev_feedback)

            # AUDIT: 独立审查 Agent（持久会话，含上诉裁决）
            run_audit(fix_round, args.contract, prev_feedback, session_id, feedback_file, appeal_text)
            # 上诉已提交，清理 appeal.md 防止重复发送
            if has_appeal and appeal_file.exists():
                appeal_file.unlink()

            # 读裁决
            fb = read_feedback(feedback_file)
            decision = fb["decision"]
            improvement = fb["improvement"]
            prev_feedback = fb

            log(f"DECISION={decision}, ISSUES={fb['issues']}, IMPROVEMENT={fb['improvement']}")

            # 熔断: 裁决不可读时立即终止
            if decision == "UNKNOWN":
                log("=== 熔断: 审查 Agent 未产出有效裁决 ===")
                exit_code = 1
                break

            # 终止条件
            if decision in ("PROCEED_TO_VERIFY", "STOP_WITH_BLOCKER"):
                log(f"=== 终止: {decision} ===")
                exit_code = 0 if decision == "PROCEED_TO_VERIFY" else 1
                break

            if decision == "CONTINUE_FIX":
                if has_appeal:
                    appeal_rounds += 1
                    consecutive_appeal_only += 1
                    if consecutive_appeal_only >= MAX_CONSECUTIVE_APPEAL_ONLY:
                        log(f"=== 死锁: 连续 {consecutive_appeal_only} 轮仅上诉无实际修正 ===")
                        break
                else:
                    consecutive_appeal_only = 0

                effective_max = MAX_FIX_ROUNDS + appeal_rounds
                if fix_round >= effective_max:
                    log(f"=== {effective_max} 轮硬上限 (含 {appeal_rounds} 轮上诉) ===")
                    break
                if not has_appeal and improvement is not None and improvement < 0.10:
                    log(f"=== 收敛: 改进 {improvement:.1%} < 10% ===")
                    break

            log("继续下一轮...")
    finally:
        if args.cleanup and task_dir.exists():
            shutil.rmtree(task_dir)
            print(f"[cleanup] 已清理 {task_dir}")
        elif not args.cleanup:
            print(f"[保留] state 目录: {task_dir}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
