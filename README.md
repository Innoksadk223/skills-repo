# Inno's Skills Pack

个人 AI Coding Agent 技能包，支持 **Claude Code**、**Codex**、**Hermes** 三个 agent。

## 技能清单（25 个）

| 分类 | 技能 |
|------|------|
| Browser | browser-use, remote-browser, cloud, x402 |
| PaperSpine | paper-spine, paper-spine-audit/build/citation/humanize/intake/latex/research/rewrite/translate/ui/update |
| Creative | ui-ux-pro-max |
| Research | academic-search |
| Dev | cleanup, find-skills, frontend-design, frontend-dev, grill-me, open-source, skill-creator |

## 目录结构

```
skills-repo/
├── skills/              ← 扁平结构（Claude Code / Codex 用）
│   ├── browser-use/SKILL.md
│   ├── cleanup/SKILL.md
│   └── ...
│
├── skills-hermes/       ← 分类结构（Hermes 用，symlink 指向 skills/）
│   ├── browser-use/     ← 4 个技能聚合
│   ├── paperspine/      ← 12 个技能聚合
│   ├── creative/        ← 按功能域归类
│   ├── cleanup → ../skills/cleanup
│   └── ...
│
└── setup.sh             ← 一键安装脚本
```

## 快速安装

```bash
# 1. 克隆
git clone https://github.com/innominate/skills-repo.git ~/inno-skills
cd ~/inno-skills

# 2. 一键安装（自动检测你装了哪些 agent）
bash setup.sh
```

## 手动安装

### Claude Code

```bash
for skill in ~/inno-skills/skills/*/; do
    name=$(basename "$skill")
    ln -sf "$(realpath "$skill")" ~/.claude/skills/"$name"
done
```

### Codex

```bash
for skill in ~/inno-skills/skills/*/; do
    name=$(basename "$skill")
    ln -sf "$(realpath "$skill")" ~/.codex/skills/"$name"
done
```

### Hermes

```bash
cd ~/inno-skills/skills-hermes
for item in *; do
    if [ -d "$item" ] && [ ! -L "$item" ]; then
        # 多技能分类：browser-use, paperspine, creative
        mkdir -p ~/.hermes/skills/"$item"
        for sub in "$item"/*; do
            subname=$(basename "$sub")
            ln -sf "$(realpath "$sub")" ~/.hermes/skills/"$item"/"$subname"
        done
    else
        # 单技能分类：symlink 直接指向 skills/ 下的实际目录
        ln -sf "$(realpath "$item")" ~/.hermes/skills/"$item"
    fi
done
```

## 更新

```bash
cd ~/inno-skills
git pull
```
