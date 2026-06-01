# 技能调用指南 — Claude Code / Codex / Hermes

技能装好不是摆设，告诉 AI 你要干啥，它会自动挑对技能。不同 agent 调用方式略有不同。

## Claude Code

### 自动触发

Claude Code 根据技能 SKILL.md 的 `description` 字段自动匹配。你说人话就行：

```
「帮我去淘宝搜键盘」          → 自动加载 browser-use
「搜一下 diffusion model 论文」 → 自动加载 academic-search
「生成一份周报 Word」          → 自动加载 minimax-docx
```

### 手动指定

如果一个场景可能触发多个技能，可以点名：

```
「用 paper-spine 帮我把这篇论文翻译成英文」
「用 browser-use 打开这个网页」
```

### 查看已装技能

```
「我装了哪些技能？」
「list my skills」
```

---

## Codex

### 自动触发

和 Claude Code 一样，自然语言即可。Codex 会读取技能描述自动匹配。

```
「帮我清理项目临时文件」  → 自动加载 cleanup
「审一下这篇论文」        → 自动加载 academic-paper-review
```

### 手动指定

```
「use browser-use to open github.com」
「用 pptx-generator 生成一个季报 PPT」
```

---

## Hermes

### 自动触发

Hermes 在系统提示中列出了所有可用技能。匹配到描述就自动加载。

```
「搜论文」    → 自动加载 academic-search
「打开网页」  → 自动加载 browser-use
```

### 手动指定

Hermes 支持 `/skill-name` 格式：

```
/browser-use
/paperspine
/academic-search
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
