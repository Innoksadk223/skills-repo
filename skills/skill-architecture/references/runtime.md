# 运行策略

## 首次运行

Agent 按 SKILL.md 的模块清单顺序执行：

```
加载 SKILL.md → 读模块清单 → 加载 M1.md →
检查 state/M1_* → 不存在 → 执行 M1 →
输出保存到 state/ → 加载 M2.md → ...
```

## 断点续跑

每个模块开始前检查 state/，存在则跳过：

```
加载 M1.md → state/M1_*.json 存在 → 跳过 M1（省 token）
加载 M2.md → state/M2_*.md 存在 → 跳过 M2
加载 M3.md → state/M3_* 不存在 → 执行 M3
→ 本次只跑了 M3，token 节省 > 60%
```

## 失败重试

```
M3 执行失败 → 读 M3.md 的「回滚」段 →
删除 state/M3_* → 重新执行 M3
```

M1、M2 的输出不受影响，不需要重跑。

## 增量修改

```
用户：「改第三章的引言」

Agent：看模块清单 → 引言在 M3_draft.md 的 state 里 →
直接加载 M3_draft.md 对应的 state 文件 → 改引言 →
只更新 state/M3_draft.md

跳过了 M1_research、M2_outline，token 节省 > 70%
```

## state/ 目录规范

```
state/
├── M1_research.json      ← JSON（结构化数据）
├── M2_outline.json       ← JSON
├── M3_draft.md           ← Markdown（长文本）
└── M4_final.tex          ← 模板文件
```

- 结构化数据（列表、配置、元数据）→ `.json`
- 长文本（草稿、正文、摘要）→ `.md`
- 模板文件（LaTeX、HTML）→ 保留原扩展名

## 加载策略（Agent 行为契约）

Agent 加载 skill-architecture 后，对于任何模块化 skill：

1. 先读完 SKILL.md（获取模块清单）
2. 按顺序检查每个模块的 state/ 文件
3. 只加载需要执行的模块的 `.md` 文件
4. **不要**一次性把所有 references/ 全读入上下文
