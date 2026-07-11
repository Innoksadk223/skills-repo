# 3 分钟上手 Inno's Skills Pack

这个技能包会给 Claude Code、Codex、Hermes 增加一组常用能力。你不用记技能名，也不用懂技术。

**直接告诉 AI 你想做什么，它会自己选择合适的技能。**

知识库相关技能请使用独立仓库：[`kb-skills-repo`](https://github.com/Innoksadk223/kb-skills-repo)。

Agent 自动读取入口（内容一致）：[AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) / [CODEX.md](CODEX.md) / [HERMES.md](HERMES.md)。

---

## 给 AI：安装后的介绍流程

用户安装或更新完成后，不要只说「装好了」，也不要先问用户要不要介绍。默认给一段 3 分钟上手教程：

> 技能包已经装好。我先用 3 分钟带你上手：你不用记技能名，直接说目标，AI 会自己选技能。  
> 如果你只想听总览，我会讲最短版；也可以选一个方向深入讲：任务路由、意图校准、Agent 循环、工具类技能。

介绍时：

1. 先用一句话说明：**用户只管说目标，AI 负责挑技能。**
2. 给最短总览和 3-5 个常用说法示例，不要一次灌输全部细节。
3. 结尾问用户想重点了解哪一组；如果用户明确说不用介绍，就收住。
4. 用户问知识库、RAG、Obsidian 或论文来源补充时，说明相关技能已拆到 `kb-skills-repo`。
5. 用户问实时搜索、前端设计、技能发现/创建、浏览器自动化、PPT、UI 设计、头脑风暴时，说明这些能力需从上游安装，见下方「需要额外安装的能力」。

---

## 你可以怎么用？

### 任务路由 / 意图校准

你可以说：

> 「先帮我规划该用哪些技能」  
> 「我这个目标有点乱，先帮我理清再做」  
> 「先澄清歧义，再给执行路线」

### Agent 循环

你可以说：

> 「这个任务要多轮执行和审查」  
> 「按 agent-loop 推进，做到可验收」

### 工具类

你可以说：

> 「清理一下项目里的临时文件」  
> 「帮我设计一个模块化技能」  
> 「把这次踩坑记下来」

---

## 常用说法速查

| 你想做 | 直接这样说 |
|---|---|
| 规划技能组合 | 「先规划该用哪些技能」 |
| 理清模糊目标 | 「先帮我澄清目标」 |
| 多轮任务 | 「按 agent-loop 推进」 |
| 清理文件 | 「清理临时文件」 |
| 设计新技能架构 | 「帮我设计一个模块化技能」 |
| 记录踩坑 | 「把这次环境问题记成 gotcha」 |

---

## 想精准指定某个技能

大多数时候不用指定技能名。AI 会自动匹配。

如果你知道要用哪个技能，可以直接点名：

> 「用 skill-planner 规划一下」  
> 「用 intent-normalizer 先校准意图」  
> 「加载 cleanup 清理一下」

不同 agent 也可以这样触发：

- Claude Code / Codex：直接说人话，或说「用 xxx 技能」。
- Hermes：可以直接说「加载 xxx 技能」，也可以用 `/skill-name`。

---

## 需要额外安装的能力

以下能力不在本技能包，需从上游安装：

| 能力 | 上游 / 下载 |
|------|-------------|
| 实时搜索 `anysearch` | [anysearch-ai/anysearch-skill](https://github.com/anysearch-ai/anysearch-skill) |
| 方案质询 `grill-me` | [mattpocock/skills · grill-me](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) |
| 前端设计 `frontend-design` | [anthropics/skills · frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) |
| 技能创建 `skill-creator` | [clawhub.ai](https://clawhub.ai) |
| 技能发现 `find-skills` | [vercel-labs/skills · find-skills](https://github.com/vercel-labs/skills/tree/main/skills/find-skills) |
| 浏览器自动化 | [browser-use](https://github.com/browser-use/browser-use) |
| PPT 演示文稿 | [ppt-agent](https://github.com/Akxan/ppt-agent-skill) |
| 前端设计审美 | [taste-skill](https://github.com/Leonxlnx/taste-skill) |
| UI/UX 设计参考 | [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |
| 通用方法论（头脑风暴、计划、调试、核验） | [Superpowers](https://github.com/obra/superpowers) |

跟 AI 说「安装 anysearch」或「安装 Superpowers」，AI 会先告知上游地址，获得你同意后再执行拉取，不会自动安装。

---

## 不确定怎么说？

直接说你的目标就行：

> 「我想让 AI 帮我做个复杂任务，但不知道用哪个技能」  
> 「先帮我理清目标再动手」

AI 应该先帮你判断该用哪组技能，再问必要的问题。

**核心原则：你只管说你要什么，AI 负责选技能。选错了就说「不对，用 xxx 技能」。**

---

## 更新

过段时间想更新技能，跟 AI 说：

> 「更新一下技能包」

或者直接甩 GitHub 链接：

> 「更新这个 https://github.com/Innoksadk223/skills-repo」

AI 会自动找到安装位置、拉取最新版、更新有变化的技能。
