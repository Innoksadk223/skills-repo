# 实例：论文写作 skill 的模块化改造

## 改造前（传统写法）

```
paper-writer/
└── SKILL.md   (800 行，包含了研究→大纲→写作→润色所有逻辑)
```

每次运行消耗 ~4000 token。卡在大纲生成时，前面研究结果全丢。

## 改造后（模块化）

```
paper-writer/
├── SKILL.md                    (70 行，调度器)
├── state/                      (.gitignore)
│   ├── M1_research.json
│   ├── M2_outline.json
│   └── M3_draft.md
├── references/
│   ├── M1_research.md          (120 行)
│   ├── M2_outline.md           (80 行)
│   ├── M3_draft.md             (200 行)
│   └── M4_polish.md            (150 行)
└── templates/
    └── latex_base.tex
```

### SKILL.md（调度器）

```markdown
# 论文写作

## 调度流程

1. **M1** 文献研究 → `state/M1_research.json`
2. **M2** 大纲生成 → `state/M2_outline.json`
3. **M3** 正文撰写 → `state/M3_draft.md`
4. **M4** 润色排版 → `state/M4_final.tex`

## 决策
- M2 的大纲超过 5 节 → 对每节并行跑 M3 子模块
- 用户指定"只改第三章" → 从 M3_ch3 开始，跳过 M1、M2

## 模块清单
| 模块 | 文件 | 输入 | 输出 |
|------|------|------|------|
| M1 | [M1_research.md] | 用户主题 | state/M1_research.json |
| M2 | [M2_outline.md] | M1 | state/M2_outline.json |
| M3 | [M3_draft.md] | M2 | state/M3_draft.md |
| M4 | [M4_polish.md] | M3 | state/M4_final.tex |
```

### M1_research.md

```markdown
## 状态检查
检查 state/M1_research.json → 存在则跳过

## 输入
| 字段 | 来源 |
|------|------|
| topic | 用户输入 |

## 执行
1. 解析 topic，提取 3-5 个关键词
2. 用 academic-search 搜索每个关键词
3. 筛选近 3 年、引用 > 10 的论文（上限 20 篇）
4. 对每篇提取：标题、摘要、方法、结论
5. 按主题聚类，生成研究现状摘要

## 输出
state/M1_research.json:
{
  "keywords": [...],
  "papers": [{title, abstract, method, conclusion}],
  "clusters": [{theme, papers: [...]}],
  "summary": "string"
}

## 回滚
失败时删除 state/M1_research.json
```

## 实际效果对比

| 场景 | 传统写法 | 模块化 |
|------|---------|--------|
| 首次完整运行 | ~4000 token | ~3000 token（SKILL.md + M1~M4） |
| 只改第三章 | ~4000 token（全读） | ~600 token（SKILL.md + M3） |
| 大纲阶段失败 | 重来 | 重跑 M2 即可（M1 已存） |
| 半年后更新润色规则 | Agent 重读 800 行 | 只读 M4（150 行） |

**token 节省：改单模块时省 85%，断点续跑时省 60-80%。**
