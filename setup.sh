#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_FLAT="$REPO_DIR/skills"

GROUP_KEYS=(browser paperspine minimax search academic productivity creative tools)
GROUP_DESC=(
    "[Browser] browser automation: browser-use, remote-browser, cloud, x402, open-source"
    "[PaperSpine] paper writing pipeline: research, rewrite, LaTeX, translate"
    "[Minimax] document generation: DOCX, PDF, XLSX, PPTX"
    "[Search] AnySearch real-time web/vertical search"
    "[Academic] academic search, paper review, wiki/RAG knowledge management"
    "[Productivity] MinerU document extraction"
    "[Creative] PPT agent"
    "[Tools] agent-loop, cleanup, skill tools, markitdown"
)

RECOMMENDED_SKILLS=(
    agent-loop
    anysearch
    cleanup
    find-skills
    skill-creator
    skill-architecture
    capture-gotcha
    markitdown
    academic-search
    academic-paper-review
)

HERMES_MAP=(
    "browser-use:browser-use,remote-browser,cloud,x402,open-source"
    "paperspine:paper-spine,paper-spine-audit,paper-spine-build,paper-spine-citation,paper-spine-humanize,paper-spine-intake,paper-spine-latex,paper-spine-research,paper-spine-rewrite,paper-spine-translate,paper-spine-ui,paper-spine-update"
    "minimax:minimax-docx,minimax-pdf,minimax-xlsx"
    "research:karpathy-wiki,SiliconFlow-rag,social-science-km"
    "productivity:mineru-document-extractor"
    "creative:ppt-agent-skill"
)
HERMES_SOLO="academic-search academic-paper-review anysearch agent-loop cleanup find-skills grill-me markitdown skill-creator skill-architecture capture-gotcha"

PRESET=""
TARGET_ARG=""
TARGET_DIR=""
GROUP_ARG=""
SKILL_ARG=""
YES=0
DRY_RUN=0
UPDATE_ONLY=0
LIST_ONLY=0
INTERACTIVE=1
INSTALL_NEW="y"
SELECT_ALL=0
SELECTED_GROUPS=()
SELECTED_SKILLS=()
TARGETS=()

print_banner() {
    echo "╔══════════════════════════════╗"
    echo "║  Inno's Skills Pack 安装器   ║"
    echo "╚══════════════════════════════╝"
    echo ""
}

show_help() {
    cat <<'EOF'
Inno's Skills Pack 安装器

小白模式：
  bash setup.sh
    进入菜单，默认推荐安装。适合第一次使用，不需要懂目录结构。

常用命令：
  bash setup.sh --preset recommended
    安装推荐核心技能，避免一次装太多。

  bash setup.sh --preset all
    安装仓库内全部技能。

  bash setup.sh --target codex --groups tools,search
    只给 Codex 安装指定分组。

  bash setup.sh --target codex --skills agent-loop,anysearch
    只安装指定技能。

  bash setup.sh --update-only
    只更新已经存在的技能，不新增技能。

  bash setup.sh --dry-run
    预览会新增/更新/跳过哪些技能，不真正写文件。

选项：
  --preset recommended|all    安装预设，默认 recommended
  --target codex|claude|hermes|all
                              安装目标，可用逗号多选
  --dir PATH                  自定义 skills 目录；需和单个 --target 搭配
  --groups LIST               分组列表，如 tools,search；也支持数字
  --skills LIST               技能名列表，如 agent-loop,anysearch
  --update-only               只更新已有技能
  --dry-run                   只预览，不写入
  --yes, -y                   自动确认
  --list                      列出分组和技能后退出
  --help, -h                  显示帮助

说明：
  - 不会删除不在本仓库里的技能。
  - 默认安装到 ~/.codex/skills、~/.claude/skills、~/.hermes/skills。
  - Hermes 会按用途分组；Codex/Claude 使用扁平目录。
EOF
}

die() {
    echo "错误: $*" >&2
    exit 1
}

contains_word() {
    local needle="$1"
    shift
    local item
    for item in "$@"; do
        [ "$item" = "$needle" ] && return 0
    done
    return 1
}

comma_to_words() {
    echo "$1" | tr ',' ' '
}

agent_default_dir() {
    case "$1" in
        claude) echo "$HOME/.claude/skills" ;;
        codex) echo "$HOME/.codex/skills" ;;
        hermes) echo "$HOME/.hermes/skills" ;;
        *) return 1 ;;
    esac
}

detect_agents() {
    TARGETS=()
    [ -d "$HOME/.claude" ] && TARGETS+=("claude|$HOME/.claude/skills")
    [ -d "$HOME/.codex" ] && TARGETS+=("codex|$HOME/.codex/skills")
    [ -d "$HOME/.hermes" ] && TARGETS+=("hermes|$HOME/.hermes/skills")
}

skill_group() {
    case "$1" in
        browser-use|remote-browser|cloud|x402|open-source) echo "browser" ;;
        paper-spine|paper-spine-*) echo "paperspine" ;;
        minimax-*|pptx) echo "minimax" ;;
        anysearch) echo "search" ;;
        karpathy-wiki|academic-search|academic-paper-review|SiliconFlow-rag|social-science-km) echo "academic" ;;
        mineru-document-extractor) echo "productivity" ;;
        ppt-agent-skill) echo "creative" ;;
        cleanup|find-skills|grill-me|markitdown|skill-creator|skill-architecture|agent-loop|capture-gotcha) echo "tools" ;;
        *) echo "" ;;
    esac
}

hermes_relative_path() {
    local name="$1"
    local entry cat skills skill
    for entry in "${HERMES_MAP[@]}"; do
        cat="${entry%%:*}"
        skills="${entry#*:}"
        for skill in $(comma_to_words "$skills"); do
            if [ "$skill" = "$name" ]; then
                echo "$cat/$name"
                return 0
            fi
        done
    done
    for skill in $HERMES_SOLO; do
        if [ "$skill" = "$name" ]; then
            echo "$name"
            return 0
        fi
    done
    echo "$name"
}

all_skill_names() {
    local skill
    for skill in "$SKILLS_FLAT"/*; do
        [ -d "$skill" ] || continue
        basename "$skill"
    done | sort
}

list_groups_and_skills() {
    local i name
    echo "分组："
    for i in "${!GROUP_KEYS[@]}"; do
        echo "  $((i + 1))) ${GROUP_KEYS[$i]} - ${GROUP_DESC[$i]}"
    done
    echo ""
    echo "技能："
    for name in $(all_skill_names); do
        echo "  - $name"
    done
}

resolve_group_token() {
    local token="$1"
    local idx
    [ "$token" = "a" ] && token="all"
    if [ "$token" = "all" ]; then
        SELECT_ALL=1
        return 0
    fi
    case "$token" in
        '' ) return 0 ;;
        *[!0-9]* )
            contains_word "$token" "${GROUP_KEYS[@]}" || die "未知分组: $token"
            SELECTED_GROUPS+=("$token")
            ;;
        * )
            idx=$((token - 1))
            [ "$idx" -ge 0 ] && [ "$idx" -lt "${#GROUP_KEYS[@]}" ] || die "未知分组编号: $token"
            SELECTED_GROUPS+=("${GROUP_KEYS[$idx]}")
            ;;
    esac
}

parse_groups() {
    local token
    SELECTED_GROUPS=()
    SELECT_ALL=0
    for token in $(comma_to_words "$1"); do
        resolve_group_token "$token"
    done
}

parse_skills() {
    local token
    SELECTED_SKILLS=()
    for token in $(comma_to_words "$1"); do
        [ -n "$token" ] && SELECTED_SKILLS+=("$token")
    done
}

selected_skill() {
    local name="$1"
    local group
    if [ "${#SELECTED_SKILLS[@]}" -gt 0 ]; then
        contains_word "$name" "${SELECTED_SKILLS[@]}"
        return $?
    fi
    [ "$SELECT_ALL" -eq 1 ] && return 0
    if [ "${#SELECTED_GROUPS[@]}" -eq 0 ]; then
        return 0
    fi
    group="$(skill_group "$name")"
    [ -n "$group" ] && contains_word "$group" "${SELECTED_GROUPS[@]}"
}

parse_args() {
    [ "$#" -gt 0 ] && INTERACTIVE=0
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --help|-h)
                show_help
                exit 0
                ;;
            --preset)
                [ "$#" -ge 2 ] || die "--preset 需要值"
                PRESET="$2"
                shift 2
                ;;
            --target)
                [ "$#" -ge 2 ] || die "--target 需要值"
                TARGET_ARG="$2"
                shift 2
                ;;
            --dir|--target-dir)
                [ "$#" -ge 2 ] || die "--dir 需要路径"
                TARGET_DIR="$2"
                shift 2
                ;;
            --groups)
                [ "$#" -ge 2 ] || die "--groups 需要值"
                GROUP_ARG="$2"
                shift 2
                ;;
            --skills)
                [ "$#" -ge 2 ] || die "--skills 需要值"
                SKILL_ARG="$2"
                shift 2
                ;;
            --update-only)
                UPDATE_ONLY=1
                shift
                ;;
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            --yes|-y)
                YES=1
                shift
                ;;
            --list)
                LIST_ONLY=1
                shift
                ;;
            --)
                shift
                break
                ;;
            -*)
                die "未知选项: $1"
                ;;
            *)
                [ -z "$TARGET_DIR" ] || die "只能提供一个自定义目录"
                TARGET_DIR="$1"
                shift
                ;;
        esac
    done
}

choose_targets_interactive() {
    local detected=("${TARGETS[@]}")
    local choice idx agent dir custom_agent custom_dir

    if [ "${#detected[@]}" -eq 0 ]; then
        echo "没有检测到 ~/.claude、~/.codex 或 ~/.hermes。"
        echo "你仍然可以输入一个 skills 目录手动安装。"
    else
        echo "检测到 ${#detected[@]} 个可安装目标："
        for idx in "${!detected[@]}"; do
            agent="${detected[$idx]%%|*}"
            dir="${detected[$idx]#*|}"
            echo "  $((idx + 1))) $agent  ->  $dir"
        done
        echo "  a) 全部安装（默认）"
    fi
    echo "  0) 自定义路径"
    echo ""
    read -p "选择安装目标: " choice
    [ -z "$choice" ] && choice="a"

    case "$choice" in
        a)
            [ "${#detected[@]}" -gt 0 ] || die "没有可自动安装的目标，请选择 0 自定义路径"
            TARGETS=("${detected[@]}")
            ;;
        0)
            read -p "agent 类型 (codex/claude/hermes): " custom_agent
            read -p "目标 skills 目录: " custom_dir
            [ -n "$custom_agent" ] || die "agent 类型不能为空"
            [ -n "$custom_dir" ] || die "目录不能为空"
            TARGETS=("$custom_agent|$custom_dir")
            ;;
        *[!0-9]*)
            die "无效选择: $choice"
            ;;
        *)
            idx=$((choice - 1))
            [ "$idx" -ge 0 ] && [ "$idx" -lt "${#detected[@]}" ] || die "无效选择: $choice"
            TARGETS=("${detected[$idx]}")
            ;;
    esac
}

choose_mode_interactive() {
    local choice group_choice skill_choice
    echo "请选择安装方式："
    echo "  1) 推荐安装（默认，小白模式：核心工具 + 搜索 + 文档转换）"
    echo "  2) 全部安装（适合想完整同步的人）"
    echo "  3) 自定义安装（自己选分组或技能）"
    echo "  4) 只更新已有技能（不新增）"
    echo "  5) 预览推荐安装（不写文件）"
    echo "  0) 退出"
    echo ""
    read -p "选择安装方式: " choice
    [ -z "$choice" ] && choice="1"

    case "$choice" in
        1) PRESET="recommended" ;;
        2) PRESET="all" ;;
        3)
            PRESET="custom"
            echo ""
            echo "可选分组："
            local i
            for i in "${!GROUP_KEYS[@]}"; do
                echo "  $((i + 1))) ${GROUP_KEYS[$i]} - ${GROUP_DESC[$i]}"
            done
            echo ""
            read -p "输入分组编号/名称（逗号或空格分隔，留空则改为按技能名选择）: " group_choice
            if [ -n "$group_choice" ]; then
                GROUP_ARG="$group_choice"
            else
                read -p "输入技能名（例如 agent-loop,anysearch）: " skill_choice
                [ -n "$skill_choice" ] || die "自定义安装至少要选择分组或技能"
                SKILL_ARG="$skill_choice"
            fi
            ;;
        4)
            PRESET="all"
            UPDATE_ONLY=1
            ;;
        5)
            PRESET="recommended"
            DRY_RUN=1
            ;;
        0)
            echo "已退出。"
            exit 0
            ;;
        *)
            die "无效选择: $choice"
            ;;
    esac
}

build_cli_targets() {
    local token agent dir count
    TARGETS=()
    if [ -z "$TARGET_ARG" ]; then
        detect_agents
        [ "${#TARGETS[@]}" -gt 0 ] || die "未检测到 agent。请用 --target codex --dir /path/to/skills 指定安装目录"
        return 0
    fi

    count=0
    for token in $(comma_to_words "$TARGET_ARG"); do
        count=$((count + 1))
    done
    [ -n "$TARGET_DIR" ] && [ "$count" -eq 1 ] || [ -z "$TARGET_DIR" ] || die "--dir 只能和单个 --target 搭配"

    for token in $(comma_to_words "$TARGET_ARG"); do
        if [ "$token" = "all" ] || [ "$token" = "a" ]; then
            [ -z "$TARGET_DIR" ] || die "--target all 不能搭配 --dir"
            detect_agents
            [ "${#TARGETS[@]}" -gt 0 ] || die "未检测到 agent，无法使用 --target all"
            return 0
        fi

        if echo "$token" | grep ':' >/dev/null 2>&1; then
            agent="${token%%:*}"
            dir="${token#*:}"
        else
            agent="$token"
            if [ -n "$TARGET_DIR" ]; then
                dir="$TARGET_DIR"
            else
                dir="$(agent_default_dir "$agent")" || die "未知 target: $agent"
            fi
        fi
        case "$agent" in
            codex|claude|hermes) ;;
            *) die "agent 类型必须是 codex、claude 或 hermes: $agent" ;;
        esac
        [ -n "$dir" ] || die "目标目录不能为空"
        TARGETS+=("$agent|$dir")
    done
}

configure_selection() {
    if [ -n "$SKILL_ARG" ]; then
        parse_skills "$SKILL_ARG"
        return 0
    fi

    if [ -n "$GROUP_ARG" ]; then
        parse_groups "$GROUP_ARG"
        return 0
    fi

    case "${PRESET:-recommended}" in
        recommended)
            SELECTED_SKILLS=("${RECOMMENDED_SKILLS[@]}")
            ;;
        all)
            SELECT_ALL=1
            ;;
        custom)
            die "自定义安装需要 --groups 或 --skills"
            ;;
        *)
            die "未知 preset: $PRESET"
            ;;
    esac
}

destination_for() {
    local agent="$1" base="$2" name="$3" rel
    if [ "$agent" = "hermes" ]; then
        rel="$(hermes_relative_path "$name")"
    else
        rel="$name"
    fi
    echo "$base/$rel"
}

relative_for() {
    local agent="$1" name="$2"
    if [ "$agent" = "hermes" ]; then
        hermes_relative_path "$name"
    else
        echo "$name"
    fi
}

action_for_skill() {
    local src="$1" dst="$2"
    if [ ! -f "$dst/SKILL.md" ]; then
        echo "new"
        return 0
    fi
    if diff -rq "$src" "$dst" >/dev/null 2>&1; then
        echo "same"
    else
        echo "update"
    fi
}

collect_new_skills() {
    local target agent dir name src dst action rel
    NEW_LINES=()
    for target in "${TARGETS[@]}"; do
        agent="${target%%|*}"
        dir="${target#*|}"
        for name in $(all_skill_names); do
            selected_skill "$name" || continue
            src="$SKILLS_FLAT/$name"
            dst="$(destination_for "$agent" "$dir" "$name")"
            action="$(action_for_skill "$src" "$dst")"
            if [ "$action" = "new" ]; then
                rel="$(relative_for "$agent" "$name")"
                NEW_LINES+=("[$agent] $rel")
            fi
        done
    done
}

confirm_new_skills() {
    local answer item
    if [ "$UPDATE_ONLY" -eq 1 ]; then
        INSTALL_NEW="n"
        return 0
    fi
    if [ "$DRY_RUN" -eq 1 ] || [ "$YES" -eq 1 ]; then
        INSTALL_NEW="y"
        return 0
    fi
    collect_new_skills
    [ "${#NEW_LINES[@]}" -eq 0 ] && { INSTALL_NEW="n"; return 0; }

    echo ""
    echo "将新增 ${#NEW_LINES[@]} 个技能："
    for item in "${NEW_LINES[@]}"; do
        echo "  + $item"
    done
    echo ""
    read -p "是否安装这些新技能？(y/n，默认 y): " answer
    INSTALL_NEW="${answer:-y}"
}

sync_skill() {
    local src="$1" dst="$2" action="$3"
    if [ "$DRY_RUN" -eq 1 ]; then
        return 0
    fi
    mkdir -p "$(dirname "$dst")"
    if [ "$action" = "new" ] || [ "$action" = "update" ]; then
        rm -rf "$dst"
        cp -R "$src" "$dst"
    fi
}

install_target() {
    local agent="$1" dir="$2"
    local name src dst rel action new upd skip
    new=0
    upd=0
    skip=0

    echo ""
    echo "-- [$agent] -> $dir --"
    [ "$UPDATE_ONLY" -eq 1 ] && echo "  模式: 只更新已有技能，不新增"
    [ "$DRY_RUN" -eq 1 ] && echo "  模式: 预览模式，不写文件"

    if [ "$DRY_RUN" -eq 0 ]; then
        mkdir -p "$dir"
    fi

    for name in $(all_skill_names); do
        selected_skill "$name" || continue
        src="$SKILLS_FLAT/$name"
        dst="$(destination_for "$agent" "$dir" "$name")"
        rel="$(relative_for "$agent" "$name")"
        action="$(action_for_skill "$src" "$dst")"

        if [ "$action" = "new" ] && { [ "$UPDATE_ONLY" -eq 1 ] || [ "$INSTALL_NEW" != "y" ]; }; then
            echo "  - $rel (新，已跳过)"
            skip=$((skip + 1))
            continue
        fi

        case "$action" in
            new)
                sync_skill "$src" "$dst" "$action"
                echo "  + $rel (新)"
                new=$((new + 1))
                ;;
            update)
                sync_skill "$src" "$dst" "$action"
                echo "  ↻ $rel (更新)"
                upd=$((upd + 1))
                ;;
            same)
                skip=$((skip + 1))
                ;;
        esac
    done

    if [ "$DRY_RUN" -eq 0 ]; then
        echo "$REPO_DIR" > "$dir/.skills-repo-path"
    fi

    echo "  -> 新增 ${new}，更新 ${upd}，跳过 ${skip}"
}

validate_selected_skills() {
    local name missing
    missing=0
    for name in "${SELECTED_SKILLS[@]}"; do
        if [ ! -f "$SKILLS_FLAT/$name/SKILL.md" ]; then
            echo "  ! 未找到技能: $name" >&2
            missing=1
        fi
    done
    [ "$missing" -eq 0 ] || die "存在未知技能，请先用 --list 查看可用名称"
}

main() {
    parse_args "$@"

    if [ "$LIST_ONLY" -eq 1 ]; then
        list_groups_and_skills
        exit 0
    fi

    print_banner

    if [ "$INTERACTIVE" -eq 1 ]; then
        detect_agents
        choose_mode_interactive
        choose_targets_interactive
    else
        build_cli_targets
    fi

    configure_selection
    validate_selected_skills

    if [ "$DRY_RUN" -eq 1 ]; then
        echo "预览模式：下面只展示计划，不会写入任何文件。"
    fi
    if [ "$UPDATE_ONLY" -eq 1 ]; then
        echo "只更新已有技能：新技能会显示为跳过。"
    fi

    confirm_new_skills

    local target agent dir
    for target in "${TARGETS[@]}"; do
        agent="${target%%|*}"
        dir="${target#*|}"
        install_target "$agent" "$dir"
    done

    echo ""
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "预览完成。确认无误后去掉 --dry-run 重新运行。"
    else
        echo "完成。更新命令: cd $REPO_DIR && git pull && bash setup.sh"
    fi
}

main "$@"
