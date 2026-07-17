---
name: capture-gotcha
description: Records reusable local-environment lessons (paths, permissions, proxies, SSL, env vars, ports, tool installs, shell differences) to ~/.agents/env.md so future tasks don't hit the same environment trap twice. Use when terminal, browser, MCP, skill, or filesystem validation failures reveal a stable, reproducible environment-level fix. Also consult ~/.agents/env.md before terminal/browser/MCP/filesystem-heavy tasks to avoid known traps. Skip code bugs, business logic errors, user misunderstandings, and temporary outages.
---

# Capture Gotcha

把跨任务可复用的本机环境教训写入 `~/.agents/env.md`（三端软链共享），让后续任务少踩同一个坑。

## Workflow

1. **查重** — 先读 `~/.agents/env.md` 对应区段查已有解法（`add_gotcha.py search '关键词'` 快速查重）。确认无覆盖且满足四条件（环境层 + 可复用 + 稳定解法 + 真实根因已定位）才继续。
2. **写入** — 组织条目（问题 + 真实报错证据 → 根因 → 可执行解法，优先归入已有 `##` 区段），脚本写入或手动编辑，逐条过 [Audit Gates](#audit-gates)。
3. **验证** — 读 `~/.agents/env.md` 确认条目存在、格式正确、无重复；口头 PASS 不算 PASS。

## Audit Gates

条目必须全部通过：

| 门 | 检查 |
|---|---|
| `scope` | 属环境层（路径/权限/代理/SSL/版本/环境变量/端口/工具安装/symlink/shell差异/包装层策略）。**不记**：代码bug、业务逻辑、用户误解、远端临时故障、无稳定解法的模糊报错 |
| `evidence` | 有真实报错/日志支撑，非包装层摘要（`Command failed` 不算证据） |
| `placement` | 归入正确区段；标题/场景无重复（脚本自动去重 skip；条目过时用 `update` 刷新内容或手动编辑） |
| `actionability` | 解法稳定可执行，非单次外推或"试试看" |

## Script

```bash
SKILL_DIR=~/.agents/skills/capture-gotcha
python $SKILL_DIR/scripts/add_gotcha.py add \
  --title '标题' --scene '场景' --cause '原因' --fix '解法'

python $SKILL_DIR/scripts/add_gotcha.py search '关键词'
python $SKILL_DIR/scripts/add_gotcha.py list [--section 'Git']
python $SKILL_DIR/scripts/add_gotcha.py update '匹配词' --fix '新解法'
python $SKILL_DIR/scripts/add_gotcha.py check '原始报错文本'
python $SKILL_DIR/scripts/add_gotcha.py self-test
```

参数：`--dry-run`（预览）、`--date YYYY-MM-DD`、`--section '## 区段名'`、`--env-path PATH`（测试用）。`update` 支持 `--title`/`--cause`/`--fix`（可选，只传要改的）。

## Format

`##` 区段下每条一行：

```markdown
- **[YYYY-MM-DD] 标题**：场景 → 原因 → 解法
```

标题短到可扫读；场景写触发条件不写流水账；原因写底层机制；解法写可执行动作。

## Rules

- 先查后记 — 读 env.md 确认无已有解法再动手
- 不因记一笔打断主任务 — 先修复，再回头记
- 不替用户决定 — 不确定是否该记时，列证据让用户判断
