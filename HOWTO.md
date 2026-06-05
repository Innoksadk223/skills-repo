# 技能调用指南 — Claude Code / Codex / Hermes

技能装好不是摆设，告诉 AI 你要干啥，它会自动挑对技能。不同 agent 调用方式略有不同。

## Claude Code & Codex

### 自动触发

根据技能描述自动匹配。你说人话就行：

```
🌐 浏览器
「帮我去淘宝搜键盘」           → browser-use
「打开这个网页截图」           → browser-use
「用浏览器自动填表」           → browser-use

📝 论文
「帮我写一篇论文」             → paper-spine
「审一下这篇论文」             → academic-paper-review / paper-spine-audit
「翻译这篇论文成英文」         → paper-spine-translate
「这个论文查重率太高了」       → paper-spine-humanize

📄 文档
「生成一份周报 Word」          → minimax-docx
「把这个数据做成表格」         → minimax-xlsx
「生成一个季度汇报 PPT」       → pptx-generator
「做一份漂亮的 PDF 报告」      → minimax-pdf

🔬 学术
「搜一下 diffusion model 论文」 → academic-search
「这篇论文能不能免费下载」     → academic-search
「把论文建个知识库」           → social-science-km / karpathy-wiki / SiliconFlow-rag

🛠 工具
「帮我清理项目临时文件」       → cleanup
「给我新装一个技能」           → skill-creator
「技能怎么设计比较好」         → skill-architecture
「我该用什么技能」             → find-skills
```

### 手动指定

如果一个场景可能触发多个技能，点名就行：

```
「用 browser-use 打开这个网页」
「用 paper-spine 帮我把这篇论文翻译成英文」
「加载 cleanup 清理一下」
```

### 查看已装技能

```
「我装了哪些技能？」
「list my skills」
```

---

## Hermes

### 自动触发

Hermes 在系统提示中列出所有可用技能，匹配到描述就自动加载。

```
「搜论文」    → academic-search
「打开网页」  → browser-use
「写 Word」   → minimax-docx
```

### 手动指定

Hermes 支持 `/skill-name` 格式：

```
/browser-use
/paper-spine
/academic-search
/cleanup
```

也可以直接说：

```
「加载 paper-spine 技能，我要写论文」
「use the minimax-pdf skill」
```

### 查看技能

```
「列出所有技能」
「show skills」
「我有什么技能可用？」
```

---

## 通用技巧

| 你想要的 | 怎么说 |
|----------|--------|
| 精准触发某个技能 | 「用 xxx 技能帮我…」 |
| 不确定有没有这个技能 | 「你能帮我做 XXX 吗？」 |
| 想看所有技能 | 「我装了哪些技能？」 |
| 技能不好用 | 「这个技能的结果不对，换个方式」 |
| 不知道怎么描述 | 直接说需求，AI 自己匹配 |

> **核心原则：你只管说你要什么，AI 负责选技能。选错了就说「不对，用 xxx 技能」。**
