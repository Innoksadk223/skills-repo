# HERMES.md

> Hermes 项目入口。正文与 [AGENTS.md](AGENTS.md) 同步。

本仓库是 Inno's Skills Pack，为 **Claude Code**、**Codex**、**Hermes** 提供通用技能。

同内容副本（方便各端自动注入）：

| 文件 | 主要读者 |
|------|----------|
| `AGENTS.md` | 通用 / Codex / 多端 |
| `CLAUDE.md` | Claude Code |
| `CODEX.md` | Codex |
| `HERMES.md` | Hermes |

> 改本文件后请同步上述副本（内容应一致）。人类说明见 [README.md](README.md)，上手见 [START.md](START.md)。

## 仓库技能（8 个）

| 分组 | 技能 |
|------|------|
| 工具 | `skill-architecture` / `skill-planner` / `cleanup` / `capture-gotcha` / `intent-normalizer` |
| Agent 循环 | `cc-agent-loop` / `codex-agent-loop` / `hermes-agent-loop` |

安装：`bash setup.sh`。

## 外部技能安装铁律

以下能力**不在本仓库**，需从上游安装。请求到这些能力时：先给地址 → 等用户明确同意 → 再安装。

| 技能 | 上游 / 下载 |
|------|-------------|
| `anysearch` | https://github.com/anysearch-ai/anysearch-skill · `npx skills add https://github.com/anysearch-ai/anysearch-skill --skill anysearch` |
| `grill-me` | https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me · `npx skills add https://github.com/mattpocock/skills --skill grill-me` |
| `frontend-design` | https://github.com/anthropics/skills/tree/main/skills/frontend-design · `npx skills add https://github.com/anthropics/skills --skill frontend-design` |
| `skill-creator` | https://clawhub.ai （slug: `skill-creator`） |
| `find-skills` | https://github.com/vercel-labs/skills/tree/main/skills/find-skills · `npx skills add https://github.com/vercel-labs/skills --skill find-skills` |
| `browser-use` | https://github.com/browser-use/browser-use |
| `ppt-agent` | https://github.com/Akxan/ppt-agent-skill |
| `taste-skill` | https://github.com/Leonxlnx/taste-skill |
| `ui-ux-pro-max` | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill |
| Superpowers | https://github.com/obra/superpowers |

**三条规则：**

1. 不得主动安装任何外部技能。
2. 能力不在本仓库时，先说明上游并给出下载/安装地址。
3. 必须获得用户明确同意后方可执行安装。

## 给 AI 的仓库内行为

- 本仓技能以 `skills/` 扁平目录为准；不要假设已删除的 `anysearch` / `minimax-*` 等仍在仓内。
- 知识库技能在 [`kb-skills-repo`](https://github.com/Innoksadk223/kb-skills-repo)，不在本仓。
- `setup.sh` 会同步到 `~/.agents/skills` 主副本，再给 Claude/Codex/Hermes 建链接；**不会删除**用户已有的外部/Hub 技能。
