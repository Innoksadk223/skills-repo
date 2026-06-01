#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_FLAT="$REPO_DIR/skills"

echo "╔══════════════════════════════╗"
echo "║  Inno's Skills Pack 安装器   ║"
echo "╚══════════════════════════════╝"
echo ""

# ── Hermes 分类映射（直接从 skills/ 构建，不依赖 skills-hermes/ symlink） ──
# 格式: "分类目录:技能1,技能2,..."
HERMES_MAP=(
    "browser-use:browser-use,remote-browser,cloud,x402"
    "paperspine:paper-spine,paper-spine-audit,paper-spine-build,paper-spine-citation,paper-spine-humanize,paper-spine-intake,paper-spine-latex,paper-spine-research,paper-spine-rewrite,paper-spine-translate,paper-spine-ui,paper-spine-update"
)
# 单技能分类 → 技能名即分类名
HERMES_SOLO="academic-search cleanup find-skills grill-me open-source skill-creator"

# ── 检测已安装的 agent ──
AGENTS=()
[ -d "$HOME/.claude" ] && AGENTS+=("claude:$HOME/.claude/skills")
[ -d "$HOME/.codex" ]  && AGENTS+=("codex:$HOME/.codex/skills")
[ -d "$HOME/.hermes" ] && AGENTS+=("hermes:$HOME/.hermes/skills")

if [ ${#AGENTS[@]} -eq 0 ]; then
    echo "未检测到任何 agent（Claude Code / Codex / Hermes）"
    echo "用法: bash setup.sh /path/to/skills"
    exit 0
fi

# ── 选择安装目标 ──
echo "检测到 ${#AGENTS[@]} 个 agent："
for i in "${!AGENTS[@]}"; do
    agent="${AGENTS[$i]%%:*}"
    dir="${AGENTS[$i]#*:}"
    echo "  $((i+1))) $agent  →  $dir"
done
echo "  a) 全部安装"
echo "  0) 自定义路径"
echo ""
read -p "选择: " choice

TARGETS=()
case "$choice" in
    a)
        TARGETS=("${AGENTS[@]}")
        ;;
    0)
        read -p "输入目标 skills 目录: " custom_dir
        read -p "agent 类型 (hermes/claude/codex): " custom_agent
        TARGETS=("$custom_agent:$custom_dir")
        ;;
    *)
        idx=$((choice - 1))
        TARGETS=("${AGENTS[$idx]}")
        ;;
esac

# ── 辅助函数 ──
link_skill() {
    local src="$1" dst="$2"
    if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
        return 1  # 已存在且正确 → 跳过
    fi
    rm -f "$dst"
    ln -s "$src" "$dst"
    return 0  # 新建
}

# ── 安装 ──
for target in "${TARGETS[@]}"; do
    agent="${target%%:*}"
    dir="${target#*:}"
    echo ""
    echo "── [$agent] → $dir ──"
    mkdir -p "$dir"
    new=0; skip=0

    case $agent in
        hermes)
            # 多技能分类
            for entry in "${HERMES_MAP[@]}"; do
                cat="${entry%%:*}"
                skills="${entry#*:}"
                mkdir -p "$dir/$cat"
                IFS=',' read -ra names <<< "$skills"
                for name in "${names[@]}"; do
                    src="$SKILLS_FLAT/$name"
                    [ -d "$src" ] || { echo "  ! $name 不在 repo 中，跳过"; continue; }
                    if link_skill "$src" "$dir/$cat/$name"; then
                        echo "  + $cat/$name"
                        new=$((new + 1))
                    else
                        skip=$((skip + 1))
                    fi
                done
            done
            # 单技能分类
            for name in $HERMES_SOLO; do
                src="$SKILLS_FLAT/$name"
                [ -d "$src" ] || { echo "  ! $name 不在 repo 中，跳过"; continue; }
                if link_skill "$src" "$dir/$name"; then
                    echo "  + $name"
                    new=$((new + 1))
                else
                    skip=$((skip + 1))
                fi
            done
            ;;
        claude|codex)
            for skill in "$SKILLS_FLAT"/*/; do
                [ ! -d "$skill" ] && continue
                name=$(basename "$skill")
                if link_skill "$skill" "$dir/$name"; then
                    echo "  + $name"
                    new=$((new + 1))
                else
                    skip=$((skip + 1))
                fi
            done
            ;;
        *)
            # 自定义路径：按 hermes 结构
            for entry in "${HERMES_MAP[@]}"; do
                cat="${entry%%:*}"; skills="${entry#*:}"
                mkdir -p "$dir/$cat"
                IFS=',' read -ra names <<< "$skills"
                for name in "${names[@]}"; do
                    src="$SKILLS_FLAT/$name"
                    [ -d "$src" ] || continue
                    link_skill "$src" "$dir/$cat/$name" && echo "  + $cat/$name" && new=$((new+1)) || skip=$((skip+1))
                done
            done
            for name in $HERMES_SOLO; do
                src="$SKILLS_FLAT/$name"
                [ -d "$src" ] || continue
                link_skill "$src" "$dir/$name" && echo "  + $name" && new=$((new+1)) || skip=$((skip+1))
            done
            ;;
    esac
    echo "  → 新增 $new，跳过 $skip"
done

echo ""
echo "✓ 完成。更新: cd $REPO_DIR && git pull && bash setup.sh"
