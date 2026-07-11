# CC Executor Mode

默认使用两个固定 agent：父 Hermes 负责编排与 checker；一个 persistent Claude Code session 是 maker。父 Hermes 不修改交付物，CC maker 不写 verdict 或 `review.md`。

| 角色 | Transport | 负责 | 禁止 |
| --- | --- | --- | --- |
| maker | `claude -p` persistent session | ACT、LOOP、OPTIMIZE_NOW | verdict、issue closure、写 `review.md` |
| checker | 当前父 Hermes | PLAN、OBSERVE、AUDIT、VERIFY、prompts、OPTIMIZE、FINAL_VERIFY、DELIVER | 修改交付物 |

公共 schema、gate 和阶段路由见 `protocol.md`。

## 1. 启动 CC Maker

调用前生成 UUID，并写入 `state.md` 的 `maker_session`：

```bash
MAKER_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')

claude -p "你是 maker。读取 state/<slug>/state.md 与所列技能，只执行已确认的步骤。
不要扩大范围，不要审查自己的工作，也不要写 review.md。
完成后报告实际 diff、验证输出和剩余风险。" \
  --session-id "$MAKER_ID" \
  --allowedTools "Read,Write,Edit,Bash" \
  --permission-mode dontAsk \
  --max-turns 10 \
  --output-format json
```

- 首次调用前记录 `maker_generation: 1`、`maker_status: RUNNING` 和完整 handoff。
- handoff 必须包含绝对工作目录、过程目录、交付物、checklist、停止条件和必须加载的技能。
- 首次 `--allowedTools` 是后续 resume 的边界；不要假设续轮可以扩大权限。
- 不要使用 `--continue`、`--no-session-persistence` 或扫描最近 session。

## 2. 父 Hermes 审查

maker 返回后，父 Hermes 必须亲自读取实际 diff、文件、日志和命令输出，再按 `protocol.md`：

1. 把 AUDIT、VERIFY、OPTIMIZE 和 FINAL_VERIFY 追加到 `review.md`。
2. 为每个 issue 写独立 `fix_prompt`，先记录 SHA-256，再原样发送给 maker。
3. 独立重跑 checklist；maker 自述不能替代证据或 PASS。
4. 不修改交付物，也不让 maker 判定 issue closure。

## 3. 续轮

收到 `CONTINUE_FIX` 或 `OPTIMIZE_NOW` 后，发送 `review.md` 中的原始 prompt：

```bash
claude -p "<verbatim fix_prompt 或 optimize_prompt>" \
  --resume "$MAKER_ID" \
  --max-turns 5 \
  --output-format json
```

不得改写、拼接、弱化或补全 prompt。maker 返回无法执行或证据错误时，父 Hermes 把反证写入 `appeal.md`，再以 checker 身份裁决；`CLARIFIED` 必须给完整 replacement prompt。

## 4. 按需辅助委派

父 Hermes 可在任务能从并行或专长分工中实际受益时调用 `delegate_task`，无需为每次普通委派另行确认；更高优先级指令、外部动作和不可逆操作仍照常受限。

- 只委派独立、有限、可验证的一次性任务。
- delegate agent 不替代 persistent maker 或 checker，不参与 AUDIT / VERIFY。
- 优先委派只读探索、测试、日志分析和资料核验；禁止与 maker 并发修改重叠文件。
- 把 handoff、结果和父 Hermes 的独立验证写入 `state.md`；self-report 不能直接作为证据。
- 若 delegate agent 修改隔离的子交付物，必须在 OBSERVE 前由 maker-side 完成整合，并纳入父 Hermes 的完整审查。

## 5. 预算与恢复

- 常规预算：ACT 10 turns；LOOP / OPTIMIZE_NOW 5。父 Hermes 的审查成本由合约停止护栏控制。
- maker resume 失败且排除临时 provider / auth / quota 故障：保留旧 UUID，递增 `maker_generation`，把合约、真实 diff、已执行 prompts 和未决工作交给 replacement maker。
- 父 Hermes 从 `state.md` 与 `review.md` 恢复 checker 进度，不创建 checker session。
- DELIVER 时保留 maker session ID 和过程文件；只有用户能授权清理。
