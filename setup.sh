#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_FLAT="$REPO_DIR/skills"
SKILLS_HERMES="$REPO_DIR/skills-hermes"

echo "Inno's Skills Pack — 安装脚本"
echo "=============================="
echo ""

# ── Claude Code ──
setup_claude() {
    local dir="$HOME/.claude/skills"
    if [ ! -d "$HOME/.claude" ]; then
        echo "[跳过] Claude Code 未安装"
        return
    fi
    mkdir -p "$dir"
    echo "[Claude Code] 安装到 $dir"
    for skill in "$SKILLS_FLAT"/*/; do
        name=$(basename "$skill")
        rm -f "$dir/$name"
        ln -s "$skill" "$dir/$name"
    done
    echo "  → $(ls "$dir" | wc -l | tr -d ' ') 个技能已链接"
}

# ── Codex ──
setup_codex() {
    local dir="$HOME/.codex/skills"
    if [ ! -d "$HOME/.codex" ]; then
        echo "[跳过] Codex 未安装"
        return
    fi
    mkdir -p "$dir"
    echo "[Codex] 安装到 $dir"
    for skill in "$SKILLS_FLAT"/*/; do
        name=$(basename "$skill")
        rm -f "$dir/$name"
        ln -s "$skill" "$dir/$name"
    done
    echo "  → $(ls "$dir" | wc -l | tr -d ' ') 个技能已链接"
}

# ── Hermes ──
setup_hermes() {
    local dir="$HOME/.hermes/skills"
    if [ ! -d "$HOME/.hermes" ]; then
        echo "[跳过] Hermes 未安装"
        return
    fi
    mkdir -p "$dir"
    echo "[Hermes] 安装到 $dir"
    local count=0
    for item in "$SKILLS_HERMES"/*; do
        name=$(basename "$item")
        if [ -d "$item" ] && [ ! -L "$item" ]; then
            # 多技能分类目录
            mkdir -p "$dir/$name"
            for sub in "$item"/*; do
                subname=$(basename "$sub")
                rm -f "$dir/$name/$subname"
                ln -s "$(realpath "$sub")" "$dir/$name/$subname"
                count=$((count + 1))
            done
        elif [ -L "$item" ]; then
            # 单技能分类 symlink → 解析到 skills/ 下的实际目录
            rm -f "$dir/$name"
            ln -s "$(realpath "$item")" "$dir/$name"
            count=$((count + 1))
        fi
    done
    echo "  → $count 个技能已链接"
}

setup_claude
echo ""
setup_codex
echo ""
setup_hermes

echo ""
echo "✓ 安装完成。git pull 即可更新。"
