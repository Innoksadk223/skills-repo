#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SETUP="$ROOT_DIR/setup.sh"

PASS_COUNT=0
TMP_DIRS=()
TMP_RESULT=""

cleanup() {
    for dir in "${TMP_DIRS[@]+"${TMP_DIRS[@]}"}"; do
        [ -n "$dir" ] && [ -d "$dir" ] && rm -rf "$dir"
    done
}
trap cleanup EXIT

make_tmp() {
    TMP_RESULT="$(mktemp -d "${TMPDIR:-/tmp}/setup-test.XXXXXX")"
    TMP_DIRS+=("$TMP_RESULT")
}

pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    printf 'ok %s - %s\n' "$PASS_COUNT" "$1"
}

fail() {
    printf 'not ok %s - %s\n' "$((PASS_COUNT + 1))" "$1" >&2
    exit 1
}

assert_contains() {
    local text="$1" needle="$2" label="$3"
    case "$text" in
        *"$needle"*) pass "$label" ;;
        *) fail "$label (missing: $needle)" ;;
    esac
}

assert_exists() {
    local path="$1" label="$2"
    [ -e "$path" ] && pass "$label" || fail "$label"
}

assert_not_exists() {
    local path="$1" label="$2"
    [ ! -e "$path" ] && pass "$label" || fail "$label"
}

assert_symlink() {
    local path="$1" label="$2"
    [ -L "$path" ] && pass "$label" || fail "$label"
}

assert_same_file() {
    local left="$1" right="$2" label="$3"
    cmp -s "$left" "$right" && pass "$label" || fail "$label"
}

test_help() {
    local out
    make_tmp
    out="$(HOME="$TMP_RESULT" bash "$SETUP" --help)"
    assert_contains "$out" "小白模式" "help explains beginner mode"
    assert_contains "$out" "--dry-run" "help lists dry-run"
    assert_contains "$out" "--skills" "help lists single-skill install"
}

test_dry_run_does_not_write() {
    local tmp target out
    make_tmp
    tmp="$TMP_RESULT"
    target="$tmp/codex-skills"
    out="$(HOME="$tmp/home" bash "$SETUP" --preset recommended --target codex --dir "$target" --dry-run --yes)"
    assert_contains "$out" "预览模式" "dry-run announces preview mode"
    assert_not_exists "$target/.skills-repo-path" "dry-run does not write install marker"
    assert_not_exists "$target/hermes-agent-loop" "dry-run does not copy skills"
    assert_not_exists "$tmp/home/.agents/skills/hermes-agent-loop" "dry-run does not write shared skill store"
}

test_single_skill_install() {
    local tmp target out
    make_tmp
    tmp="$TMP_RESULT"
    target="$tmp/codex-skills"
    out="$(HOME="$tmp/home" bash "$SETUP" --target codex --dir "$target" --skills hermes-agent-loop --yes)"
    assert_contains "$out" "hermes-agent-loop" "single-skill output mentions selected skill"
    assert_contains "$out" "新增 1，更新 0" "single-skill summary shows correct counts"
    assert_exists "$tmp/home/.agents/skills/hermes-agent-loop/SKILL.md" "single-skill install copies requested skill to shared store"
    assert_symlink "$target/hermes-agent-loop" "single-skill install links agent skill to shared store"
    assert_exists "$target/hermes-agent-loop/SKILL.md" "single-skill install exposes requested skill through link"
    assert_same_file "$ROOT_DIR/skills/hermes-agent-loop/SKILL.md" "$target/hermes-agent-loop/SKILL.md" "agent skill content matches repository"
    assert_not_exists "$target/capture-gotcha/SKILL.md" "single-skill install skips unrequested skill"
}

test_update_only_skips_new_skills() {
    local tmp target out
    make_tmp
    tmp="$TMP_RESULT"
    target="$tmp/codex-skills"
    out="$(HOME="$tmp/home" bash "$SETUP" --target codex --dir "$target" --skills hermes-agent-loop --update-only --yes)"
    assert_contains "$out" "只更新已有技能" "update-only announces update mode"
    assert_contains "$out" "新增 0，更新 0，跳过 1" "update-only summary shows skipped new skill"
    assert_not_exists "$target/hermes-agent-loop/SKILL.md" "update-only does not add new skill"
}

test_update_only_refreshes_existing_skill() {
    local tmp target out
    make_tmp
    tmp="$TMP_RESULT"
    target="$tmp/codex-skills"
    mkdir -p "$target/hermes-agent-loop"
    printf 'stale local skill\n' > "$target/hermes-agent-loop/SKILL.md"

    out="$(HOME="$tmp/home" bash "$SETUP" --target codex --dir "$target" --skills hermes-agent-loop --update-only --yes)"
    assert_contains "$out" "新增 0，更新 1" "update-only refreshes an existing local skill"
    assert_exists "$tmp/home/.agents/skills/hermes-agent-loop/SKILL.md" "update-only writes refreshed skill to shared store"
    assert_symlink "$target/hermes-agent-loop" "update-only migrates existing copied skill to shared link"
    assert_same_file "$ROOT_DIR/skills/hermes-agent-loop/SKILL.md" "$target/hermes-agent-loop/SKILL.md" "updated local skill matches repository"
}

test_recommended_preset_is_small() {
    local tmp target
    make_tmp
    tmp="$TMP_RESULT"
    target="$tmp/codex-skills"
    HOME="$tmp/home" bash "$SETUP" --preset recommended --target codex --dir "$target" --yes >/dev/null
    assert_exists "$target/hermes-agent-loop/SKILL.md" "recommended preset includes hermes-agent-loop"
    assert_exists "$target/cleanup/SKILL.md" "recommended preset includes cleanup"
    assert_exists "$target/skill-planner/SKILL.md" "recommended preset includes skill-planner"
    assert_not_exists "$target/cc-agent-loop/SKILL.md" "recommended preset does not install non-recommended skills"
}

test_help
test_dry_run_does_not_write
test_single_skill_install
test_update_only_skips_new_skills
test_update_only_refreshes_existing_skill
test_recommended_preset_is_small

printf '# %s assertions passed\n' "$PASS_COUNT"
