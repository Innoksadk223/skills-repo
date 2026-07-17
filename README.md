# Inno's Skills Pack

个人 AI Coding Agent 技能包，支持 **Claude Code**、**Codex**、**Hermes**。

> 小白上手看 [START.md](START.md) — 不用懂技术，会说目标就行。
>
> 知识库相关技能已拆到 [`kb-skills-repo`](https://github.com/Innoksadk223/kb-skills-repo)。
>
> Agent 入口文件（内容一致）：[AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) / [CODEX.md](CODEX.md) / [HERMES.md](HERMES.md)

## AI 使用流程

收到安装请求后，AI 应按以下步骤：

1. **先介绍** — 按分组介绍技能，每组一句话概括
2. **再确认** — 问用户要装到哪个 agent、选哪些分组。涉及推荐/外部技能时，列出上游地址，等用户确认后再安装
3. **再安装** — `bash setup.sh`（仅本仓技能）
4. **最后教** — 安装/更新完成后，直接读 [START.md](START.md)，给用户一段 3 分钟上手教程

## 本仓库技能（7 个）

| 分组 | 技能 | 一句话 |
|------|------|--------|
| 工具 | `skill-architecture` / `cleanup` / `capture-gotcha` / `intent-normalizer` (4) | 模块化架构、清理、环境记录、意图校准 |
| Agent 循环 | `cc-agent-loop` / `codex-agent-loop` / `hermes-agent-loop` (3) | 各平台 Agent 编排循环（执行-审查分离） |

## 推荐技能（自用清单）

以下是我自己在用的推荐能力，**不在本仓库**，从上游安装。AI 不得擅自安装，须用户同意。

| 技能 | 用途 | 上游 / 安装 |
|------|------|-------------|
| `anysearch` | 实时搜索、垂直搜索、批量搜索、URL 提取 | [anysearch-ai/anysearch-skill](https://github.com/anysearch-ai/anysearch-skill) · `npx skills add https://github.com/anysearch-ai/anysearch-skill --skill anysearch` |
| `grill-me` | 深度质询方案/设计 | [mattpocock/skills · grill-me](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) · `npx skills add https://github.com/mattpocock/skills --skill grill-me` |
| `frontend-design` | 高质量前端页面/组件 | [anthropics/skills · frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) · `npx skills add https://github.com/anthropics/skills --skill frontend-design` |
| `skill-creator` | 创建新技能 | [clawhub.ai](https://clawhub.ai)（slug: `skill-creator`） |
| `find-skills` | 发现/安装社区技能 | [vercel-labs/skills · find-skills](https://github.com/vercel-labs/skills/tree/main/skills/find-skills) · `npx skills add https://github.com/vercel-labs/skills --skill find-skills` |
| `playwright-cli` | 浏览器自动化（Playwright CLI + Skills） | [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) · `npx skills add microsoft/playwright-cli@playwright-cli` |
| `ponytail` | 反过度工程：最懒且能用的解 | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) · `npx skills add https://github.com/DietrichGebert/ponytail --skill ponytail` |
| `rtk` | CLI 输出压缩，降低 LLM token（工具，非 skill 包） | [rtk-ai/rtk](https://github.com/rtk-ai/rtk) · `brew install rtk` 后 `rtk init -g --agent hermes`（Claude/Codex 见上游） |
| `ppt-agent` | PPT 全流程生成 | [Akxan/ppt-agent-skill](https://github.com/Akxan/ppt-agent-skill) |
| `taste-skill` | 反模板化前端审美 | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `ui-ux-pro-max` | UI/UX 设计参考 | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |
| Superpowers | 头脑风暴、计划、技能编写、并行代理 | [obra/superpowers](https://github.com/obra/superpowers) |

### 给 AI：推荐技能安装约束

1. 不得主动安装任何推荐/外部技能。
2. 能力不在本仓库时，先说明上游并给出下载/安装地址。
3. 必须获得用户明确同意后方可执行安装。

## 常用工作流入口

| 场景 | 入口 | 何时用 | 产物 |
|------|------|--------|------|
| 复杂任务循环 | `hermes-agent-loop` / `cc-agent-loop` / `codex-agent-loop` | 多步、可验收、需执行+审查 | `state/`、审查结果 |
| 意图校准 | `intent-normalizer` | 目标模糊、歧义 | 可执行意图 |
| 清理 | `cleanup` | 任务结束后 | 清理报告 |

## 本仓库技能来源

| 技能 | 用途 | 来源 |
|------|------|------|
| `skill-architecture` | 模块化技能架构 | 本仓库 |
| `cleanup` | 清理临时文件 | 本仓库 |
| `capture-gotcha` | 环境踩坑记录 | 本仓库 |
| `intent-normalizer` | 意图校准 | 本仓库 |
| `*-agent-loop` | 各平台 Agent 循环 | 本仓库 |

## 安装

```bash
git clone https://github.com/Innoksadk223/skills-repo.git ~/inno-skills
cd ~/inno-skills
bash setup.sh
```

常用：

```bash
bash setup.sh --dry-run
bash setup.sh --preset all
bash setup.sh --target codex --groups tools
bash setup.sh --target codex --skills hermes-agent-loop,cleanup
bash setup.sh --update-only
bash setup.sh --help
```

`setup.sh` 会：检测 agent → 同步到 `~/.agents/skills` → 在 Codex/Claude/Hermes skills 目录建链接；安装 capture-gotcha 时初始化 `~/.agents/env.md` 并建各端软链；**不删除**仓外已有技能。

## 更新

```bash
cd $(cat ~/.agents/skills/.skills-repo-path)
git pull
bash setup.sh --update-only
```

## 目录结构

```text
skills-repo/
├── skills/          # 本仓 7 个技能（扁平）
├── AGENTS.md        # Agent 通用入口
├── CLAUDE.md        # Claude Code 入口（与 AGENTS 同步）
├── CODEX.md         # Codex 入口（与 AGENTS 同步）
├── HERMES.md        # Hermes 入口（与 AGENTS 同步）
├── START.md         # 人类上手
├── README.md
└── setup.sh
```
