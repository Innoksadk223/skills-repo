---
name: capture-gotcha
description: Use when terminal, browser, web, MCP, skill, path, proxy, permission, version, env var, port, tool install, wrapper policy, or filesystem validation failures reveal a reusable local-environment lesson that should be recorded; do not use for code bugs, business logic, user intent mistakes, or temporary external outages.
---

# Capture Gotcha

AI 自维护环境教训库。在执行命令中遇到环境类陷阱（路径/代理/权限/版本/端口等），自动记录到 `~/.hermes/env.md`，自动清理过期条目（>7 天）。人类零维护。

## AI Workflow

**Before** — 涉及终端/安装/改路径/代理/技能脚本前，读 `~/.hermes/env.md` 的 `## 常见陷阱` 和相关区段。

**On Error** — 报错后先 `check '原始错误文本'`，匹配已知教训：
```bash
python skills/capture-gotcha/scripts/add_gotcha.py check 'SSLEOFError: EOF occurred in violation of protocol'
```

**Record** — 确认是新陷阱后 `add`，4 个字段：
```bash
python skills/capture-gotcha/scripts/add_gotcha.py add \
  --title '简括标题' --scene '触发条件' --cause '底层原因' --fix '可直接执行的解法'
```
`add` 成功后自动清除 `~/.hermes/env.md` 中距今 >7 天的条目。

## 判定：记不记

满足全部才记：
- 根因已定位（不是包装层摘要 `Command failed` / `API call failed after 3 retries`）
- 属于环境层：路径/权限/代理/SSL/版本/环境变量/端口/工具安装/symlink/shell 差异/包装层策略
- 可跨任务复用
- 有稳定解法

**不记**：代码 bug、业务逻辑错、用户误解、远端临时故障、无稳定解法的模糊报错。

## Commands

| 命令 | 用法 | 说明 |
|------|------|------|
| `add` | `--title --scene --cause --fix [--section '## 区段'] [--dry-run]` | 新增条目，自动查重，自动清 >7 天 |
| `search` | `'关键词'` | 全文搜索，返回行号 + 条目 |
| `list` | `[--section 'Git']` | 列出所有（可按区段过滤） |
| `update` | `'匹配词' [--title] [--cause] [--fix] [--section]` | 更新已有条目，自动刷新日期 |
| `check` | `'原始错误文本'` | 用原始报错匹配已知教训，返回匹配条目 |
| `self-test` | 无 | 自检 |

## Format

`~/.hermes/env.md` 每个 `##` 区段下，一条一行：
```markdown
- **[YYYY-MM-DD] 标题**：场景 → 原因 → 解法
```
标题短到可扫读；场景写触发条件不写流水账；原因写底层机制；解法写可直接执行的动作。

## Error Signals

| 信号 | 处理 |
|------|------|
| `Command failed` / `Tool error` / `API call failed after N retries` | 追底层原因，不直接记 |
| `No such file` / `ENOENT` / `command not found` / `No module named` | 找稳定路径/来源后可记 |
| `Permission denied` / `EACCES` | 找到权限边界后可记 |
| `SSLError` / `Could not resolve host` / `connection refused` | 区分代理/DNS/端口/远端故障 |
| `version mismatch` / CLI 参数不兼容 / `address already in use` | 找版本约束/端口处理后记 |
| traceback 指向项目逻辑或断言 | **不记** |
