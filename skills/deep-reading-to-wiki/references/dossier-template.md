# Reading Dossier Template

Use this template for `reading_dossiers/<source-title>-深读档案.md`.

```markdown
---
title: <书名或文献名>深读档案
type: reading_dossier
source_raw:
  - wiki/raw/...
trigger: explicit_source # explicit_source / user_directed_expansion / retroactive_repair
user_intent: ""
source_discovery:
  - path: wiki/raw/...
    reason: ""
    key_terms: []
status: draft
target: karpathy-wiki
created: YYYY-MM-DD
updated: YYYY-MM-DD
compiled_to: []
confidence: medium
---

# <书名或文献名>深读档案

## 1. 阅读地图

### 全书/全文问题
- 这份材料主要试图回答什么问题：
- 它与当前 wiki 主题的关系：
- 它回应的用户补库意图或 wiki 缺口：
- 不应过度使用的地方：

### 来源发现记录
| 候选 raw | 命中原因 | 关键词 | 处理决定 |
|---|---|---|---|
| wiki/raw/... | 回应用户意图/补现有缺口 | 儿童教育/爱敬/... | 深读/略读/忽略 |

### 结构/问题地图
| 部分 | 脉络功能 | 解决什么问题 | 推进哪条主线 | 触及哪个 wiki 缺口 | 覆盖证据/层级 | 选/跳理由 |
|---|---|---|---|---|---|---|
| 导论/第一章 | 开题/定义/问题化 |  |  | 可能关联 [[...]] / 新缺口 | 标题/开头/结尾；L1/L2/L3/跳过 | 高相关/重复/低相关 |

### 高价值区域
| 区域 | 结构角色 | 为什么值得深挖 | 预计输出 |
|---|---|---|---|
| 章节/小节 | definition/premise/support/objection/limitation/bridge/conclusion | 能支撑/挑战哪个 wiki 节点 | claim/concept/comparison |

### 放弃清单
| 未深读区域 | 已覆盖层级 | 放弃原因 | 可能风险 | 重新触发条件 |
|---|---|---|---|---|
| 章节/小节 | L0/L1 | 低相关/重复/证据不足 | 可能漏掉反方 | 用户要求/后续检索命中 |

## 2. 候选节点池

### 候选 Concepts
| 概念 | 作者用法 | 边界/相邻概念 | raw 锚点 | 建议 |
|---|---|---|---|---|
|  |  |  | wiki/raw/... | 新建/更新/忽略 |

### 候选 Claims
| 命题 | 类型 | 支撑/反驳/限制什么 | raw 锚点 | 价值 |
|---|---|---|---|---|
|  | main/support/objection/limitation/bridge |  | wiki/raw/... | 高/中/低 |

### 候选 Comparisons / Debates
| 对比或争议 | 双方/多方 | 差异核心 | raw 锚点 | 建议 |
|---|---|---|---|---|
|  |  |  | wiki/raw/... |  |

### 候选 Entities
| 实体 | 类型 | 与本库关系 | raw 锚点 | 建议 |
|---|---|---|---|---|
| 作者/文本/学派 | person/text/org/tradition |  | wiki/raw/... |  |

## 3. 高价值点深挖

Repeat this block for each high-value candidate.

### HV-1: <候选点名称>

- 候选类型：claim / concept / comparison / entity
- 建议 wiki 目标：`wiki/claims/...` 或 `wiki/concepts/...`
- 来自结构地图：章节/小节 + 结构角色
- 分层路径：全书/全文 → 篇章/论证阶段 → 章节/小节 → 候选点
- 价值判断：为什么值得进入或更新 wiki

#### 上下文胶囊
- raw 锚点：`wiki/raw/...`
- 原文摘录：
  > 短摘录，保持逐字引用。
- 局部语境：这段前后在解决什么问题，推向什么结论。
- 全书位置：definition / premise / support / bridge / objection / limitation / conclusion / method note
- 压缩风险：如果写成一个 wiki 节点，最容易误读什么。
- 方法边界：normative / empirical / conceptual / interpretive / analogy / AI inference
- RAG 回查问题：
  - 问题 1
  - 问题 2

#### 与现有 wiki 的关系
- 可更新：
- 可新建：
- 可挑战：
- 可忽略重复：

## 4. wiki 交接清单

### 建议新建
| 目标路径 | 类型 | 来源候选 | 条目深度素材 | 互链/关系 | 必查 raw 锚点 | 入库条件 |
|---|---|---|---|---|---|---|
| wiki/claims/... | claim | HV-1 | 核心命题、边界、支撑/限制 | [[...]] / supports / challenges | `wiki/raw/...` | 复核锚点和上下文风险 |

### 建议更新
| 现有页面 | 深化方向 | 新增层次 | 来源候选 | 互链/关系 | 注意 |
|---|---|---|---|---|---|
| wiki/concepts/... | 补定义边界/反例/限制/关系 |  | HV-1 | [[...]] | 避免重复或过度泛化 |

### 必查 raw 锚点
| raw 锚点 | 支撑哪个 wiki 动作 | 必查原因 |
|---|---|---|
| `wiki/raw/...` | 新建/更新 `wiki/...` | 防止断章取义/保留限制条件/确认概念边界 |

### 暂不进入 wiki
| 内容 | 原因 | 后续条件 |
|---|---|---|
|  | 证据弱/重复/偏离主题/上下文不足 |  |

## 5. 反偷懒自检

- [ ] 已读取 wiki 入口文件或说明为何不可用。
- [ ] 如果由用户补库意图触发，已记录 user_intent 和 source_discovery。
- [ ] 已完成结构/问题地图，而不是直接挑选 AI 觉得有价值的段落。
- [ ] 主要部分已回答“解决什么问题 / 推进哪条主线 / 触及哪个 wiki 缺口”。
- [ ] 高价值候选都有分层路径，而不是从 raw 直接跳到 wiki claim。
- [ ] L1/L2/L3 的升级理由已记录，且没有把结构覆盖变成全书通读。
- [ ] 已列出高价值区域和放弃清单。
- [ ] 已生成候选 concepts / claims / comparisons / entities。
- [ ] 高价值候选都有 raw 锚点。
- [ ] 高价值候选都有上下文胶囊。
- [ ] 已说明压缩风险和可能误读。
- [ ] 已生成 RAG 回查问题。
- [ ] 已区分作者原意、raw 证据、AI 推论、wiki 迁移建议。
- [ ] 已标出不能直接进入 wiki 的弱候选。
- [ ] wiki 交接清单不仅列路径，还给出条目深度素材、互链关系、必查 raw 锚点和入库条件。

### 下一步

- 交给 `karpathy-wiki` 的重点：
- 需要 RAG 复核的问题：
- 需要用户判断的问题：
```
