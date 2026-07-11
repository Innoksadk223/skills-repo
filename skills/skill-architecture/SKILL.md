---
name: skill-architecture
description: "Modular skill architecture design system with pipeline modules, state-based resumability, and loose coupling via state/ file IPC. Use when creating, updating, or refactoring skills that need: (1) multi-step pipelines with checkpoint/resume, (2) module decomposition with file-based communication between steps, (3) coordination with external skill-creator during the edit phase, or (4) anti-pattern diagnosis in existing modular skills."
---

# 技能架构设计原则

## 一句话

**把 Skill 看作流水线，每个模块是一个工位。工位之间只靠 state/ 文件通信。**

## 三条原则

### 1. 模块边界：松耦合 + 高内聚

模块间只通过输入/输出契约通信。改一个模块的内部实现不应波及其他模块。

| 判断 | 达标 | 反面 |
|------|------|------|
| 松耦合 | M3 只读 `state/M2_xxx.json` | ❌ "参考 M2 第 47 行的变量" |
| 高内聚 | 一个模块只解决一个问题 | ❌ "搜索 + 格式化 + 大纲" |

**拆分信号**：步骤 >7、多职责、各步需独立调试。**合并信号**：两个模块总一起执行、共享全部 state。

### 2. 状态持久化

模块输出落盘到 `state/`。运行前检查 state/，存在则跳过--这就是断点续跑。无需断点续跑的 skill 不需要此模式。

```
skill-name/
├── SKILL.md        ← 调度器（只列模块清单+决策树，≤100 行）
├── state/          ← 断点文件（.gitignore）
├── references/     ← 模块文件 M1_*.md, M2_*.md ...
├── scripts/
└── templates/
```

state 格式统一：结构化数据用 `.json`，长文本用 `.md`，模板保留原扩展名。

### 3. 可维护性

- **接口稳定**：模块间通信靠 state 文件名和格式，改内部实现不改 state 契约
- **局部修改安全**：改 M3 只需重跑 M3，M1/M2 的 state 不受影响
- **演进安全**：新增步骤追加到管道末尾或插入中间模块，前置模块输出不变

## 适用判断

| 场景 | 模式 | 何时不用本技能 |
|------|------|---------------|
| 线性管道，步骤有先后依赖，需断点续跑 | **管道模块**（本技能） | -- |
| 操作独立，无前后依赖，按需加载 | **渐进披露** | 用上游 `skill-creator`（clawhub.ai） |
| ≤3 步，SKILL.md <200 行 | **不拆** | 直接写 |

**不需要管道模块的信号**：操作之间无前后依赖、不需要断点续跑、SKILL.md 短且稳定。

## 边界

| 本技能负责 | 不负责（交给谁） |
|-----------|----------------|
| 模块边界、耦合/内聚、可维护性 | 创建流程 init->edit->package（上游 skill-creator） |
| 调度器写法、模块契约、断点设计 | 渐进披露拆分、YAML frontmatter（上游 skill-creator） |
| 反模式诊断 | 验证方法论、TDD、SDO（writing-skills） |

## 场景入口

| 你要做什么 | 加载 |
|-----------|------|
| 新建管道模块 | [templates/module.md] + [templates/scheduler.md] |
| 实现断点续跑 | [references/runtime.md] |
| 排查设计问题 / 拆分合并判断 | [references/anti-patterns.md] |
| 看完整改造示例 | [references/real-example.md] |
