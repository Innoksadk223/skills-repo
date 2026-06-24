---
name: cleanup
description: Mandatory post-task janitor that removes temporary scripts, process files, build artifacts, cache directories, debug leftovers, and other disposable junk created during the current run. Use when a task is ending, interrupted, rejected, or retried — enforces cleanup as a non-negotiable step before claiming completion.
---

# Cleanup

## 铁律

1. **每次任务完成时强制执行** — 不是可选项。声称"好了"前必须先清理。
2. **不问"要不要清理"** — 直接执行。
3. **不确定归属的文件保留并报告** — 宁可留，不可误删。
4. **目标是清理本次确认无用的过程文件、一次性文件和垃圾文件** — 不是追求工作区零噪音。

## 快速检查清单

- [ ] `__pycache__/`、`*.pyc`、`*.pyo`
- [ ] `node_modules/`（仅本次安装且未使用的）
- [ ] `.DS_Store`
- [ ] 编辑器备份 `*~`、`*.bak`、`*.orig`
- [ ] 本次创建的临时脚本（一次性处理/调试用）
- [ ] 未使用的 import
- [ ] 调试语句 `print()`、`console.log()`、`debugger`、`pdb.set_trace()`
- [ ] 硬编码密钥/测试账号/假数据
- [ ] 本次创建且确认无用的空目录、失败产物、未引用文件

> 详细清单见 [references/file-types.md](references/file-types.md)

## 场景

| 场景 | 动作 |
|------|------|
| **正常完成** | 删本次确认无用的过程文件 + 复查（git diff / git status / ls / find） |
| **中断/拒收** | 删本次产物 + 仅复原本 agent 明确创建/修改且确认无需保留的改动；无法确认归属则保留并报告 |
| **错误重试** | 清错误产物 + 重新执行 |

## 输出

简单任务可一句话，复杂任务用 [references/report-template.md](references/report-template.md)。

报告必须含：已删除内容、保留待确认内容及原因、`Status: cleaned | interrupted-cleaned`。无删除或无保留也要写"无"。

## 约束

- 每个删除/复原动作都能说明"为何属于本次任务"和"为何结束后不再需要"
- `untracked` 不等于本次任务产物；`git diff`、`git status`、`ls` 只可辅助确认，不是删除或回滚授权
- 不使用 `git clean -fd/-fdx`、仓库级 `rm -rf`、通配符批量删除来追求"干净"
- 不得回滚用户或其他 agent 的改动；归属不明则保留并报告
- 敏感信息只说已移除，不复述内容
- 只清理确认归属的，不扩大范围
