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
2. **再确认** — 问用户要装到哪个 agent、选哪些分组。涉及外部技能时，列出上游地址，等用户确认后再安装
3. **再安装** — `bash setup.sh`
4. **最后教** — 安装/更新完成后，直接读 [START.md](START.md)，给用户一段 3 分钟上手教程

## 本仓库技能（8 个）

| 分组 | 技能 | 一句话 |
|------|------|--------|
| 工具 | `skill-architecture` / `skill-planner` / `cleanup` / `capture-gotcha` / `intent-normalizer` (5) | 模块化架构、任务路由、清理、环境记录、意图校准 |
| Agent 循环 | `cc-agent-loop` / `codex-agent-loop` / `hermes-agent-loop` (3) | 各平台 Agent 编排循环（执行-审查分离） |

## 外部技能：从上游安装

以下技能不在本仓库，请从上游安装（AI 不得擅自安装，须用户同意）：

| 技能 | 用途 | 上游 / 安装 |
|------|------|-------------|
| `anysearch` | 实时搜索、垂直搜索、批量搜索、URL 提取 | [GitHub](https://github.com/anysearch-ai/anysearch-skill) · [releases](https://github.com/anysearch-ai/anysearch-skill/releases) · `npx skills add https://github.com/anysearch-ai/anysearch-skill --skill anysearch` |
| `grill-me` | 深度质询方案/设计 | [路径](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) · [skills.sh](https://www.skills.sh/mattpocock/skills/grill-me) · `npx skills add https://github.com/mattpocock/skills --skill grill-me` |
| `frontend-design` | 高质量前端页面/组件 | [路径](https://github.com/anthropics/skills/tree/main/skills/frontend-design) · [skills.sh](https://www.skills.sh/anthropics/skills/frontend-design) · `npx skills add https://github.com/anthropics/skills --skill frontend-design` |
| `skill-creator` | 创建新技能 | [clawhub.ai](https://clawhub.ai)（slug: `skill-creator`） |
| `find-skills` | 发现/安装社区技能 | [路径](https://github.com/vercel-labs/skills/tree/main/skills/find-skills) · [skills.sh](https://www.skills.sh/vercel-labs/skills/find-skills) · `npx skills add https://github.com/vercel-labs/skills --skill find-skills` |
| `browser-use` | 浏览器自动化 | [browser-use/browser-use](https://github.com/browser-use/browser-use) |
| `ppt-agent` | PPT 全流程生成 | [Akxan/ppt-agent-skill](https://github.com/Akxan/ppt-agent-skill) |
| `taste-skill` | 反模板化前端审美 | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `ui-ux-pro-max` | UI/UX 设计参考 | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |

### 给 AI：外部技能安装约束

1. 不得主动安装任何外部技能。
2. 能力不在本仓库时，先说明上游并给出下载/安装地址。
3. 必须获得用户明确同意后方可执行安装。

## Superpowers

[Superpowers](https://github.com/obra/superpowers) — 头脑风暴、计划、技能编写、并行代理等。安装见上游 README：https://github.com/obra/superpowers

常用：`brainstorming` · `writing-plans` · `writing-skills` · `dispatching-parallel-agents` · `using-superpowers`

## 常用工作流入口

| 场景 | 入口 | 何时用 | 产物 |
|------|------|--------|------|
| 复杂任务循环 | `hermes-agent-loop` / `cc-agent-loop` / `codex-agent-loop` | 多步、可验收、需执行+审查 | `state/`、审查结果 |
| 任务路由 | `skill-planner` | 规划 skill 组合与顺序 | 路由表 |
| 意图校准 | `intent-normalizer` | 目标模糊、歧义 | 可执行意图 |
| 清理 | `cleanup` | 任务结束后 | 清理报告 |

## 本仓库技能来源

| 技能 | 用途 | 来源 |
|------|------|------|
| `skill-architecture` | 模块化技能架构 | 本仓库 |
| `skill-planner` | 任务 skill 路由 | 本仓库 |
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

`setup.sh` 会：检测 agent → 同步到 `~/.agents/skills` → 在 Codex/Claude/Hermes skills 目录建链接；**不删除**仓外已有技能。

## 更新

```bash
cd $(cat ~/.agents/skills/.skills-repo-path)
git pull
bash setup.sh --update-only
```

## 目录结构

```text
skills-repo/
├── skills/          # 本仓 8 个技能（扁平）
├── AGENTS.md        # Agent 通用入口
├── CLAUDE.md        # Claude Code 入口（与 AGENTS 同步）
├── CODEX.md         # Codex 入口（与 AGENTS 同步）
├── HERMES.md        # Hermes 入口（与 AGENTS 同步）
├── START.md         # 人类上手
├── README.md
└── setup.sh
```
