# Inno's Skills Pack

个人 AI Coding Agent 技能包，支持 **Claude Code**、**Codex**、**Hermes**。

> 小白上手看 [START.md](START.md) — 不用懂技术，会说目标就行。
>
> 知识库相关技能已拆到 [`kb-skills-repo`](https://github.com/Innoksadk223/kb-skills-repo)。

## AI 使用流程

收到安装请求后，AI 应按以下步骤：

1. **先介绍** — 按分组介绍技能，每组一句话概括
2. **再确认** — 问用户要装到哪个 agent、选哪些分组。涉及外部技能时，列出上游仓库地址，等用户确认后再安装
3. **再安装** — `bash setup.sh`
4. **最后教** — 安装/更新完成后，直接读 [START.md](START.md)，给用户一段 3 分钟上手教程

## 本仓库技能（17 个）

| 分组 | 技能 | 一句话 |
|------|------|--------|
| Minimax | `minimax-docx` / `minimax-pdf` / `minimax-xlsx` (3) | DOCX/PDF/XLSX 专业文档生成 |
| 搜索 | `anysearch` (1) | AnySearch 实时网页搜索、垂直领域搜索、批量搜索、URL 内容提取 |
| 前端 | `frontend-design` (1) | 高质量前端页面、组件和 Web App |
| 知识格式 | `wiki-to-okf` (1) | wiki 到 OKF 知识格式转换 |
| 工具 | `skill-creator` / `skill-architecture` / `skill-planner` / `cleanup` / `find-skills` / `grill-me` / `capture-gotcha` / `intent-normalizer` (8) | 技能创建、模块化架构、任务路由、清理、发现、质询、环境记录、意图校准 |
| Agent 循环 | `cc-agent-loop` / `codex-agent-loop` / `hermes-agent-loop` (3) | 各平台 Agent 编排循环（执行-审查分离） |

## 外部技能：从上游安装

以下技能不在本仓库，请从上游 GitHub 仓库安装：

| 技能 | 用途 | 上游仓库 |
|------|------|----------|
| `browser-use` | 浏览器自动化：网页测试、表单填充、截图、数据提取 | [browser-use/browser-use](https://github.com/browser-use/browser-use) |
| `ppt-agent` | 专业 PPT 演示文稿全流程生成 | [Akxan/ppt-agent-skill](https://github.com/Akxan/ppt-agent-skill) |
| `taste-skill` | 反模板化前端设计审美与落地检查 | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `ui-ux-pro-max` | UI/UX 设计、配色、字体、布局与多技术栈界面实现参考 | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |

AI 收到上述能力请求时，应引导用户从上游仓库安装，而非在本仓库中查找。

### 给 AI：外部技能安装约束

1. 不得主动安装任何外部技能。
2. 当用户请求的能力不在本仓库时，先说明所需技能来自哪个上游仓库。
3. 必须获得用户明确同意后方可执行安装。

## Superpowers

[Superpowers](https://github.com/obra/superpowers) 是一套完整的软件开发方法论技能包，包含头脑风暴、计划编写、技能编写、并行代理调度等。

安装方式见上游仓库 README：https://github.com/obra/superpowers

常用技能：
- `brainstorming` — 创意发散与方案梳理
- `writing-plans` — 轻量执行计划
- `writing-skills` — 技能编写与测试
- `dispatching-parallel-agents` — 并行子代理调度
- `using-superpowers` — Superpowers 入口

## 常用工作流入口

| 场景 | 工作流入口 | 适合什么时候用 | 产物 |
|------|----------|----------------|------|
| 复杂任务循环推进 | `agent-loop` | 任务有多步、可验收、需要执行与反馈循环 | `state/` 过程记录、Worker 产出、Feedbacker 反馈、主 Agent 验收结果 |
| 文档生成 | `minimax-docx` / `minimax-pdf` / `minimax-xlsx` | 要生成、修改、格式化 Word/PDF/Excel | 可交付文档或表格 |
| 前端 | `frontend-design` | 要做网页、组件或 Web App | 前端代码 |

## 详细来源

| 技能 | 用途 | 来源 |
|------|------|------|
| `anysearch` | 实时网页搜索、垂直领域搜索、批量搜索、URL 内容提取 | [AnySearch](https://www.anysearch.com/) |
| `wiki-to-okf` | 将 wiki 页面转换为 OKF 知识格式 | 本仓库 |
| `minimax-docx` | 专业 DOCX 文档创建与编辑 | Minimax 官方 |
| `minimax-pdf` | 高质量 PDF 生成与设计 | Minimax 官方 |
| `minimax-xlsx` | Excel 表格创建、分析与验证 | Minimax 官方 |
| `skill-creator` | 创建新的 AI 技能 | [clawhub.ai](https://clawhub.ai) |
| `skill-architecture` | 模块化技能架构设计 | 本仓库 |
| `skill-planner` | 收到任务时规划应调用的 skill 组合与顺序 | 本仓库 |
| `agent-loop` | 反馈驱动的 Agent 编排循环 | 本仓库 |
| `cleanup` | 任务完成后清理临时文件 | 本仓库 |
| `find-skills` | 发现和安装社区技能 | [vercel-labs/skills](https://github.com/vercel-labs/skills/tree/main/skills/find-skills) / Claude Code 社区生态 |
| `grill-me` | 深度质询方案/设计决策 | [mattpocock/skills](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) |
| `capture-gotcha` | 记录可复用的环境类踩坑经验 | 本仓库 |
| `intent-normalizer` | 将非专业、模糊或混合目标的用户表达校准成可执行意图 | 本仓库 |
| `frontend-design` | 创建高质量前端页面、组件和 Web App | Claude Code / 社区生态 |

## 安装

新手直接运行：

```bash
git clone https://github.com/Innoksadk223/skills-repo.git ~/inno-skills
cd ~/inno-skills
bash setup.sh
```

常用命令：

```bash
bash setup.sh --dry-run
bash setup.sh --preset all
bash setup.sh --target codex --groups tools,search
bash setup.sh --target codex --skills agent-loop,anysearch
bash setup.sh --update-only
bash setup.sh --help
```

`setup.sh` 会：

- 自动检测你装了哪些 agent
- 默认推荐安装常用核心技能
- 可按预设、分组或单个 skill 安装
- 先将仓库技能同步到 `~/.agents/skills` 主副本
- 在 Codex / Claude / Hermes 的 skills 目录中创建指向主副本的链接
- 不删除不在本仓库里的技能

## 给 Agent 的安装/更新指令

安装：

```bash
git clone https://github.com/Innoksadk223/skills-repo.git ~/inno-skills
cd ~/inno-skills
bash setup.sh
```

更新：

```bash
cd $(cat ~/.agents/skills/.skills-repo-path)
git pull
bash setup.sh --update-only
```

## 目录结构

```text
skills-repo/
├── skills/              ← 扁平结构（三个 agent 通用）
└── setup.sh
```
