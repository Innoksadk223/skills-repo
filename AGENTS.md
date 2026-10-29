# AGENTS.md

本文件只记录 AI 维护本仓库时遵循的规则。项目介绍、技能清单、安装与使用说明统一见 [README.md](README.md)；技能的具体行为以各自 `SKILL.md` 为准，不在此重复维护。

## 仓库边界

- 发布技能以 `skills/` 下纳入 Git 跟踪的目录为准；被忽略的本机技能不属于发布清单，不因目录存在就收录或删除。
- 知识库技能属于独立的 `kb-skills-repo`，不在本仓；地址见 README。
- 增删发布技能时，同步 README 清单与数量。仅取消发布时，保留用户要求留在本机的文件及加载入口。

## 安装与更新

- 按 README 的安装流程确认目标 Agent 和实际加载位置，处理完整技能目录；保留用户修改和已有外部技能，不盲目覆盖同名内容。
- 外部推荐及上游地址只在 README 维护。不得主动安装；先提供上游与安装地址，获得用户明确同意后执行。

## 经验与清理

- 项目与通用经验的读写统一用 magic-context：`ctx_search` 按关键词或语义召回，`ctx_memory` 写入（分类 PROJECT_RULES／ARCHITECTURE／CONSTRAINTS／CONFIG_VALUES／NAMING）。换到无关项目仍成立的事实写成通用表述，让提升机制标为 ecosystem／universe。
- 遇到错误先 `ctx_search` 回查；修复验证后把可复用经验写入 `ctx_memory`，未验证的只作候选。
- 收尾、中断或重试时遵循 [cleanup](skills/cleanup/SKILL.md)：检查过程产物及相关历史遗留，包括旧备份和冗余副本；按用途与恢复价值判断，不确定则保留。历史文件与一次性制作工具先列清单确认，保护最终产品、可复用测试和用户资料。
