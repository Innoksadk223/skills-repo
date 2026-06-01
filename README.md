# Inno's Skills Pack

个人 AI Coding Agent 技能包，支持 **Claude Code**、**Codex**、**Hermes**。

> **Claude Code 用户建议优先从官方源安装**（`npx skills add -g <name>`），版本更新更及时。
> 此包主要用于：Hermes / Codex 安装、团队统一技能集、离线环境。

## 技能清单（23 个）

| 分类 | 技能 | 来源 |
|------|------|------|
| Browser | browser-use, remote-browser, cloud, x402, open-source | [browser-use/browser-use](https://github.com/browser-use/browser-use) |
| PaperSpine | paper-spine + 11 个子模块 | [WUBING2023/PaperSpine](https://github.com/WUBING2023/PaperSpine) |
| Research | academic-search, academic-paper-review | [ustc-ai4science/academic-search](https://github.com/ustc-ai4science/academic-search) · [bytedance/deer-flow](https://github.com/bytedance/deer-flow/tree/main/skills/public/academic-paper-review) |
| Tools | skill-creator | [clawhub.ai](https://clawhub.ai) |
| — | cleanup, find-skills, grill-me | — |

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

### Claude Code 推荐方式

```bash
# browser-use 系列
npx skills add -g browser-use

# academic-search
npx skills add -g academic-search

# paper-spine（需手动从 GitHub 安装）
git clone https://github.com/WUBING2023/PaperSpine.git /tmp/paperspine
# 然后将需要的子模块 symlink 到 ~/.claude/skills/
```

## 目录结构

```
skills-repo/
├── skills/              ← 扁平结构（Claude Code / Codex）
├── skills-hermes/       ← 分类结构（Hermes，symlink → skills/）
│   ├── browser-use/     ← 5 个技能
│   ├── paperspine/      ← 12 个技能
│   ├── academic-search → ../skills/academic-search
│   └── ...
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
for name in academic-search academic-paper-review cleanup find-skills grill-me skill-creator; do
    [ -L ~/.hermes/skills/"$name" ] || \
        ln -s "$(pwd)/skills/$name" ~/.hermes/skills/"$name"
done
```
