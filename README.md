# Inno's Skills Pack

个人 AI Coding Agent 技能包，支持 **Claude Code**、**Codex**、**Hermes**。

> 小白上手看 [START.md](START.md) — 不用懂技术，会说目标就行。
>
> 知识库相关技能已拆到 [`kb-skills-repo`](https://github.com/Innoksadk223/kb-skills-repo)。本仓库只保留通用工具、文档生成、搜索、审阅、前端/PPT/UI 和方法论技能。

## AI 使用流程

收到安装请求后，AI 应按以下步骤：

1. **先介绍** — 按分组介绍技能，每组一句话概括
2. **再确认** — 问用户要装到哪个 agent、选哪些分组
3. **再安装** — `bash setup.sh`
4. **最后教** — 安装/更新完成后，直接读 [START.md](START.md)，给用户一段 3 分钟上手教程

## 技能速查（27 个）

| 分组 | 技能 | 一句话 |
|------|------|--------|
| 浏览器 | `browser-use` (1) | 网页自动化：网页测试、表单填充、截图、数据提取 |
| Minimax | `minimax-docx` / `minimax-pdf` / `minimax-xlsx` (3) | DOCX/PDF/XLSX 专业文档生成 |
| 搜索 | `anysearch` (1) | AnySearch 实时网页搜索、垂直领域搜索、批量搜索、URL 内容提取 |
| 学术 | `academic-paper-review` / `social-science-paper-review` / `wiki-to-okf` (3) | 论文审阅、社科稿件评审、wiki 到 OKF 转换 |
| 创作 | `ppt-agent` / `frontend-design` / `taste-skill` / `ui-ux-pro-max` (4) | 专业 PPT、前端页面、UI/UX 设计与反模板化审美 |
| Superpowers | `using-superpowers` / `brainstorming` / `writing-plans` / `systematic-debugging` / `test-driven-development` / `verification-before-completion` (6) | 轻量通用方法论：澄清、计划、排查、验收、验证、收尾 |
| 工具 | `skill-creator` / `skill-architecture` / `skill-planner` / `agent-loop` / `cleanup` / `find-skills` / `grill-me` / `capture-gotcha` / `intent-normalizer` (9) | 技能创建、模块化架构、任务路由、Agent 编排、清理、发现、质询、环境记录、意图校准 |

## 常用工作流入口

| 场景 | 工作流入口 | 适合什么时候用 | 产物 |
|------|----------|----------------|------|
| 复杂任务循环推进 | `agent-loop` | 任务有多步、可验收、需要执行与反馈循环 | `state/` 过程记录、Worker 产出、Feedbacker 反馈、主 Agent 验收结果 |
| 文档生成 | `minimax-docx` / `minimax-pdf` / `minimax-xlsx` | 要生成、修改、格式化 Word/PDF/Excel | 可交付文档或表格 |
| 论文审阅 | `academic-paper-review` / `social-science-paper-review` | 要评估论文质量、方法问题、修改方向 | 审稿式问题清单和修改建议 |
| 前端/PPT/UI | `ppt-agent` / `frontend-design` / `taste-skill` / `ui-ux-pro-max` | 要做演示稿、网页、界面或设计审查 | HTML/PPT/前端代码/设计建议 |

## 详细来源

| 技能 | 用途 | 来源 |
|------|------|------|
| `browser-use` | 浏览器自动化 | [browser-use](https://github.com/browser-use/browser-use) |
| `anysearch` | 实时网页搜索、垂直领域搜索、批量搜索、URL 内容提取 | [AnySearch](https://www.anysearch.com/) |
| `academic-paper-review` | 论文审阅、方法论评估、同行评审 | [bytedance/deer-flow](https://github.com/bytedance/deer-flow) |
| `social-science-paper-review` | 社科论文严格审阅与修改建议 | 本仓库 |
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
| `using-superpowers` | 轻量选择方法论技能 | 本仓库，轻量改编自 [obra/superpowers](https://github.com/obra/superpowers) |
| `brainstorming` | 在目标、约束或路线不清时做简短澄清与方案对比 | 同上 |
| `writing-plans` | 为多步骤任务写计划 | 同上 |
| `systematic-debugging` | 对失败、异常行为或反复尝试无效的问题做根因排查 | 同上 |
| `test-driven-development` | 先定义验收条件，再行动 | 同上 |
| `verification-before-completion` | 完成前核验证据 | 同上 |
| `ppt-agent` | 专业 PPT 演示文稿全流程生成 | [Akxan/ppt-agent-skill](https://github.com/Akxan/ppt-agent-skill) |
| `frontend-design` | 创建高质量前端页面、组件和 Web App | Claude Code / 社区生态 |
| `taste-skill` | 反模板化前端设计审美与落地检查 | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `ui-ux-pro-max` | UI/UX 设计、配色、字体、布局与多技术栈界面实现参考 | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |

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
├── skills/              ← 扁平结构（Claude Code / Codex）
├── skills-hermes/       ← 分类结构（Hermes；按用途分组）
│   ├── browser-use/
│   ├── minimax/
│   ├── creative/
│   ├── superpowers/
│   └── ...
└── setup.sh
```
