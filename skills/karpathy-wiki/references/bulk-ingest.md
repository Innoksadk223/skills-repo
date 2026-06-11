# Bulk Ingest

When ingesting multiple sources at once, batch the updates.

## Sequential workflow (fewer than 5 sources, or sources that reference each other)

1. Read all sources first
2. Identify all entities and concepts across all sources (one search pass, not N)
3. Check existing pages for all of them
4. Create/update pages in one pass (avoids redundant updates)
5. Update index.md once at the end
6. Write a single log entry covering the batch

## Parallel workflow (5+ independent sources — use agentloop/subagents)

When you have many sources that don't cross-reference each other heavily, parallelize the analysis phase to save time:

1. Copy all source files to `raw/` first (one batch command).
2. **Split sources into groups** of 2-4 files each. Each group gets a read-only `agentloop`/subagent task.
3. Each subagent reads assigned files and returns structured summary with entities, concepts, key quotes, and cross-references *within that group*.
4. **Collect all summaries** back in the parent session. Synthesize across groups — a person/idea may appear in files from different groups, and only the parent session can connect those dots.
5. **Create/update wiki pages in the parent session only.** The parent uses the combined intelligence to write entity, concept, and 辨析 pages with cross-group cross-references that no single subagent could produce.
6. Update `index.md` and `log.md` exclusively in the parent session.

> ⚠️ **Subagent file-mutation hazard (critical pitfall):** agentloop/subagent workers may share or fork from the same filesystem context. A subagent that writes to `index.md` or creates wiki pages can:
> - **Rename files** the parent is tracking (e.g. `log.md` → `log 2.md`)
> - **Overwrite** pages the parent or another subagent created
> - **Create orphans** — pages the subagent added to `index.md` but the parent doesn't know about
>
> **Rule: Subagents analyze and return structured data only. The parent creates pages and updates navigation.** If you must let subagents write pages (e.g. they hold the full context needed), always verify by re-reading `index.md` and `log.md` in the parent immediately after — never trust subagent claims of "index.md updated" without a confirmation read.
