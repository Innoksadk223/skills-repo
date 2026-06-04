# Lint

Health-check the wiki for issues and research opportunities.

## Run the Script

```bash
python3 scripts/lint.py <wiki_path>
```

The script scans all wiki pages and raw files, outputs a JSON report. Parse the JSON and present findings to the user grouped by severity:

**broken_links > orphans > source_drift > contraditions > stale > frontmatter > quality > oversized > tag_issues > stub_upgrades > stub_cleanup**

## Report Format

Translate JSON findings into a human-readable report:

1. **断链** — wikilinks pointing to non-existent pages (list each broken target + which pages link to it)
2. **孤立页面** — pages with zero inbound links
3. **来源漂移** — raw/ files whose content changed (sha256 mismatch)
4. **矛盾页面** — pages marked `contested: true` or with `contradictions:` field
5. **陈旧内容** — pages not updated in >90 days
6. **Frontmatter 问题** — missing required fields, tags outside taxonomy
7. **质量信号** — `confidence: low` pages, single-source pages without confidence field
8. **超大页面** — pages over 200 lines (candidates for splitting)
9. **Tag 审计** — tags not in SCHEMA.md taxonomy
10. **Stub 升级候选** — stubs referenced by 2+ full pages
11. **Stub 清理** — stubs whose all referrers are archived

Append to log.md: `## [YYYY-MM-DD] lint | N issues found`

## Research Leads

After presenting findings, review the JSON for research opportunities. The Obsidian graph view already surfaces these signals visually — you are naming them explicitly:

- **Stub 升级**: for each `stub_upgrades` entry, suggest finding a source covering that concept. A stub with 3+ inbound links is a knowledge gap the user likely cares about.
- **矛盾页面**: for each page with `contested: true` or `contradictions:`, suggest finding a third-party source to break the tie.
- **孤立页面**: for each orphan, suggest which existing page(s) could naturally link to it — the content is there, just disconnected.
- **高频 tag 缺概念页**: scan all tags in use. If a tag appears on 5+ pages but has no dedicated concept page in `concepts/`, suggest creating one to synthesize the scattered references.
- **概念密集领域缺综述**: scan `concepts/` for clusters of 5+ pages sharing 2+ tags but with no corresponding page in `synthesis/`. Flag these as synthesis candidates.
- **单来源页面**: pages with only one source and `confidence: low` or missing confidence field — suggest finding corroborating sources.
