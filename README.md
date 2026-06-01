# Inno's Skills Pack

个人 AI Coding Agent 技能包，支持 **Claude Code**、**Codex**、**Hermes**。

## 技能清单（22 个）

| 分类 | 技能 |
|------|------|
| Browser | browser-use, remote-browser, cloud, x402, open-source |
| PaperSpine | paper-spine + 11 个子模块 |
| Research | academic-search |
| Dev | cleanup, find-skills, grill-me, skill-creator |

## 快速安装

```bash
git clone https://github.com/Innoksadk223/skills-repo.git ~/inno-skills
cd ~/inno-skills
bash setup.sh
```

`setup.sh` 会：
- 自动检测你装了哪些 agent（支持多选 / 全选）
- Hermes 直接从 skills/ 构建分类目录（不依赖中间 symlink）
- 已有技能自动跳过，只装新增的
- 以后 `git pull && bash setup.sh` 即可同步增删

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
# 多技能分类（直接从 skills/ 构建）
mkdir -p ~/.hermes/skills/browser-use
for name in browser-use remote-browser cloud x402 open-source; do
    [ -L ~/.hermes/skills/browser-use/"$name" ] || \
        ln -s "$(pwd)/skills/$name" ~/.hermes/skills/browser-use/"$name"
done

mkdir -p ~/.hermes/skills/paperspine
for name in paper-spine paper-spine-audit paper-spine-build paper-spine-citation \
            paper-spine-humanize paper-spine-intake paper-spine-latex \
            paper-spine-research paper-spine-rewrite paper-spine-translate \
            paper-spine-ui paper-spine-update; do
    [ -L ~/.hermes/skills/paperspine/"$name" ] || \
        ln -s "$(pwd)/skills/$name" ~/.hermes/skills/paperspine/"$name"
done

# 单技能分类
for name in academic-search cleanup find-skills grill-me skill-creator; do
    [ -L ~/.hermes/skills/"$name" ] || \
        ln -s "$(pwd)/skills/$name" ~/.hermes/skills/"$name"
done
```
