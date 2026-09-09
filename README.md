# Inno's Skills Pack

个人 AI Coding Agent 技能包，支持 **Claude Code**、**Codex**、**Hermes** 与 **Pi**。

本文供人和 AI 共同阅读，包含技能介绍、安装和使用说明。仓库维护规则见 [AGENTS.md](AGENTS.md)。

知识库相关技能位于独立仓库 [`kb-skills-repo`](https://github.com/Innoksadk223/kb-skills-repo)。

## 本仓库技能（9 个）

| 分组 | 技能 | 一句话 |
|------|------|--------|
| 工具 | `cleanup` / `capture-gotcha` (2) | 清理、环境记录 |
| Agent 循环 | `cc-agent-loop` / `codex-agent-loop` / `hermes-agent-loop` / `pi-agent-loop` (4) | 各平台 Agent 编排循环（执行-审查分离） |
| 内容与提示词 | `image-prompt-designer` / `uiux-prompt-designer` / `xiaohongshu-content-formatter` (3) | 图片提示词、界面提示词与小红书图文整理 |

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
| 复杂任务循环 | `hermes-agent-loop` / `cc-agent-loop` / `codex-agent-loop` / `pi-agent-loop` | 多步、可验收、需执行+审查 | `state/`、审查结果 |
| 经验记忆 | `capture-gotcha` | 任务开始与修复后 | 项目、全局经验及候选记录 |
| 清理 | `cleanup` | 任务结束后 | 清理报告 |

## 安装与更新

可以直接告诉 AI：“把本仓库的 cleanup 和 capture-gotcha 安装到我正在使用的 Agent。”

AI 先确认目标 Agent 与所需技能，检查其实际支持的技能目录，再将 `skills/<技能名>/` 完整目录链接或复制到该位置。保留脚本和参考资料，不只复制 `SKILL.md`；遇到已有同名内容先比较，保护用户修改与外部技能。

优先链接到本仓库，更新仓库后链接即可读取最新内容；如果使用复制安装，更新后还需同步对应技能目录。更新前检查本地修改，不强制覆盖。安装完成后确认 Agent 能发现技能，并说明如何调用。

## 使用

直接描述目标，或点名技能，例如“用 cleanup 检查本次过程文件”“按 capture-gotcha 读取已有经验”。复杂任务按所用 Agent 选择对应的循环技能。

- `capture-gotcha`：任务开始读取项目与全局正式记忆，修复后记录可复用经验；候选不参与正常召回。具体命令见其 `SKILL.md`，从项目根目录执行，脚本路径以实际安装位置为准。
- `cleanup`：结束前按用途检查过程产物；一次性制作工具先列明再确认删除，最终产品、正式测试和用户资料保留。

技能的自动触发取决于 Agent 配置。需要稳定读取记忆时，将任务开始执行 `recall` 的要求加入实际生效的 Agent 规则入口；不要把安装技能等同于安装自动钩子。

## 目录结构

```text
skills-repo/
├── skills/          # 9 个根技能
├── AGENTS.md        # 仓库维护规则
└── README.md        # 人与 AI 共用的介绍、安装和上手说明
```
