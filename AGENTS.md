# AGENTS.md

本仓库是 Inno's Skills Pack，为 Claude Code、Codex、Hermes 提供通用技能。

## 仓库技能（17 个）

| 分组 | 技能 |
|------|------|
| 文档 | `minimax-docx` / `minimax-pdf` / `minimax-xlsx` |
| 搜索 | `anysearch` |
| 前端 | `frontend-design` |
| 知识格式 | `wiki-to-okf` |
| 工具 | `skill-creator` / `skill-architecture` / `skill-planner` / `cleanup` / `find-skills` / `grill-me` / `capture-gotcha` / `intent-normalizer` |
| Agent 循环 | `cc-agent-loop` / `codex-agent-loop` / `hermes-agent-loop` |

安装：`bash setup.sh`。详见 [README.md](README.md)。

## 外部技能安装铁律

以下能力不在本仓库，需从上游 GitHub 安装：

| 能力 | 上游 |
|------|------|
| 浏览器自动化 | https://github.com/browser-use/browser-use |
| PPT 演示文稿 | https://github.com/Akxan/ppt-agent-skill |
| 前端设计审美 | https://github.com/Leonxlnx/taste-skill |
| UI/UX 设计参考 | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill |
| 通用方法论 | https://github.com/obra/superpowers |

**三条规则：**

1. 不得主动安装任何外部技能。
2. 当用户请求的能力不在本仓库时，先说明所需技能来自哪个上游仓库。
3. 必须获得用户明确同意后方可执行安装。
