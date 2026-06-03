---
name: skill-architecture
description: 模块化技能架构设计系统。在创建或重构任何 skill 时必须加载。提供松耦合/高内聚的模块拆分方法、断点续传的输出持久化机制、以及模块间通信契约模板。适用于新建 skill、skill 重构、skill 调试优化等场景。与 skill-creator 配合使用。
---

# 模块化技能架构设计系统

## 一句话

**把 Skill 看作流水线，每个模块是一个工位。工位之间只靠 state/ 文件通信。**

## 三条铁律

### 1. 模块化

每个模块 = 一个独立的 `references/M*.md`，包含五个标准段落：[模板见此](templates/module.md)

```markdown
## 状态检查    ← 先查 state/，有则跳过
## 输入        ← 需要什么数据，从哪来
## 执行        ← 步骤列表，不超过 7 步
## 输出        ← 保存到 state/M?_xxx.json
## 回滚        ← 失败时清理哪些文件
```

### 2. 松耦合 + 高内聚

| 原则 | 含义 | 反面 |
|------|------|------|
| **松耦合** | 模块只通过输入/输出契约通信 | ❌ "参考 Step 3 的变量 X" |
| **高内聚** | 一个模块只解决一个问题 | ❌ "同时生成 PPT 和写论文" |

### 3. 输出持久化

每个模块的输出**必须落盘**到 `state/` 目录。Agent 运行前检查 state/，存在则跳过——这就是断点续跑。

```
skill-name/
├── SKILL.md              ← 调度器（< 100 行，只列模块清单+决策树）
├── state/                ← 断点文件（.gitignore 此目录）
├── references/           ← 模块文件 M1_*.md, M2_*.md ...
├── scripts/
└── templates/
```

## SKILL.md 的职责

**只做两件事**：列出模块清单、写决策树。**不是**写执行细节。格式见 [templates/scheduler.md](templates/scheduler.md)。

## 与 skill-creator 的协作

加载本技能后，skill-creator 的 Step 4（Edit the Skill）采用模块化方式：

| skill-creator 负责 | 本技能负责 |
|-------------------|----------|
| init → edit → package 流程 | edit 阶段的模块拆分 |
| YAML / description | SKILL.md 调度器写法 |
| 打包和发布 | 模块契约和断点设计 |

## 参考

| 文件 | 何时加载 |
|------|---------|
| [templates/module.md] | 创建新模块时复制 |
| [templates/scheduler.md] | 写 SKILL.md 调度器时参考 |
| [references/runtime.md] | 首次实现运行逻辑时 |
| [references/anti-patterns.md] | 有坏味道时排查 |
| [references/real-example.md] | 需要完整示例时 |
