---
name: hermes-agent-loop
description: "Use when a Hermes-orchestrated task needs maker-checker review, evidence-backed verification, issue-specific fix prompts, repeated correction, resumable maker state, bounded optimization, or an explicit /agent-loop request. Keep the parent Hermes responsible for orchestration and checking while one persistent CC or Hermes maker session changes deliverables; allow bounded delegate_task auxiliaries when the task benefits."
---

# Hermes Agent Loop

保持两个固定 agent：父 Hermes 负责 PLAN、USER_GATE、OBSERVE、AUDIT、VERIFY、针对性 prompts、优化分流和交付；一个 persistent maker 负责 ACT、交付物变更与整合。父 Hermes 不修改交付物，因此可以兼任 checker，而不会让 maker 自审。

## 模式选择

默认使用 **CC executor mode**；只有用户在 PLAN 明确要求 Hermes-native 执行时才选 **Hermes executor mode**。

| 模式 | Maker | Checker |
| --- | --- | --- |
| CC executor（默认） | 一个 persistent `claude -p` session | 父 Hermes |
| Hermes executor（opt-in） | 一个 persistent `hermes chat` worker session | 父 Hermes |

按任务派出的 `delegate_task` 是临时辅助 agent，不属于固定角色，也不能替代 maker 或 checker。

## 加载与状态

1. 先复用已有计划；没有可执行计划时写最小合约。
2. 修改交付物前，把 `references/contract-template.md` 复制到 `state/<slug>/state.md`，展示合约并取得用户显式确认。
3. 首次 ACT / AUDIT 前完整读取 `references/protocol.md` 和对应 executor-mode reference。

| 文件 | 所有者 | 用途 |
| --- | --- | --- |
| `state/<slug>/state.md` | 父 Hermes | 合约、证据、maker session、辅助委派、恢复、基线、交付 |
| `state/<slug>/review.md` | 父 Hermes（checker） | verdict、fix prompts、appeal、VERIFY、OPTIMIZE、FINAL_VERIFY |
| `state/<slug>/appeal.md` | 父 Hermes | maker 或用户提供的可选反证与裁决 |
| `state/inbox.md` | 父 Hermes | 可选的跨任务未决项 |

## 工作流

```text
PLAN → USER_GATE → MAKER_ACT → OBSERVE → PARENT_AUDIT
                                              │
                        CONTINUE_FIX ─────────┤
                        ESCALATE_REPLAN ──────┤
                        PROCEED_TO_VERIFY ────▼
                                           VERIFY
                                              ▼
                                       BASELINE_LOCK
                                              ▼
                        OPTIMIZE → AUDIT(re-verify)
                                              ▼
                                      FINAL_VERIFY → DELIVER
```

每个环节完成后在 `state.md` 的 `loop_todo` 对应项打勾；`loop_todo` 是 `stage` 的可视化防漏，冲突时以 `stage` 为准。

1. **ACT / OBSERVE**：父 Hermes 把合约交给 maker；随后亲自读取 diff、文件、日志和命令输出，不采信 maker 自述。
2. **AUDIT**：父 Hermes 作为 checker 检查 PLAN 与六 gate，并为每个 issue 写可直接执行的 `fix_prompt`。
3. **LOOP**：父 Hermes 把已写入 `review.md` 的 prompt 原样发送给 maker；maker 修正后，父 Hermes 先关闭旧 issue 再重审。
4. **VERIFY**：父 Hermes 独立重跑 checklist，不让 maker 给自己判 PASS。
5. **BASELINE / OPTIMIZE**：父 Hermes 记录 hash 与回滚入口，先写 `optimize_todo`（四维度 + 已知候选逐条登记），执行四维扫描并逐项关闭 todo，把 `OPTIMIZE_NOW` 的 `optimize_prompt` 原样发送给 maker。
6. **FINAL_VERIFY / DELIVER**：父 Hermes 确认基线和停止理由后交付。

## Maker 与辅助 Agent

- CC maker 使用预分配 UUID 的 `claude -p --session-id`，后续用 `--resume`。
- Hermes maker 使用 `hermes chat -Q -q`；每次从 stderr 的精确 `session_id:` 行捕获 ID，再用 `--resume <id>` 续轮。
- 不要用 `-z` one-shot 路径恢复 Hermes maker，也不要用 `delegate_task` 充当 persistent maker。
- 本技能允许父 Hermes 根据任务需要调用 `delegate_task`；只委派独立、有限、可验证的一次性辅助任务。
- 辅助 agent 不参与 AUDIT / VERIFY、不写 verdict、不替代 persistent maker；其 self-report 必须由父 Hermes 读取实际证据后验证。
- maker 与辅助 agent 不得并发修改重叠文件；并行优先用于只读探索、测试、日志分析和资料核验。
- 辅助 agent 若修改隔离的子交付物，其输出按 maker-side 工作处理，必须在 OBSERVE 前完成整合并纳入完整审查。

## 审查硬规则

- 保持 maker-checker split：maker 不得审查自己；父 Hermes 不得修改交付物。
- 每个阻塞 issue 必须有 ID、证据、`fix_instruction` 和独立 `fix_prompt`；prompt 必含目标、证据、必改、禁改、验证和完成回报。
- 父 Hermes 先把 prompt 写入 `review.md` 并记录 SHA-256，再原样发送；不得在传输时弱化、合并或补全。
- `CLARIFIED` 必须生成完整 replacement prompt，旧 prompt 作废。
- 第二轮及以后先关闭旧 issue，再重跑六 gate。相同 issue class 连续两轮复发时 `ESCALATE_REPLAN`。
- 口头 PASS 视为 FAIL；过程文件不能替代实际 diff、日志、命令输出或产物。
- 范围外建议进入 notes 或 `state/inbox.md`；`enrichment` 永远先问用户。

## 恢复与交付

恢复前读取实际存在的 `state.md`、`review.md`、`appeal.md` 和 `state/inbox.md`，再恢复唯一 maker session。

- maker session 不可恢复时，保留旧 ID，递增 `maker_generation`，从过程文件创建 replacement maker。
- 父 Hermes 的 checker 状态由过程文件恢复，不创建第二个 checker session。
- `user-confirm` 非空、合约需变更、外部动作需授权或连续两次 replan 无进展：停止并询问用户。
- 只有 `FINAL_VERIFY: VERIFIED` 才能交付；maker session ID 和过程文件只有用户能授权清理。

公共 schema 与路由见 `references/protocol.md`；精确 maker transport 见 `references/cc-executor-mode.md` 或 `references/hermes-executor-mode.md`。
