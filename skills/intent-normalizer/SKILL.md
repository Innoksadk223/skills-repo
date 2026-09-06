---
name: intent-normalizer
description: Clarifies vague or ambiguous actionable requests into a minimally sufficient internal instruction, then hands the task to the appropriate skill or continues execution. Use automatically or when explicitly requested when the user's purpose, target, scope, or expected deliverable is unclear enough that plausible interpretations would materially change the result, or when following a proposed action instead of its stated goal could materially change the outcome. Inspect available context before asking questions. Do not use for clear requests, casual conversation, pure knowledge questions, or domain-specific detail gathering that belongs to another skill.
---

# Intent Normalizer

## 定位

把笼统或含义不清的行动请求澄清成下游能够正确处理的指令。

只处理宏观意图：用户想达成什么、针对什么、希望得到什么。风格、功能、技术方案和实施细节交给对应的专业技能。终点不是生成完整契约，而是在内部形成够用的明确指令并继续推进。

## 何时介入

满足以下条件时介入：

- 用户要求 AI 制作、修改、规划、选择或执行某件事。
- 目的、对象、范围或预期交付物存在会明显改变结果的不同理解。
- 用户同时给出目标和具体做法，而直接照做与围绕目标推进会产生明显不同结果。
- 用户显式要求先澄清、校准或规范化指令。

以下情况不介入：

- 现有对话、文件或材料已经能消除歧义。
- 缺少的只是可安全默认的次要细节。
- 请求已经明确，可以直接回答、执行或交给专业技能。
- 用户只是在闲聊或询问知识。

显式调用只会强制检查，不会为了使用本技能而制造问题；指令已经清楚时直接继续。

## 流程

1. **先读上下文**：检查当前对话、用户提供的材料、点名的文件和已有项目，不重复询问已经可知的信息。
2. **找到最小缺口**：只识别会改变目的、对象、范围、交付物或下游技能选择的歧义。用户同时给出目标和具体做法，但两者关系没有依据时，只确认是按指定做法执行，还是以目标为准交给专业技能选择做法；不展开完整领域诊断。
3. **必要时提问**：集中询问最少的问题，取得足以正确交棒的信息。
4. **内部清晰化**：用一句自然语言形成最短可执行指令；只包含已确认的目标、对象、预期结果和必要边界，不强制填固定字段。
5. **复述并交棒**：向用户用一句话复述最终理解，不等待额外确认，立即调用合适的专业技能或继续执行。用户纠正时再更新理解。

## 提问规则

- 通常一次问 1–3 个问题，硬上限为 5 个。
- 只问答案会改变下一步的问题，不为填模板追问。
- 存在真实候选时给 2–3 个生活化选项；项目名称、现有材料等事实允许用户直接填写。
- 只有上下文提供充分依据时才标推荐项；纯偏好不替用户决定。
- 不解释提问原因。
- 首轮回答产生新的重大分叉时，最多再追问一轮；其余缺口交给下游技能处理。

## 与其他技能协作

- 本技能只解决“要做什么、为什么做、做到什么程度”的宏观歧义。
- 专业技能负责自己的需求访谈，例如前端技能确定视觉与交互，PPT 技能确定叙事与版式，代码技能确定实现与验证。
- 能直接选择下游技能时立即交棒，不重复专业技能将要询问的内容。
- 不写任务契约文件，不维护独立状态，不替代规划、执行、审查或安全规则。

## 示例

### 模糊请求

用户：`帮我设计一下前端。`

先检查是否已有产品说明或项目。没有时，只澄清宏观缺口，例如：

1. 要设计的是哪种产品或页面？
2. 这个前端最主要要帮助用户完成什么？
3. 第一版希望拿到设计方向、可点击原型，还是可运行页面？

回答后内部形成一句明确指令，简短复述并交给前端设计技能；视觉风格、布局和技术实现由该技能继续处理。

### 明确请求

用户：`把 README 第三段翻译成英文，保留 Markdown 格式。`

不触发澄清，直接执行。
