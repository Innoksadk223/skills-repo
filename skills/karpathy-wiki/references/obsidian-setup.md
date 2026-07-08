# Obsidian Integration

The wiki directory works as an Obsidian vault out of the box:

- `[[wikilinks]]` render as clickable links;
- Graph View visualizes the knowledge network;
- YAML frontmatter powers Dataview queries;
- `raw/assets/` holds images referenced via `![[image.png]]`.

## Setup

For best graph readability:

- Set Obsidian's attachment folder to `raw/assets/`.
- Enable Wikilinks in Obsidian settings.
- **Exclude `raw/` from graph view:** Settings → Files & Links → Excluded files → add `raw/`. Also in Graph view → Filter → Excluded folders → add `raw/`.
- Keep `raw/` evidence locations as plain-text paths, not wikilinks.

## Graph Path Groups

Obsidian Graph can group notes by folder path. Use path-based groups to visually separate page types:

| Page type | Graph group query | Meaning |
|---|---|---|
| Claims | `path:claims/` | 论证节点 |
| Concepts | `path:concepts/` | 概念节点 |
| Entities | `path:entities/` | 人物/组织/文本 |
| Comparisons | `path:comparisons/` | 辨析节点 |
| Debates | `path:debates/` | 社科争议谱系（可选） |
| Queries | `path:queries/` | 查询存档 |
| Synthesis | `path:synthesis/` | 轻量入口页 |

Graph should mainly show `claims/`, `concepts/`, `entities/`, and `comparisons/`. `synthesis/` should appear as entry hubs, not as giant content centers.

## Claim Graph Rules

Obsidian default graph sees body wikilinks, not semantic YAML arrays. Therefore every claim must include a body section:

```markdown
## 关系
- 支撑：[[孝为仁之本]]
- 反对：[[孝基于生育事实]]
- 限定：[[早期亲子关系影响道德发展]]
- 依赖：[[心理学证据只能提供机制解释]]
```

Do not rely only on frontmatter fields like `supports:` or `limits:` if you want graph edges to appear.

## Useful Dataview Queries

Core claims:

```dataview
TABLE claim_type, status, confidence
FROM "claims"
WHERE core = true
SORT claim_type ASC, file.name ASC
```

Contested claims:

```dataview
TABLE claim_type, supports, opposes, limits
FROM "claims"
WHERE status = "contested" OR claim_type = "objection"
```

Stub claims needing evidence:

```dataview
TABLE claim_type, related_concepts
FROM "claims"
WHERE status = "stub" OR confidence = "low"
```

Debate hubs:

```dataview
TABLE status, positions, related_claims
FROM "debates"
SORT file.name ASC
```

Literature-review matrices:

```dataview
TABLE updated, sources
FROM "synthesis"
WHERE contains(file.name, "文献综述矩阵")
SORT updated DESC
```

If using the Obsidian skill alongside this one, set `OBSIDIAN_VAULT_PATH` to the same directory as the wiki path.
