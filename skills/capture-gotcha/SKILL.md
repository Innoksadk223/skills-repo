---
name: capture-gotcha
description: >
  记录并召回有证据、可复用的项目、环境和工具调用经验。开始任何项目任务、
  终端/浏览器/MCP/文件操作，或遇到错误、命令失败和工具调用失败时使用。
  任务开始必须先运行 recall，读取当前项目与全局正式记忆；项目记忆优先。
  修复并验证后，把项目特有经验写入项目记忆，把跨项目仍成立的经验写入全局记忆，
  无法确认的经验写入候选记忆，不让候选参与 recall。
---

# Capture Gotcha

把已验证的失败经验变成下一次任务开始时可直接执行的提醒。这个技能的价值在于稳定召回，所以每次相关任务都遵循固定顺序：**recall → 执行 → 按错误查询 → 修复验证 → 沉淀**。

## 开始任务：强制 recall

只要任务涉及项目、终端、浏览器、MCP、文件系统、构建、测试、部署或工具调用，先运行：

```bash
python ~/.agents/skills/capture-gotcha/scripts/add_gotcha.py recall
```

不要凭记忆猜测文件位置，也不要因为任务看起来简单而跳过。无关键词 `recall` 会按项目记忆、全局记忆的顺序输出正式经验；候选记忆不会输出。若命令失败，先报告失败原因并直接读取对应的 `.agents/gotchas.md` 作为降级路径；读取失败本身可以在验证后记录为全局工具经验。

读完后检查三件事：

1. 当前任务是否命中某条经验。
2. 项目经验是否覆盖全局经验；冲突时遵守项目经验。
3. 是否有记忆中的命令、路径或工具限制需要在动手前调整。

遇到具体错误时，再用关键词查询：

```bash
python ~/.agents/skills/capture-gotcha/scripts/add_gotcha.py recall '关键词或错误码'
```

## 判断记忆范围

正式记忆只有两处：

- **项目记忆**：`<项目根>/.agents/gotchas.md`。当前代码、配置、目录结构、业务约定或项目工具链特有的经验写这里。
- **全局记忆**：`~/.agents/gotchas.md`。脱离当前项目仍成立的本机环境、通用工具行为、权限、代理、路径、shell 和包装层经验才写这里。

问自己：换到一个完全无关的项目，这条经验是否仍然成立？是，才考虑全局；否，写项目。项目特例绝不能污染全局。无法判断范围时，先写项目候选，验证后再提升。

## 什么时候记录

只有同时满足以下条件，才写正式记忆：

- 有真实错误、日志或可重复行为作为 `evidence`。
- 根因已经比“可能是……”更明确。
- `fix` 已经执行并验证成功。
- 未来任务能据此改变行动。

普通代码 bug、一次性远端故障、用户误解和未经验证的猜测不要直接写正式记忆。暂时有价值但尚未确认时，写当前项目候选：

```bash
python ~/.agents/skills/capture-gotcha/scripts/add_gotcha.py add \
  --scope candidate --title '标题' --scene '触发场景' \
  --cause '待确认原因' --evidence '真实现象' --fix '待验证方案'
```

候选位于 `<项目根>/.agents/gotchas-candidates.md`，不参与 recall。相同问题再次复现且解法稳定后，用唯一关键词提升：

```bash
python ~/.agents/skills/capture-gotcha/scripts/add_gotcha.py promote '关键词' --scope project
python ~/.agents/skills/capture-gotcha/scripts/add_gotcha.py promote '关键词' --scope global
```

## 写入与验证

正式记录示例：

```bash
python ~/.agents/skills/capture-gotcha/scripts/add_gotcha.py add \
  --scope project --title '标题' --scene '触发场景' \
  --cause '已确认根因' --evidence '原始报错或验证结果' \
  --fix '可执行且已验证的解法'
```

敏感信息会在落盘前脱敏，但仍应主动隐藏密码、令牌和认证 URL。添加或提升后，再运行一次带关键词的 `recall`，确认条目出现在正确作用域、顺序正确且内容可执行。更新文件使用同目录临时文件和原子替换。

支持的覆盖参数用于测试或特殊工作区：`--project-path`、`--global-path`、`--dry-run`。自检命令：

```bash
python ~/.agents/skills/capture-gotcha/scripts/add_gotcha.py self-test
```
