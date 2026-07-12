# Codex Agent Loop Protocol

按阶段读取对应节（见 SKILL 开卷表）。定义原生 agent 调用、AUDIT/VERIFY/OPTIMIZE/FINAL、appeal、恢复。

## 目录

1. 工具契约 · 2. 首次 Reviewer · 3. 复用/等待/纠偏 · 4. AUDIT · 5. LOOP/Appeal · 6. VERIFY · 7. BASELINE/OPTIMIZE · 8. FINAL_VERIFY · 9. 恢复 · 10. 预算/辅助 · 11. DELIVER

## 1. 原生 Agent 工具契约

直接调用 host multi-agent 工具（可带 `collaboration.` 前缀）。勿包进 shell/`functions.exec`。

| 工具 | 语义 | 勿误用 |
| --- | --- | --- |
| `spawn_agent` | 新建 child；以 canonical task name 为必记 handle | 勿每阶段新建 reviewer |
| `followup_task` | 给无进行中 turn 的 agent 开新 turn | 勿造第二 reviewer |
| `send_message` | 给运行中 agent 补消息 | 勿用它启动 idle agent |
| `wait_agent` | 等 mailbox；返回≠verdict | — |
| `list_agents` | 查当前根任务树 | 勿扫 `~/.codex/sessions/` |
| `interrupt_agent` | 中断 turn；agent 仍可复用 | 中断≠删除 |

共享工作区：主 Codex 写交付物；reviewer 写 review.md；禁并发同文件。

```md
- audit_task: <canonical task name；必填>
- audit_agent_id: <host 返回时记；否则 UNAVAILABLE>
- audit_generation: 1
- audit_status: <list_agents 原样；或 UNSPAWNED|INTERRUPTED|UNREACHABLE>
- audit_transport: direct_write | primary_verbatim
```

根任务恢复 ≠ child 续轮。勿记猜测的 CLI session ID。

### 字段集（复用）

**PROMPT_BLOCK**：目标对象 / 问题证据 / 必改内容 / 禁止变化 / 验证命令 / 完成回报  

**ISSUE_FIELDS**：id / failure_type / severity / evidence / fix_instruction / fix_prompt_ref  

failure_type 与 severity 枚举同 CC/Hermes 家族。

**OPTIMIZE_DIM_FIELDS** / **enrichment** 字段同家族（enrichment 禁 OPTIMIZE_NOW）。

## 2. 首次生成 Reviewer

OBSERVE 证据落盘后 spawn。`task_name` 短小、小写字母数字下划线；`fork_turns="none"`。

```text
spawn_agent({
  "task_name": "audit_<slug>",
  "fork_turns": "none",
  "message": "<完整 handoff>"
})
```

Handoff 必含：cwd、process dir、交付物、phase、唯一可写文件、停止条件、须读 state/review/appeal/inbox/protocol 对应节、六 gate 名、禁改交付物、sandbox 不能写时返回完整 block。

生成后立即写 audit_task + generation=1；agent id 仅 host 实返时记录。

### 只读转存兜底

完整 block → 主 Codex 逐字落盘 → `primary_verbatim` + SHA-256。篡改无效。  
勿声称 read-only custom agent 一定能写 review；以实际权限为准。

## 3. 复用、等待与纠偏

**idle 新阶段**：`followup_task({target, message})`  

**运行中补充**：`send_message`（不启动 idle）  

**等待**：`wait_agent` 有界（如 ≤60s）后亲读 review.md  

**中断**：`interrupt_agent` 后仍可 followup  

禁：`create_thread` / `fork_thread` / `codex exec resume` / `--last` / 扫 sessions 目录管 child。

## 4. AUDIT

```text
进入 AUDIT Round <N>。读 state/review/appeal/交付物。
先关旧 issue，再 PLAN+六 gate。追加完整 AUDIT。Decision 枚举同家族。
同根因两轮 → ESCALATE_REPLAN。
```

六 gate：

| gate | 口径 |
| --- | --- |
| contract | goal/non-goals/assumptions/checklist/handoff/recovery 可查 |
| completeness | 目标完整，无未确认扩 scope |
| correctness | 逻辑/边界/结构可接受 |
| reuse_existing | 优先复用既有能力，无无理由重造 |
| budget | 时间/工具/agent/继续价值记录充分 |
| evidence_regression | 证据可复查，无未解释回归 |

```md
## AUDIT Round N
DECISION: PROCEED_TO_VERIFY | CONTINUE_FIX | ESCALATE_REPLAN | STOP_WITH_BLOCKER
ISSUE_COUNT / STALL_DETECTION / PLAN_CHECK / GATES
ISSUES: <ISSUE_FIELDS>
FIX_PROMPTS:
### <id>
- target_role: primary_codex
- execution_order: <int>
- prompt: |
    你正在修正 issue <id>，勿处理其它问题。
    <PROMPT_BLOCK>
APPEALS / VERIFY_HANDOFF
```

主 Codex 不得代写/合并/弱化 prompt。PROCEED 条件同家族。

## 5. LOOP 与 Appeal

按 execution_order 原样执行 → 更新 OBSERVE。reviewer 不实施修正。

```md
## [APPEAL] <issue id>
original_fix_prompt / reason / counter_evidence
```

followup 请求裁决：UPHELD / OVERRULED / CLARIFIED（完整 replacement）。  
硬上限/blocker/低收益/两轮仅 appeal → 停。两轮同 class → ESCALATE_REPLAN + 用户确认合约。

## 6. VERIFY

仅 PROCEED 后 followup：

```text
进入 VERIFY。独立重跑 checklist。不依赖 OBSERVE。记命令与输出。只追加 VERIFY。
```

schema 同家族（VERIFIED|RETURN_TO_LOOP|STOP_WITH_BLOCKER）。

## 7. BASELINE 与 OPTIMIZE

主 Codex 追加 Baseline。followup reviewer：

```text
进入 OPTIMIZE Round <N>。optimization-seeking。
scanned_files 非空真实路径；先 optimize_todo 四维+known_candidates。
```

```md
## OPTIMIZE Round N
PERSPECTIVE: optimization-seeking
scanned_files: [paths]
### functionality — 复用已有功能等价物；不抄 UI
<OPTIMIZE_DIM_FIELDS>
### conciseness — 删冗余/死代码/多余间接层
<OPTIMIZE_DIM_FIELDS>
### maintainability — 命名/边界/依赖/重复
<OPTIMIZE_DIM_FIELDS>
### enrichment — 合约外增强；先问用户
decision: SUGGEST_TO_USER | NO_CANDIDATE（禁 OPTIMIZE_NOW）
```

规则：gain≥5%；低风险；无回归；无新依赖。enrichment 仅 `SUGGEST_TO_USER` | `NO_CANDIDATE`。  
**OPTIMIZE_NOW → 主 Codex 原样执行 → 同一 reviewer 再 AUDIT → VERIFY。**  
无改动停止 → FINAL_VERIFY。空泛 NO_CANDIDATE → 重扫。

## 8. FINAL_VERIFY

确认 baseline / 优化轮次 / 停止理由；loop_todo 与 optimize_todo 门槛同家族。

仅 VERIFIED → DELIVER。

## 9. 恢复路由

读过程文件。

**Handle**：list_agents(prefix) → RUNNING 则等/send_message；idle → followup；UNREACHABLE → 升 generation + `audit_<slug>_gN` replacement + 先关旧 issue。状态文件是跨根任务权威接口。

**Phase 优先级** 同家族表（user-confirm → appeal → CONTINUE_FIX → ESCALATE → PROCEED → … → OPTIMIZE_NOW 未复验回 AUDIT → 优化停 FINAL → DELIVER）。

切阶段更新 stage+loop_todo。

## 10. 预算、辅助与停止

- 一任务一可达 reviewer；replacement 仅真失效。  
- 记调用/修正轮/耗时/继续价值。有界等待并更新用户。  
- 辅助 agent：一次性可验证；不同 task name；不替代 reviewer；禁重叠写；子交付物 OBSERVE 前整合。

## 11. DELIVER

从 state+review 汇总。  
**不清空 handle、不删过程文件；仅用户授权清理。**
