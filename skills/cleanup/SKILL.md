---
name: cleanup
description: 每次任务完成、阶段切换、中断或拒收时必须自动加载并执行。清理本次任务产生的编译残留、一次性脚本、npm/pip/node_modules 等构建依赖、空目录、临时文件。在所有涉及 npm install、pip install、node compile、mkdir 构建等操作的任务结束时，这是强制性最后步骤——不要等用户提醒，不要询问"是否需要清理"。Use this skill automatically at the conclusion of EVERY task, especially those involving builds, package installs, or compilation.
---

# Cleanup

## 铁律

1. **每次任务完成时强制执行** — 不是可选项。声称"好了"前必须先清理。
2. **不问"要不要清理"** — 直接执行。
3. **不确定归属的文件保留并报告** — 宁可留，不可误删。

## 快速检查清单

- [ ] `__pycache__/`、`*.pyc`、`*.pyo`
- [ ] `node_modules/`（仅本次安装且未使用的）
- [ ] `.DS_Store`
- [ ] 编辑器备份 `*~`、`*.bak`、`*.orig`
- [ ] 本次创建的临时脚本（一次性处理/调试用）
- [ ] 未使用的 import
- [ ] 调试语句 `print()`、`console.log()`、`debugger`、`pdb.set_trace()`
- [ ] 硬编码密钥/测试账号/假数据
- [ ] 空目录、失败产物、未引用文件

> 详细清单见 [references/file-types.md](references/file-types.md)

## 场景

| 场景 | 动作 |
|------|------|
| **正常完成** | 删过程文件 + 复查（git diff / ls） |
| **中断/拒收** | 删本次产物 + 复原已知改动（有 git diff 才回滚） |
| **错误重试** | 清错误产物 + 重新执行 |

## 输出

简单任务一句话，复杂任务用 [references/report-template.md](references/report-template.md)。

报告必须含：已删除内容、保留待确认内容及原因、`Status: cleaned | interrupted-cleaned`。

## 约束

- 每个动作都能说明"为何属于本次任务且不再需要"
- 敏感信息只说已移除，不复述内容
- 只清理确认归属的，不扩大范围
