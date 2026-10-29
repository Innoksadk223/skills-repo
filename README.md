# Inno's Skills Pack

个人 AI Agent 技能包，面向 **Claude Code**、**Codex**、**Hermes** 与 **Pi**。具体技能的工具依赖与适用范围见各自说明；`pi-agent-loop` 依赖 Pi 的 Agent Team 编排能力。

本文供人和 AI 共同阅读，介绍技能、安装与使用；仓库维护规则见 [AGENTS.md](AGENTS.md)。知识库相关技能位于独立仓库 [`kb-skills-repo`](https://github.com/Innoksadk223/kb-skills-repo)。

## 本仓库技能（6 个）

发布清单以 Git 跟踪的技能目录为准，不包含被忽略的本机技能。点击技能名查看完整规则。

| 技能 | 用途与使用时机 |
|------|----------------|
| [cleanup](skills/cleanup/SKILL.md) | 任务收尾或整理目录时，检查过程文件、旧备份和过期资料，按实际用途与恢复价值决定去留，最终产品和用户资料保留。 |
| [user-profile](skills/user-profile/SKILL.md) | 维护跨任务有效的用户特点与协作偏好，新对话或上下文丢失后读取；「回顾画像」「总结画像」触发本次交流的整理写入，先列候选供用户选定；不记具体任务材料。 |
| [pi-agent-loop](skills/pi-agent-loop/SKILL.md) | 需要用子代理或会话做多代理流程编排时使用：先定计划，再分派执行与独立审查，最后由人验收。 |
| [image-prompt-designer](skills/image-prompt-designer/SKILL.md) | 把文字需求或成品图片整理成可直接使用的生图提示词，并可保存、复用视觉风格；不直接生成图片。 |
| [uiux-prompt-designer](skills/uiux-prompt-designer/SKILL.md) | 把产品需求或界面图片整理成可复用的 UI/UX 提示词与风格配置；不直接实现或审查界面。 |
| [plain-output](skills/plain-output/SKILL.md) | 写中文回复或文档时主动遵循的表达规范，减少空话和无依据判断；属于写作规范，不是润色流程。 |

## 安装与更新

可以直接告诉 AI：“把本仓库的 cleanup 和 user-profile 安装到我正在使用的 Agent。”

1. 确认目标 Agent、所需技能及其实际加载目录，不假定所有 Agent 使用相同路径。
2. 将 `skills/<技能名>/` **完整目录**链接或复制到加载位置，保留脚本和参考资料；遇到同名内容先比较，不覆盖用户修改或已有外部技能。
3. 优先链接到本仓库，便于后续读取更新；复制安装则需再次同步。更新前检查本地修改，不强制覆盖。
4. 安装后确认 Agent 能发现技能、所需工具可用，并说明调用方式。

技能的自动触发取决于 Agent 配置，安装不等于增加自动执行钩子。需要在任务开始稳定读取经验或画像时，应将读取要求加入实际生效的 Agent 规则入口；修改配置前先确认。

## 使用

直接描述目标，或点名技能，例如：

- “用 cleanup 检查过程文件和旧备份。”历史文件与一次性制作工具先列清单确认删除；最终产品、正式测试和用户资料保留。
- “用 pi-agent-loop 推进这项任务。”先确认计划，再分配执行与独立审查。

- “查看画像”“回顾画像”“总结画像”“记住这个偏好”“纠正这条”“忘记这条”。具体记录边界见 `user-profile`。

## 外部推荐（自用清单）

以下技能与工具**不在本仓库**，需从上游安装。AI 应先说明用途、提供上游与安装地址，取得用户明确同意后再执行；不得主动安装。

| 技能或工具 | 用途 | 上游 / 安装 |
|------------|------|-------------|
| `anysearch` | 实时搜索、垂直搜索、批量搜索、URL 提取 | [anysearch-ai/anysearch-skill](https://github.com/anysearch-ai/anysearch-skill) · 技能市场搜 `anysearch`，或下载 [release zip](https://github.com/anysearch-ai/anysearch-skill/releases) 解压到技能目录，再按上游 README 跑一次入口自检 |
| `grill-me`（执行体为 `grilling`） | 深度质询方案/设计，每轮用提问卡片推进 | [mattpocock/skills](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) · `npx skills add https://github.com/mattpocock/skills --skill grill-me` |
| `hallmark` | 反 AI 味界面设计；2.0 起只用于新建页面，改已有设计需点名 hallmark | [Nutlope/hallmark](https://github.com/Nutlope/hallmark) · `npx skills add nutlope/hallmark -g` |
| `skill-creator` | 创建新技能 | [anthropics/skills · skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) · `npx skills add https://github.com/anthropics/skills --skill skill-creator` |
| `playwright-cli` | 浏览器自动化（Playwright CLI + Skills） | [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) · `npm install -g @playwright/cli@latest` 后 `npx skills add microsoft/playwright-cli@playwright-cli` |
| `ponytail` | 反过度工程：最懒且能用的解 | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) · `npx skills add https://github.com/DietrichGebert/ponytail --skill ponytail` |
| `rtk` | CLI 输出压缩，降低 LLM token（工具，非 skill 包） | [rtk-ai/rtk](https://github.com/rtk-ai/rtk) · `brew install rtk` 后 `rtk init -g --agent hermes`（Claude/Codex 见上游） |
| `ppt-agent` | PPT 全流程生成 | [Akxan/ppt-agent-skill](https://github.com/Akxan/ppt-agent-skill) · `npx skills add Akxan/ppt-agent-skill` |
| `design-taste-frontend`（仓库名 `taste-skill`） | 反模板化前端审美，v2 从 247 个画廊站点抽签给方向，配真浏览器检查脚本 | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) · `npx skills add https://github.com/Leonxlnx/taste-skill --skill taste-skill` |
| `ui-ux-pro-max` | UI/UX 设计参考；上游一次装 7 个技能（另含 banner-design、brand、design、design-system、slides、ui-styling） | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |
| `agent-reach` | 15 个平台的只读采集（小红书/推特/B站/Reddit/LinkedIn 等），自带工具拿不到正文时补缺口 | [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) · 让 Agent 读 [install.md](https://raw.githubusercontent.com/Panniantong/Agent-Reach/main/docs/install.md) 后执行 |
| `archify` | 架构、流程、状态图，产出可交互的独立 HTML | [tt-a1i/archify](https://github.com/tt-a1i/archify) · `npx skills add tt-a1i/archify -g` |

## 目录结构

```text
skills-repo/
├── skills/          # 发布技能，详见上方清单
├── AGENTS.md        # AI 维护仓库时遵循的规则
└── README.md        # 技能介绍、安装与使用说明
```
