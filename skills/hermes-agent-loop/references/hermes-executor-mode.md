# Hermes Executor Mode

只有用户在 PLAN 明确要求 Hermes-native 执行时使用本模式。固定角色仍只有两个：父 Hermes 负责编排与 checker；一个独立 persistent Hermes worker session 是 maker。

| 角色 | 负责 | 禁止 |
| --- | --- | --- |
| worker / maker | ACT、LOOP、OPTIMIZE_NOW | verdict、issue closure、写 `review.md` |
| 父 Hermes / checker | PLAN、OBSERVE、AUDIT、VERIFY、prompts、OPTIMIZE、FINAL_VERIFY、DELIVER | 修改交付物 |

worker 必须使用 `hermes chat -Q -q`；`-z` one-shot 路径不能恢复旧 session。`delegate_task` 只用于按需辅助任务，不能充当 persistent maker。

公共 schema、gate 与阶段路由见 `protocol.md`。

## 0. 模型配置

合约 `state.md` 可选指定 maker 或 checker 的模型，实现跨模型审查。provider 始终继承 config 默认，无需单独指定。

| 字段 | 用途 | 留空时 |
| --- | --- | --- |
| `maker_model` | worker spawn + resume | 走 config 默认模型 |
| `checker_model` | AUDIT/VERIFY 推理 | 父 Hermes 内联审查（当前模型） |

- **Maker**：`maker_model` 非空时，`hermes chat` 命令带 `-m "$MAKER_MODEL"`；留空则省略，走 config 默认。
- **Checker**：`checker_model` 非空时，父 Hermes 将证据 + checklist 组装为 prompt，用 `hermes chat -Q -q -m "$CHECKER_MODEL"` 一次性调用该模型产出 verdict，再写入 `review.md`。留空则父 Hermes 自行内联审查（当前行为）。

命令中用 bash 参数展开 `${MAKER_MODEL:+-m "$MAKER_MODEL"}`：变量非空时展开为 `-m "model"`，为空时展开为空串，不影响其余参数。

checker 一次性调用模板（无工具、纯推理）：

```bash
CHECKER_ERR=$(mktemp)
hermes chat -Q -q "<AUDIT/VERIFY prompt + 全部证据 + checklist + 输出格式要求>" \
  ${CHECKER_MODEL:+-m "$CHECKER_MODEL"} \
  --max-turns 1 \
  --ignore-rules \
  2>"$CHECKER_ERR"
CHECKER_EXIT=$?
rm -f "$CHECKER_ERR"
test "$CHECKER_EXIT" -eq 0
```

- checker 不需要工具（`--max-turns 1`、`--ignore-rules`），只做推理产出 verdict。
- 父 Hermes 仍负责写 `review.md`、路由决策和 prompt 转发。
- checker session 一次性使用，不需 resume。

## 1. Session ID 捕获规则

quiet query 将最终回复写到 stdout，并在 stderr 末尾输出：

```text
session_id: <exact-id>
```

每次首次调用和 resume 都必须：

1. 单独捕获 stderr。
2. 只匹配 `^session_id: `，并确认命令 exit code 为 0、ID 非空。
3. 把返回 ID 写回 `maker_session`；压缩可能产生新的 continuation ID。
4. 删除本次捕获用临时文件，保留调用结果与 ID 变化记录。

不要用 `--continue`、`hermes sessions list`、最新 session 或本地目录猜 ID。

## 2. 启动 Worker

```bash
WORKER_ERR=$(mktemp)
hermes chat -Q -q "你是 worker/maker。读取 state/<slug>/state.md 与所列技能。
只执行已确认的步骤，不扩大范围，不审查自己的工作，也不要写 review.md。
完成后报告实际 diff、验证输出和剩余风险。" \
  -t terminal,file \
  --max-turns 10 \
  ${MAKER_MODEL:+-m "$MAKER_MODEL"} \
  2>"$WORKER_ERR"
WORKER_EXIT=$?
cat "$WORKER_ERR" >&2
WORKER_ID=$(sed -n 's/^session_id: //p' "$WORKER_ERR" | tail -n 1)
rm -f "$WORKER_ERR"
test "$WORKER_EXIT" -eq 0 && test -n "$WORKER_ID"
```

把 `WORKER_ID` 写入 `maker_session`，记录 `maker_transport: hermes_chat`、`maker_generation: 1` 和实际调用结果。

完整 handoff 必须包含绝对工作目录、过程目录、交付物、checklist、停止条件和必须加载的技能。

默认只启用 `terminal,file`。若合约确需 web 或其它 toolset，必须在 USER_GATE 中明确；无人值守时需要 `--yolo` 也必须先有同等明确授权，不要静默添加。

## 3. 父 Hermes 审查

worker 返回后，父 Hermes 必须亲自读取实际 diff、文件、日志和命令输出，再按 `protocol.md`：

1. 把 AUDIT、VERIFY、OPTIMIZE 和 FINAL_VERIFY 追加到 `review.md`。
2. 为每个 issue 写独立 `fix_prompt`，记录 SHA-256 后原样发送给 worker。
3. 独立重跑 checklist；worker 自述不能替代证据或 PASS。
4. 不修改交付物，也不让 worker 判定 issue closure。

## 4. 续轮

父 Hermes 从 `review.md` 读取完整 prompt，记录 SHA-256，再原样发送：

```bash
hermes chat -Q -q "<verbatim fix_prompt 或 optimize_prompt>" \
  -t terminal,file \
  --max-turns 5 \
  ${MAKER_MODEL:+-m "$MAKER_MODEL"} \
  --resume "$WORKER_ID"
```

每次 resume 都按第 1 节捕获 stderr，并用返回值更新 `maker_session`。不得改写、拼接、弱化或补全 prompt。

worker 返回无法执行或证据错误时，父 Hermes 把反证写入 `appeal.md`，再以 checker 身份裁决；`CLARIFIED` 必须给完整 replacement prompt。

## 5. 按需辅助委派

父 Hermes 可在任务能从并行或专长分工中实际受益时调用 `delegate_task`，无需为每次普通委派另行确认；更高优先级指令、外部动作和不可逆操作仍照常受限。

- 只委派独立、有限、可验证的一次性任务。
- delegate agent 不替代 persistent maker 或 checker，不参与 AUDIT / VERIFY。
- 优先委派只读探索、测试、日志分析和资料核验；禁止与 worker 并发修改重叠文件。
- 把 handoff、结果和父 Hermes 的独立验证写入 `state.md`；self-report 不能直接作为证据。
- 若 delegate agent 修改隔离的子交付物，必须在 OBSERVE 前由 maker-side 完成整合，并纳入父 Hermes 的完整审查。

## 6. 预算与恢复

- 常规预算：worker ACT 10 turns，LOOP / OPTIMIZE_NOW 5。父 Hermes 的审查成本由合约停止护栏控制。
- worker 不可恢复且排除临时 provider / auth / quota 故障：保留旧 ID，递增 `maker_generation`，把合约、真实 diff、已执行 prompts 和未决工作交给 replacement worker。
- 父 Hermes 从 `state.md` 与 `review.md` 恢复 checker 进度，不创建 checker session。
- DELIVER 时保留 maker session ID 与过程文件；只有用户能授权清理。
