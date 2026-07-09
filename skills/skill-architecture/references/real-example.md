# 实例：论文写作 skill 的模块化改造

## 改造前

```
paper-writer/
└── SKILL.md   (800 行，研究->大纲->写作->润色全挤在一起)
```

卡在大纲生成时，前面研究结果全丢。每次 ~4000 token。

## 改造后

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

### SKILL.md（调度器示例）

```markdown
## 调度流程
1. **M1** 文献研究 -> `state/M1_research.json`
2. **M2** 大纲生成 -> `state/M2_outline.json`
3. **M3** 正文撰写 -> `state/M3_draft.md`
4. **M4** 润色排版 -> `state/M4_final.tex`

## 决策
- 大纲超过 5 节 -> 每节并行跑 M3 子模块
- "只改第三章" -> 从 M3_ch3 开始，跳过 M1、M2
```

## 效果

改单模块省 ~85% token（只读 SKILL.md + 目标模块）。断点续跑省 60-80%（跳过已完成模块）。
