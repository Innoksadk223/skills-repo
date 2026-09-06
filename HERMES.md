# HERMES.md

> Hermes 项目入口。正文与 [AGENTS.md](AGENTS.md) 同步。

本仓库是 Inno's Skills Pack，为 **Claude Code**、**Codex**、**Hermes** 与 **Pi** 提供通用技能。

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
| 工具 | `skill-architecture` / `cleanup` / `capture-gotcha` / `intent-normalizer` |
| Agent 循环 | `cc-agent-loop` / `codex-agent-loop` / `hermes-agent-loop` / `pi-agent-loop` |

安装根技能：`bash setup.sh`。

## Pi 独立包

`extensions/pi-agent-orchestrator/` 同时提供 `agent_team` extension 与包内 `pi-agent-team` 配套 skill。它不计入上述 8 个根技能，也不由 `setup.sh` 安装：

```bash
pi install ./extensions/pi-agent-orchestrator
```

默认单 Agent；仅复杂可拆分或用户明确要求时组队。新成员必须先经扩展 confirmation，持久配置与 child UUID 跟随父 branch；Pi 更新不兼容时 fail closed。复杂、多轮或需恢复的团队由主 Pi维护一份成员只读、摘要选择性发布的共享进度文档；一次性独立派工不创建。

## 推荐技能（自用清单）安装铁律

以下是维护者自用推荐能力，**不在本仓库**。请求到这些能力时：先给地址 → 等用户明确同意 → 再安装。

| 技能 | 上游 / 安装 |
|------|-------------|
| `anysearch` | https://github.com/anysearch-ai/anysearch-skill · `npx skills add https://github.com/anysearch-ai/anysearch-skill --skill anysearch` |
| `grill-me` | https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me · `npx skills add https://github.com/mattpocock/skills --skill grill-me` |
| `frontend-design` | https://github.com/anthropics/skills/tree/main/skills/frontend-design · `npx skills add https://github.com/anthropics/skills --skill frontend-design` |
| `skill-creator` | https://clawhub.ai （slug: `skill-creator`） |
| `find-skills` | https://github.com/vercel-labs/skills/tree/main/skills/find-skills · `npx skills add https://github.com/vercel-labs/skills --skill find-skills` |
| `playwright-cli` | https://github.com/microsoft/playwright-cli · `npx skills add microsoft/playwright-cli@playwright-cli` |
| `ponytail` | https://github.com/DietrichGebert/ponytail · `npx skills add https://github.com/DietrichGebert/ponytail --skill ponytail` |
| `rtk` | https://github.com/rtk-ai/rtk · `brew install rtk`；`rtk init -g --agent hermes`（其它 agent 见上游） |
| `ppt-agent` | https://github.com/Akxan/ppt-agent-skill |
| `taste-skill` | https://github.com/Leonxlnx/taste-skill |
| `ui-ux-pro-max` | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill |
| Superpowers | https://github.com/obra/superpowers |

**三条规则：**

1. 不得主动安装任何推荐/外部技能。
2. 能力不在本仓库时，先说明上游并给出下载/安装地址。
3. 必须获得用户明确同意后方可执行安装。

## 给 AI 的仓库内行为

- 本仓技能以 `skills/` 扁平目录为准；不要假设已删除的 `anysearch` / `minimax-*` / `skill-planner` 等仍在仓内。
- 知识库技能在 [`kb-skills-repo`](https://github.com/Innoksadk223/kb-skills-repo)，不在本仓。
- `setup.sh` 会同步 8 个根技能到 `~/.agents/skills` 主副本，再给 Claude/Codex/Hermes 建链接；**不会删除**用户已有的外部/Hub 技能。
- 包内 `pi-agent-team` 只随 Pi package 安装，不要和根 `pi-agent-loop` 重复计数或复制进 recommended preset。
