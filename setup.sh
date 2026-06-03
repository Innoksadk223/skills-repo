#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_FLAT="$REPO_DIR/skills"

echo "╔══════════════════════════════╗"
echo "║  Inno's Skills Pack 安装器   ║"
echo "╚══════════════════════════════╝"
echo ""

# ── Hermes 分类映射 ──
HERMES_MAP=(
    "browser-use:browser-use,remote-browser,cloud,x402,open-source"
    "paperspine:paper-spine,paper-spine-audit,paper-spine-build,paper-spine-citation,paper-spine-humanize,paper-spine-intake,paper-spine-latex,paper-spine-research,paper-spine-rewrite,paper-spine-translate,paper-spine-ui,paper-spine-update"
    "minimax:minimax-docx,minimax-pdf,minimax-xlsx,pptx-generator"
    "research:llm-wiki,SiliconFlow-rag,social-science-km"
)
HERMES_SOLO="academic-search academic-paper-review cleanup find-skills grill-me markitdown skill-creator skill-architecture"

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
    "[Tools] skill-creator, skill-architecture, cleanup, find-skills, grill-me, markitdown (6)"
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
skill_group() {
    case "$1" in
        browser-use|remote-browser|cloud|x402|open-source) echo "browser" ;;
        paper-spine|paper-spine-*)                         echo "paperspine" ;;
        minimax-*|pptx-generator)                          echo "minimax" ;;
        llm-wiki|academic-search|academic-paper-review|SiliconFlow-rag|social-science-km) echo "academic" ;;
        cleanup|find-skills|grill-me|markitdown|skill-creator|skill-architecture) echo "tools" ;;
        *)                                                 echo "" ;;
    esac
}

selected() {
    local g=$(skill_group "$1")
    [ -z "$g" ] && return 0
    for sg in "${SELECTED_GROUPS[@]}"; do
        [ "$sg" = "$g" ] && return 0
    done
    return 1
}

# 同步单个技能：比较 repo 和目标，决定新建/更新/跳过
# 返回: 0=新建  1=更新  2=一致(跳过)
sync_skill() {
    local src="$1" dst="$2"

    if [ ! -f "$dst/SKILL.md" ]; then
        # 目标不存在 → 新建
        rm -rf "$dst" 2>/dev/null
        cp -R "$src" "$dst"
        return 0
    fi

    # 已存在 → 比较内容是否一致
    if diff -rq "$src" "$dst" > /dev/null 2>&1; then
        return 2  # 完全一致
    fi

    # 不一致 → 更新
    rm -rf "$dst"
    cp -R "$src" "$dst"
    return 1
}

# ── Phase 1: 扫描新技能，询问用户 ──
declare -A NEW_SKILLS  # 待确认的新技能

scan_new_skills() {
    local agent="$1" dir="$2"
    case $agent in
        hermes)
            for entry in "${HERMES_MAP[@]}"; do
                cat="${entry%%:*}"; skills="${entry#*:}"
                IFS=',' read -ra names <<< "$skills"
                for name in "${names[@]}"; do
                    selected "$name" || continue
                    [ -d "$SKILLS_FLAT/$name" ] || continue
                    [ -f "$dir/$cat/$name/SKILL.md" ] && continue
                    NEW_SKILLS["$name"]="$cat/$name"
                done
            done
            for name in $HERMES_SOLO; do
                selected "$name" || continue
                [ -d "$SKILLS_FLAT/$name" ] || continue
                [ -f "$dir/$name/SKILL.md" ] && continue
                NEW_SKILLS["$name"]="$name"
            done
            ;;
        claude|codex)
            for skill in "$SKILLS_FLAT"/*/; do
                [ ! -d "$skill" ] && continue
                name=$(basename "$skill")
                selected "$name" || continue
                [ -f "$dir/$name/SKILL.md" ] && continue
                NEW_SKILLS["$name"]="$name"
            done
            ;;
    esac
}

# Phase 1: 收集所有 target 的新技能
ALL_NEW=()
for target in "${TARGETS[@]}"; do
    agent="${target%%:*}"; dir="${target#*:}"
    NEW_SKILLS=()
    scan_new_skills "$agent" "$dir"
    for name in "${!NEW_SKILLS[@]}"; do
        ALL_NEW+=("[$agent] ${NEW_SKILLS[$name]}")
    done
done

if [ ${#ALL_NEW[@]} -gt 0 ]; then
    echo ""
    echo "── 发现 ${#ALL_NEW[@]} 个新技能 ──"
    for item in "${ALL_NEW[@]}"; do
        echo "  · $item"
    done
    echo ""
    read -p "是否安装这些新技能？(y/n，默认 y): " install_new
    INSTALL_NEW="${install_new:-y}"
else
    INSTALL_NEW="n"
fi

# ── Phase 2: 执行安装/更新 ──
for target in "${TARGETS[@]}"; do
    agent="${target%%:*}"; dir="${target#*:}"
    echo ""
    echo "── [$agent] → $dir ──"
    mkdir -p "$dir"
    new=0; upd=0; skip=0

    case $agent in
        hermes)
            # 多技能分类
            for entry in "${HERMES_MAP[@]}"; do
                cat="${entry%%:*}"; skills="${entry#*:}"
                mkdir -p "$dir/$cat"
                IFS=',' read -ra names <<< "$skills"
                for name in "${names[@]}"; do
                    selected "$name" || continue
                    src="$SKILLS_FLAT/$name"
                    [ -d "$src" ] || { echo "  ! $name 不在 repo 中，跳过"; continue; }
                    dst="$dir/$cat/$name"
                    # 判断是否新技能
                    if [ ! -f "$dst/SKILL.md" ]; then
                        [ "$INSTALL_NEW" != "y" ] && { skip=$((skip+1)); continue; }
                    fi
                    sync_skill "$src" "$dst"
                    case $? in
                        0) echo "  + $cat/$name (新)"; new=$((new+1)) ;;
                        1) echo "  ↻ $cat/$name (更新)"; upd=$((upd+1)) ;;
                        2) skip=$((skip+1)) ;;
                    esac
                done
            done
            # 单技能分类
            for name in $HERMES_SOLO; do
                selected "$name" || continue
                src="$SKILLS_FLAT/$name"
                [ -d "$src" ] || { echo "  ! $name 不在 repo 中，跳过"; continue; }
                dst="$dir/$name"
                if [ ! -f "$dst/SKILL.md" ]; then
                    [ "$INSTALL_NEW" != "y" ] && { skip=$((skip+1)); continue; }
                fi
                sync_skill "$src" "$dst"
                case $? in
                    0) echo "  + $name (新)"; new=$((new+1)) ;;
                    1) echo "  ↻ $name (更新)"; upd=$((upd+1)) ;;
                    2) skip=$((skip+1)) ;;
                esac
            done
            ;;
        claude|codex)
            for skill in "$SKILLS_FLAT"/*/; do
                [ ! -d "$skill" ] && continue
                name=$(basename "$skill")
                selected "$name" || continue
                dst="$dir/$name"
                if [ ! -f "$dst/SKILL.md" ]; then
                    [ "$INSTALL_NEW" != "y" ] && { skip=$((skip+1)); continue; }
                fi
                sync_skill "$skill" "$dst"
                case $? in
                    0) echo "  + $name (新)"; new=$((new+1)) ;;
                    1) echo "  ↻ $name (更新)"; upd=$((upd+1)) ;;
                    2) skip=$((skip+1)) ;;
                esac
            done
            ;;
        *)
            for entry in "${HERMES_MAP[@]}"; do
                cat="${entry%%:*}"; skills="${entry#*:}"
                mkdir -p "$dir/$cat"
                IFS=',' read -ra names <<< "$skills"
                for name in "${names[@]}"; do
                    selected "$name" || continue
                    src="$SKILLS_FLAT/$name"
                    [ -d "$src" ] || continue
                    dst="$dir/$cat/$name"
                    if [ ! -f "$dst/SKILL.md" ]; then
                        [ "$INSTALL_NEW" != "y" ] && { skip=$((skip+1)); continue; }
                    fi
                    sync_skill "$src" "$dst"
                    case $? in
                        0) echo "  + $cat/$name (新)"; new=$((new+1)) ;;
                        1) echo "  ↻ $cat/$name (更新)"; upd=$((upd+1)) ;;
                        2) skip=$((skip+1)) ;;
                    esac
                done
            done
            for name in $HERMES_SOLO; do
                selected "$name" || continue
                src="$SKILLS_FLAT/$name"
                [ -d "$src" ] || continue
                dst="$dir/$name"
                if [ ! -f "$dst/SKILL.md" ]; then
                    [ "$INSTALL_NEW" != "y" ] && { skip=$((skip+1)); continue; }
                fi
                sync_skill "$src" "$dst"
                case $? in
                    0) echo "  + $name (新)"; new=$((new+1)) ;;
                    1) echo "  ↻ $name (更新)"; upd=$((upd+1)) ;;
                    2) skip=$((skip+1)) ;;
                esac
            done
            ;;
    esac
    echo "  → 新增 $new，更新 $upd，跳过 $skip"
done

echo ""
echo "✓ 完成。萌新指南: cat GUIDE.md"
echo "更新: cd $REPO_DIR && git pull && bash setup.sh"
