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
    "browser-use:browser-use,remote-browser,cloud,x402,open-source"
    "paperspine:paper-spine,paper-spine-audit,paper-spine-build,paper-spine-citation,paper-spine-humanize,paper-spine-intake,paper-spine-latex,paper-spine-research,paper-spine-rewrite,paper-spine-translate,paper-spine-ui,paper-spine-update"
    "minimax:minimax-docx,minimax-pdf,minimax-xlsx,pptx-generator"
    "research:llm-wiki,SiliconFlow-rag,social-science-km"
)
# 单技能分类 → 技能名即分类名
HERMES_SOLO="academic-search academic-paper-review cleanup find-skills grill-me markitdown skill-creator"

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

# ── 选择分组 ──
GROUP_KEYS=(browser paperspine minimax academic tools)
GROUP_DESC=(
    "[Browser] browser automation: browser-use, remote-browser, cloud, x402, open-source (5)"
    "[PaperSpine] paper writing pipeline: research, rewrite, LaTeX, translate, etc. (12)"
    "[Minimax] document generation: DOCX, PDF, XLSX, PPTX (4)"
    "[Academic] llm-wiki, academic search, paper review, social-science RAG, knowledge management (5)"
    "[Tools] skill-creator, cleanup, find-skills, grill-me, markitdown (5)"
)

echo ""
echo "Select groups (space-separated, a=all, Enter=all):"
for i in "${!GROUP_KEYS[@]}"; do
    echo "  $((i+1))) ${GROUP_DESC[$i]}"
done
echo "  a) All (default)"
echo ""
read -p "Choice: " group_choice

SELECTED_GROUPS=()
if [ -z "$group_choice" ] || [ "$group_choice" = "a" ]; then
    SELECTED_GROUPS=("${GROUP_KEYS[@]}")
else
    for g in $group_choice; do
        idx=$((g - 1))
        [ -n "${GROUP_KEYS[$idx]}" ] && SELECTED_GROUPS+=("${GROUP_KEYS[$idx]}")
    done
fi

# ── 辅助函数 ──
# 判断技能属于哪个分组
skill_group() {
    case "$1" in
        browser-use|remote-browser|cloud|x402|open-source) echo "browser" ;;
        paper-spine|paper-spine-*)                         echo "paperspine" ;;
        minimax-*|pptx-generator)                          echo "minimax" ;;
        llm-wiki|academic-search|academic-paper-review|SiliconFlow-rag|social-science-km) echo "academic" ;;
        cleanup|find-skills|grill-me|markitdown|skill-creator) echo "tools" ;;
        *)                                                 echo "" ;;
    esac
}

# 检查分组是否被选中
selected() {
    local g=$(skill_group "$1")
    [ -z "$g" ] && return 0  # 未归类默认安装
    for sg in "${SELECTED_GROUPS[@]}"; do
        [ "$sg" = "$g" ] && return 0
    done
    return 1
}
copy_skill() {
    local src="$1" dst="$2"
    if [ -f "$dst/SKILL.md" ]; then
        return 1  # 已存在 → 跳过（如需覆盖，先 rm -rf）
    fi
    rm -rf "$dst"
    cp -R "$src" "$dst"
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
                    selected "$name" || continue
                    src="$SKILLS_FLAT/$name"
                    [ -d "$src" ] || { echo "  ! $name 不在 repo 中，跳过"; continue; }
                    if copy_skill "$src" "$dir/$cat/$name"; then
                        echo "  + $cat/$name"
                        new=$((new + 1))
                    else
                        skip=$((skip + 1))
                    fi
                done
            done
            # 单技能分类
            for name in $HERMES_SOLO; do
                selected "$name" || continue
                src="$SKILLS_FLAT/$name"
                [ -d "$src" ] || { echo "  ! $name 不在 repo 中，跳过"; continue; }
                if copy_skill "$src" "$dir/$name"; then
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
                selected "$name" || continue
                if copy_skill "$skill" "$dir/$name"; then
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
                    selected "$name" || continue
                    src="$SKILLS_FLAT/$name"
                    [ -d "$src" ] || continue
                    copy_skill "$src" "$dir/$cat/$name" && echo "  + $cat/$name" && new=$((new+1)) || skip=$((skip+1))
                done
            done
            for name in $HERMES_SOLO; do
                selected "$name" || continue
                src="$SKILLS_FLAT/$name"
                [ -d "$src" ] || continue
                copy_skill "$src" "$dir/$name" && echo "  + $name" && new=$((new+1)) || skip=$((skip+1))
            done
            ;;
    esac
    echo "  → 新增 $new，跳过 $skip"
done

echo ""
echo "✓ 完成。萌新指南: cat GUIDE.md"
echo "更新: cd $REPO_DIR && git pull && bash setup.sh"
