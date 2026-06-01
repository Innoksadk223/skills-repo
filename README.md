# Inno's Skills Pack

个人 AI Coding Agent 技能包，支持 **Claude Code**、**Codex**、**Hermes**。

## 技能清单（22 个）

| 分类 | 技能 |
|------|------|
| Browser | browser-use, remote-browser, cloud, x402 |
| PaperSpine | paper-spine + 11 个子模块 |
| Research | academic-search |
| Dev | cleanup, find-skills, grill-me, open-source, skill-creator |

## 快速安装

```bash
git clone https://github.com/Innoksadk223/skills-repo.git ~/inno-skills
cd ~/inno-skills
bash setup.sh
```

`setup.sh` 会：
- 自动检测你装了哪个 agent
- 让你选择安装目标
- 已有技能自动跳过，只装新增的
- 以后 `git pull` 即可同步增删

## 目录结构

```
skills-repo/
├── skills/              ← 扁平结构（Claude Code / Codex）
│   ├── browser-use/SKILL.md
│   └── ...
│
├── skills-hermes/       ← 分类结构（Hermes，symlink → skills/）
│   ├── browser-use/     ← 聚合 4 个技能
│   ├── paperspine/      ← 聚合 12 个技能
│   ├── cleanup → ../skills/cleanup
│   └── ...
│
└── setup.sh
```

## 手动安装

### Claude Code / Codex

```bash
for skill in skills/*/; do
    name=$(basename "$skill")
    [ -L ~/.claude/skills/"$name" ] || ln -s "$(realpath "$skill")" ~/.claude/skills/"$name"
done
```

### Hermes

```bash
for item in skills-hermes/*; do
    name=$(basename "$item")
    if [ -d "$item" ] && [ ! -L "$item" ]; then
        mkdir -p ~/.hermes/skills/"$name"
        for sub in "$item"/*; do
            subname=$(basename "$sub")
            [ -L ~/.hermes/skills/"$name"/"$subname" ] || \
                ln -s "$(realpath "$sub")" ~/.hermes/skills/"$name"/"$subname"
        done
    else
        [ -L ~/.hermes/skills/"$name" ] || \
            ln -s "$(realpath "$item")" ~/.hermes/skills/"$name"
    fi
done
```
