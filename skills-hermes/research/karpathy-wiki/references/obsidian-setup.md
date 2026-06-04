# Obsidian Integration

The wiki directory works as an Obsidian vault out of the box:
- `[[wikilinks]]` render as clickable links
- Graph View visualizes the knowledge network
- YAML frontmatter powers Dataview queries
- The `raw/assets/` folder holds images referenced via `![[image.png]]`

## Setup

For best results:
- Set Obsidian's attachment folder to `raw/assets/`
- Enable "Wikilinks" in Obsidian settings (usually on by default)
- **Exclude `raw/` from graph view:** Settings → Files & Links → Excluded files → add `raw/`. Also in Graph view → Filter → Excluded folders → add `raw/`. This keeps the knowledge graph clean — only wiki pages appear as nodes, not raw source files.
- **Graph color groups (path-based):** Open Graph view → Settings (gear icon) → Groups → create one group per page type:
  - Group 1: `path:entities/` → 🔵 blue (`#4a9eff`)
  - Group 2: `path:concepts/` → 🟢 green (`#4caf50`)
  - Group 3: `path:comparisons/` → 🟠 orange (`#ff9800`)
  - Group 4: `path:queries/` → ⚪ grey (`#9e9e9e`)
  - Group 5 (optional): `tag:#待补充` → dashed border / low opacity (stub pages)
- Install Dataview plugin for queries like `TABLE tags FROM "实体" WHERE contains(tags, "公司")`

If using the Obsidian skill alongside this one, set `OBSIDIAN_VAULT_PATH` to the same directory as the wiki path.
