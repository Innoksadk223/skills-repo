#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_FLAT="$REPO_DIR/skills"
SKILLS_HERMES="$REPO_DIR/skills-hermes"

echo "╔══════════════════════════════╗"
echo "║  Inno's Skills Pack 安装器   ║"
echo "╚══════════════════════════════╝"
echo ""

# ── 检测 agent ──
AGENTS=()
[ -d "$HOME/.claude" ] && AGENTS+=("claude")
[ -d "$HOME/.codex" ] && AGENTS+=("codex")
[ -d "$HOME/.hermes" ] && AGENTS+=("hermes")

if [ ${#AGENTS[@]} -eq 0 ]; then
    echo "未检测到任何已安装的 agent（Claude Code / Codex / Hermes）"
    echo "你可以手动指定安装目录："
    echo "  bash setup.sh /path/to/agent/skills"
    exit 0
fi

echo "检测到: ${AGENTS[*]}"
echo ""

# ── 选择安装目标 ──
if [ -n "$1" ]; then
    # 直接指定了路径
    TARGET_DIR="$1"
    echo "安装到: $TARGET_DIR"
else
    echo "选择安装目标："
    for i in "${!AGENTS[@]}"; do
        agent="${AGENTS[$i]}"
        case $agent in
            claude)   dir="$HOME/.claude/skills" ;;
            codex)    dir="$HOME/.codex/skills" ;;
            hermes)   dir="$HOME/.hermes/skills" ;;
        esac
        echo "  $((i+1))) $agent  →  $dir"
    done
    echo "  0) 自定义路径"
    read -p "输入序号: " choice

    if [ "$choice" = "0" ]; then
        read -p "输入目标 skills 目录: " TARGET_DIR
        case "$TARGET_DIR" in
            *hermes*) AGENT="hermes" ;;
            *claude*) AGENT="claude" ;;
            *codex*)  AGENT="codex" ;;
            *)        AGENT="hermes" ;;  # 默认按 hermes 结构
        esac
    else
        idx=$((choice - 1))
        agent="${AGENTS[$idx]}"
        case $agent in
            claude) TARGET_DIR="$HOME/.claude/skills"; AGENT="claude" ;;
            codex)  TARGET_DIR="$HOME/.codex/skills"; AGENT="codex" ;;
            hermes) TARGET_DIR="$HOME/.hermes/skills"; AGENT="hermes" ;;
        esac
    fi
fi

mkdir -p "$TARGET_DIR"

# ── 辅助函数 ──
link_skill() {
    local src="$1"
    local dst="$2"
    if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
        return 1  # 已存在且正确 → 跳过
    fi
    rm -f "$dst"
    ln -s "$src" "$dst"
    return 0  # 新建
}

# ── 安装 ──
echo ""
new=0
skip=0

if [ "$AGENT" = "hermes" ]; then
    echo "[Hermes] → $TARGET_DIR"
    for item in "$SKILLS_HERMES"/*; do
        [ ! -e "$item" ] && continue
        name=$(basename "$item")
        if [ -d "$item" ] && [ ! -L "$item" ]; then
            # 多技能分类目录
            mkdir -p "$TARGET_DIR/$name"
            for sub in "$item"/*; do
                subname=$(basename "$sub")
                src="$(realpath "$sub")"
                if link_skill "$src" "$TARGET_DIR/$name/$subname"; then
                    echo "  + $name/$subname"
                    new=$((new + 1))
                else
                    skip=$((skip + 1))
                fi
            done
        elif [ -L "$item" ]; then
            # 单技能分类 symlink
            src="$(realpath "$item")"
            if link_skill "$src" "$TARGET_DIR/$name"; then
                echo "  + $name"
                new=$((new + 1))
            else
                skip=$((skip + 1))
            fi
        fi
    done
else
    echo "[$AGENT] → $TARGET_DIR"
    for skill in "$SKILLS_FLAT"/*/; do
        [ ! -d "$skill" ] && continue
        name=$(basename "$skill")
        src="$(realpath "$skill")"
        if link_skill "$src" "$TARGET_DIR/$name"; then
            echo "  + $name"
            new=$((new + 1))
        else
            skip=$((skip + 1))
        fi
    done
fi

echo ""
echo "✓ 新增 $new 个，跳过 $skip 个（已存在）"
echo "下次更新: cd $REPO_DIR && git pull"
