# Wiki Schema

## Domain
[What this wiki covers — e.g., "大语言模型（LLM）研究", "个人健康管理", "创业情报"]

## Conventions
- **Language:** Wiki content in Chinese. English technical terms use 中英对照 on first occurrence. Page titles in Chinese. See wiki-level language convention.
- File names: Chinese or English, consistent within project. e.g. `Transformer-架构.md` or `transformer-architecture.md`
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- **Provenance markers:** On pages that synthesize 3+ sources, append `^[raw/articles/source-file.md]`
  at the end of paragraphs whose claims come from a specific source. This lets a reader trace each
  claim back without re-reading the whole raw file. Optional on single-source pages where the
  `sources:` frontmatter is enough.

## Frontmatter
  ```yaml
  ---
  title: 页面标题（English Title if needed）
  created: YYYY-MM-DD
  updated: YYYY-MM-DD
  type: entity | concept | comparison | debate | query | synthesis | claim
  tags: [from taxonomy below]
  sources: [raw/articles/source-name.md or wiki page names]
  # Optional quality signals:
  confidence: high | medium | low        # how well-supported the claims are
  contested: true                        # set when the page has unresolved contradictions
  contradictions: [other-page-slug]      # pages this one conflicts with
  ---
  ```

`confidence` and `contested` are optional but recommended for opinion-heavy or fast-moving
topics. Lint surfaces `contested: true` and `confidence: low` pages for review so weak claims
don't silently harden into accepted wiki fact.

### raw/ Frontmatter

Raw sources ALSO get a small frontmatter block so re-ingests can detect drift:

```yaml
---
source_url: https://example.com/article   # original URL, if applicable
ingested: YYYY-MM-DD
sha256: <hex digest of the raw content below the frontmatter>
---
```

The `sha256:` lets a future re-ingest of the same URL skip processing when content is unchanged,
and flag drift when it has changed. Compute over the body only, not the frontmatter itself. If
there are blank lines immediately after the closing `---`, ignore those leading blank lines.

## Tag Taxonomy
[Define 10-20 top-level tags for the domain. Add new tags here BEFORE using them.]

Example for AI/ML:
- 模型架构：`模型`、`架构（architecture）`、`基准（benchmark）`、`训练`
- 人物/组织：`人物`、`公司`、`实验室`、`开源`
- 技术：`优化`、`微调（fine-tuning）`、`推理（inference）`、`对齐（alignment）`、`数据`
- 元信息：`辨析`、`时间线`、`争议`、`预测`

Rule: every tag on a page must appear in this taxonomy. If a new tag is needed,
add it here first, then use it. This prevents tag sprawl.

## Page Thresholds
- **Create a full page** when an entity/concept is mentioned in a source and is directly related to the domain (see Domain field above). One source is enough — don't gate on source count.
- **Create a stub page** when an entity/concept is [[wikilinked]] by another page but doesn't yet have its own page. Stubs prevent dead links in Obsidian's graph view. See Stub Pages below for format.
- **Add to existing page** when a source mentions something already covered
- **DON'T create a page** for things entirely outside the domain
- **Upgrade stub → full page** when enough material accumulates to write a meaningful entry — remove the stub marker, fill in detail, update `confidence`
- **Split a page** when it exceeds ~200 lines — break into sub-topics with cross-links
- **Archive a page** when its content is fully superseded — move to `_archive/`, remove from index
- **Archive a stub** when all pages that [[wikilink]] to it have been archived — an orphan stub with no active referrers is dead weight

## Entity Pages
One page per notable entity. Include:
- Overview / what it is
- Key facts and dates
- Relationships to other entities ([[wikilinks]])
- Source references

## Concept Pages
One page per concept or topic. Include:
- Definition / explanation
- Current state of knowledge
- Open questions or debates
- Related concepts ([[wikilinks]])

For social-science projects, important concepts may also include:
- terms, translations, aliases, and abbreviations;
- definition history or competing definitions by author/school;
- operationalization, measurement, or coding when used empirically;
- this wiki's working definition and why adjacent definitions are not used.

## Stub Pages
For concepts/entities that are [[wikilinked]] but lack enough source material for a full page.
Stubs ensure Obsidian's graph view has no dead links. Format:

```markdown
---
title: 概念名
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: concept
tags: [待补充]
sources: []
confidence: low
---

# 概念名

> 📝 待完善。此页面被其他页面引用，尚无详细内容。

## 简述
[从引用此概念的 wiki 页面中提取的一句话定义，如果可用。不引用 raw/ 源文件。]

## 被引用
- [[页面A]] — 在此上下文中提及
```

Stubs must still be added to `index.md` under the correct section.
**Stubs never reference raw/ sources.** Their `sources:` field stays empty.
When a stub later accumulates enough material, upgrade it to a full page:
remove the 📝 marker, fill in full content, update `confidence`.

## Claim Pages
Argument nodes for thesis structures, objections, limitations, and bridge propositions. Include:
- **命题** — one sentence stating the claim
- **关系** — body wikilinks for 支撑/反对/限定/依赖 so Obsidian graph shows the argument network
- **支撑理由** — short reasoning, not a full essay
- **关键证据** — links to wiki pages plus plain-text raw locations
- **反驳与限制**
- **写作用途**
- **关联页面**

Core claims use `core: true`, must have evidence, and must be listed in `index.md`. Ordinary claims can be `core: false` and `status: stub` while evidence is pending.

Claim-specific frontmatter:

```yaml
claim_type: main | support | objection | limitation | bridge
core: true | false
status: stub | working | supported | contested
supports: []
opposes: []
limits: []
depends_on: []
related_concepts: []
related_entities: []
related_comparisons: []
```

Do not wikilink `raw/` files from claim evidence; write raw evidence locations as code paths.

## 辨析页（Comparison）
Side-by-side analysis, distinction, or clarification between concepts/entities. Include:
- **比较/区分什么、为什么** — 两个概念哪里像、哪里不同
- **易混点** — 一句话说清本质区别（社科高频：相关 vs 因果、平等 vs 公平）
- **对比维度** — 表格格式（适用时）
- **结论或综合**
- **来源**

## 争议谱系页（Debate）
Use `debates/` for mature social-science controversies, or keep smaller controversy pages in
`comparisons/`. Include:
- **争议问题** — what research question is disputed;
- **主要立场** — positions, representative authors, and claims;
- **证据与反证** — evidence type, source, strength, and limitation;
- **方法边界** — what cannot be inferred from the evidence;
- **写作用途** — how the debate helps literature review, theory framing, discussion, or defense.

## 文献综述矩阵
Use `synthesis/文献综述矩阵-主题.md` for source-to-writing route maps. A matrix may summarize
authors, methods, contributions, limits, and thesis use, but durable propositions still belong
in `claims/`.
