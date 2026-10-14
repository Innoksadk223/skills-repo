# Inno's Skills Pack

个人 AI Agent 技能包，面向 **Claude Code**、**Codex**、**Hermes** 与 **Pi**。具体技能的工具依赖与适用范围见各自说明；`pi-agent-loop` 依赖 Pi 的 Agent Team 编排能力。

本文供人和 AI 共同阅读，介绍技能、安装与使用；仓库维护规则见 [AGENTS.md](AGENTS.md)。知识库相关技能位于独立仓库 [`kb-skills-repo`](https://github.com/Innoksadk223/kb-skills-repo)。

## 本仓库技能（7 个）

发布清单以 Git 跟踪的技能目录为准，不包含被忽略的本机技能。点击技能名查看完整规则。

| 技能 | 用途与使用时机 |
|------|----------------|
| [cleanup](skills/cleanup/SKILL.md) | 任务收尾或整理目录时，检查过程文件、旧备份和过期资料，按实际用途与恢复价值决定去留，最终产品和用户资料保留。 |
| [capture-gotcha](skills/capture-gotcha/SKILL.md) | 开始项目、终端、浏览器或文件类任务时，先召回已确认的项目与全局经验；修复验证后再把可复用经验写回对应位置，未证实的只存候选。记忆各限 4000 码点，维护用 `inspect` 与 `replace` 显式进行。 |
| [user-profile](skills/user-profile/SKILL.md) | 维护跨任务有效的用户特点与协作偏好，新对话或上下文丢失后读取；不记具体任务材料。 |
| [pi-agent-loop](skills/pi-agent-loop/SKILL.md) | 需要用子代理或会话做多代理流程编排时使用：先定计划，再分派执行与独立审查，最后由人验收。 |
| [image-prompt-designer](skills/image-prompt-designer/SKILL.md) | 把文字需求或成品图片整理成可直接使用的生图提示词，并可保存、复用视觉风格；不直接生成图片。 |
| [uiux-prompt-designer](skills/uiux-prompt-designer/SKILL.md) | 把产品需求或界面图片整理成可复用的 UI/UX 提示词与风格配置；不直接实现或审查界面。 |
| [plain-output](skills/plain-output/SKILL.md) | 写中文回复或文档时主动遵循的表达规范，减少空话和无依据判断；属于写作规范，不是润色流程。 |

## 安装与更新

可以直接告诉 AI：“把本仓库的 cleanup 和 capture-gotcha 安装到我正在使用的 Agent。”

1. 确认目标 Agent、所需技能及其实际加载目录，不假定所有 Agent 使用相同路径。
2. 将 `skills/<技能名>/` **完整目录**链接或复制到加载位置，保留脚本和参考资料；遇到同名内容先比较，不覆盖用户修改或已有外部技能。
3. 优先链接到本仓库，便于后续读取更新；复制安装则需再次同步。更新前检查本地修改，不强制覆盖。
4. 安装后确认 Agent 能发现技能、所需工具可用，并说明调用方式。

技能的自动触发取决于 Agent 配置，安装不等于增加自动执行钩子。需要在任务开始稳定读取经验或画像时，应将读取要求加入实际生效的 Agent 规则入口；修改配置前先确认。

## 使用

直接描述目标，或点名技能，例如：

- “用 cleanup 检查过程文件和旧备份。”历史文件与一次性制作工具先列清单确认删除；最终产品、正式测试和用户资料保留。
- “按 capture-gotcha 读取已有经验。”从项目根目录执行 `recall`，脚本路径以实际安装位置为准。
- “用 pi-agent-loop 推进这项任务。”先确认计划，再分配执行与独立审查。

- “查看画像”“记住这个偏好”“纠正这条”“忘记这条”。具体记录边界见 `user-profile`。

### 经验记忆：容量与维护

- 数据分三份：全局 `~/.agents/gotchas.md`、项目 `<项目根>/.agents/gotchas.md`、候选 `<项目根>/.agents/gotchas-candidates.md`；候选不参与 `recall`。三份各限 4000 个 Unicode 码点。
- 记什么、写到哪个范围由 AI 按技能规则判断；`add`、`promote`、`replace` 只保障容量、版本与写入安全，不核实事实、也不保证脱敏完备。
- 读取用 `recall`（项目在先、全局在后，可选多个关键词，按命中词数排序；全不命中时列出可用标题）；查看用 `inspect --scope global|project|candidate`（只读，给出路径、字符数、是否超限、版本与正文，并标出 `ok`／`legacy`／`readable`／`partial`／`invalid`）。单份文件读不出只影响它自己；格式坏掉的个别记录会被跳过并逐条报出，不连坐同文件其余记录。已知限制（非 UTF-8 或无头行仍整份丢、锁文件常驻、promote 非事务等）见技能里的「已知限制」一节。
- 精简、合并或删除记录前先说明具体方案并取得同意，再用 `replace --scope ... --from-file <修订稿> --expect <版本>` 整份提交；版本不符则拒绝写入。修复超限文件与把旧格式迁到新格式也只走 `replace`。
- 每条记录是 `# Gotchas` 下的一条 `### 标题`，字段为 `适用`、`做法`、`验证`；字段值必须单行，标题写可迁移规则名而非某次事故名，`验证` 以 `YYYY-MM-DD` 开头并附最短证据。旧的五字段记录仍可读取，写入入口只接受新格式并要求先迁移。

### 用户画像：数据与接入

- 数据保存在 `~/.agents/user-profile/profile.md` 和 `changes.md`，不进入本仓库；初始无个人条目，两份文件各限 4000 个 Unicode 码点。
- AI 按技能中的六类规则判断哪些内容值得保存；正式写入统一通过 `profile_store.py`，由脚本检查容量、版本并写入，历史按需读取。手工编辑可绕过写入入口，但读取仍会检查容量。
- 不把无关背景带入回答；敏感信息先确认，凭证不存。数据保存在本机，读取后仍会进入所用模型的上下文。

本机 PI-Desktop 的接入方式是在 `~/.pi/agent/AGENTS.md` 中要求：新对话先读取 `~/.agents/skills/user-profile/SKILL.md`，再运行：

```bash
python3 ~/.agents/skills/user-profile/scripts/profile_store.py read
```

这是指令式加载，不是强制注入。上述路径对应本机安装位置，其他环境需核对实际路径和规则入口，不自动照搬或修改。

## 外部推荐（自用清单）

以下技能与工具**不在本仓库**，需从上游安装。AI 应先说明用途、提供上游与安装地址，取得用户明确同意后再执行；不得主动安装。

| 技能或工具 | 用途 | 上游 / 安装 |
|------------|------|-------------|
| `anysearch` | 实时搜索、垂直搜索、批量搜索、URL 提取 | [anysearch-ai/anysearch-skill](https://github.com/anysearch-ai/anysearch-skill) · `npx skills add https://github.com/anysearch-ai/anysearch-skill --skill anysearch` |
| `grill-me` | 深度质询方案/设计 | [mattpocock/skills · grill-me](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) · `npx skills add https://github.com/mattpocock/skills --skill grill-me` |
| `frontend-design` | 高质量前端页面/组件 | [anthropics/skills · frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) · `npx skills add https://github.com/anthropics/skills --skill frontend-design` |
| `hallmark` | 反 AI 味界面设计：新建页面、审计、重设计与设计提取 | [Nutlope/hallmark](https://github.com/Nutlope/hallmark) · `npx skills add nutlope/hallmark` |
| `skill-creator` | 创建新技能 | [clawhub.ai](https://clawhub.ai)（slug: `skill-creator`） |
| `find-skills` | 发现/安装社区技能 | [vercel-labs/skills · find-skills](https://github.com/vercel-labs/skills/tree/main/skills/find-skills) · `npx skills add https://github.com/vercel-labs/skills --skill find-skills` |
| `playwright-cli` | 浏览器自动化（Playwright CLI + Skills） | [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) · `npx skills add microsoft/playwright-cli@playwright-cli` |
| `browser-use` | 浏览器控制：会话跨命令持久，隔离／真实 Chrome／云端三种模式，CDP 直连可复用已登录状态 | [browser-use/browser-use](https://github.com/browser-use/browser-use) · `uv tool install browser-use` 后 `browser-use skill install`；接线说明见 [browser-harness install.md](https://github.com/browser-use/browser-harness/blob/main/install.md) |
| `ponytail` | 反过度工程：最懒且能用的解 | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) · `npx skills add https://github.com/DietrichGebert/ponytail --skill ponytail` |
| `rtk` | CLI 输出压缩，降低 LLM token（工具，非 skill 包） | [rtk-ai/rtk](https://github.com/rtk-ai/rtk) · `brew install rtk` 后 `rtk init -g --agent hermes`（Claude/Codex 见上游） |
| `ppt-agent` | PPT 全流程生成 | [Akxan/ppt-agent-skill](https://github.com/Akxan/ppt-agent-skill) |
| `taste-skill` | 反模板化前端审美 | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `ui-ux-pro-max` | UI/UX 设计参考 | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |
| Superpowers | 头脑风暴、计划、技能编写、并行代理 | [obra/superpowers](https://github.com/obra/superpowers) |

## 目录结构

```text
skills-repo/
├── skills/          # 发布技能，详见上方清单
├── AGENTS.md        # AI 维护仓库时遵循的规则
└── README.md        # 技能介绍、安装与使用说明
```
