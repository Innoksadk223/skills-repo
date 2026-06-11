# Claims

Create and maintain `claims/` pages: graph-visible argument nodes for research theses, objections, limitations, and bridge propositions.

A claim is not a topic summary. A claim is a **可争论命题**: it can be supported, opposed, limited, or depend on another claim. If a point cannot be stated in one sentence, split it or keep it in a concept/comparison/synthesis page until it is clearer.

## When to Create Claims

Create or update claims when the user asks for, or the wiki contains:

- 论文论证地图、理论框架、章节论证路线;
- 核心争议、反方质疑、限制条件;
- cross-field bridges such as “儒家伦理 ↔ 依恋理论”;
- a synthesis page that has become a long human-readable argument.

Do not create claims for every quote or every evidence item. Evidence belongs inside the claim it supports.

## File Naming

Use the full proposition sentence as the filename:

```text
claims/孝的道德基础是良好照料.md
claims/心理学不能直接证明儒家伦理.md
claims/亲亲可以推扩为仁民爱物.md
```

Do not use numbering or vague short labels; Obsidian graph node names should be self-explanatory.

## Claim Types

Keep `claim_type` to exactly these five values:

| claim_type | 中文 | 用途 |
|---|---|---|
| `main` | 主论题 | 整套论证的中心命题 |
| `support` | 支撑命题 | 支撑主论题或其他 claim |
| `objection` | 反方质疑 | 明确提出可能反驳 |
| `limitation` | 限定边界 | 防止论证过度扩张 |
| `bridge` | 桥接命题 | 连接两个领域或理论 |

Do not add `response`. A response is expressed through `opposes: [...]` plus `## 回应对象` in the body.

## Frontmatter

```yaml
---
title: 孝的道德基础是良好照料
type: claim
claim_type: support
core: true
status: supported
confidence: medium
supports: [孝为仁之本]
opposes: [孝基于生育事实]
limits: []
depends_on: []
related_concepts: [孝, 慈, 养育, 感恩]
related_entities: [Philip J. Ivanhoe（艾文贺）, Erin Cline（柯爱莲）]
related_comparisons: []
sources: [Philip J. Ivanhoe（艾文贺）, Erin Cline（柯爱莲）]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

### Required Fields

`title`, `type`, `claim_type`, `core`, `status`, `confidence`, `supports`, `opposes`, `limits`, `depends_on`, `related_concepts`, `related_entities`, `related_comparisons`, `sources`, `created`, `updated`.

### Status Values

| status | 含义 |
|---|---|
| `stub` | 占位，证据不足 |
| `working` | 有初步证据，但尚未稳定 |
| `supported` | 已有足够证据支撑 |
| `contested` | 有支撑，也有重要反驳 |

### Core Claims

`core: true` means this claim is part of the argument skeleton.

Core claims must:

1. appear in `index.md` under `## 论证节点 / Claims`;
2. include at least 1-2 key evidence items;
3. include `## 命题`, `## 关系`, `## 关键证据`, `## 写作用途`;
4. link to related concepts/entities/comparisons in the body;
5. add backlinks from core related concept/entity/comparison pages when appropriate.

For social-science thesis work, core claims should also include `## 论证位置`, `## 前提与推理`, `## 证据矩阵`, and `## 方法边界` when the claim will be used in writing. These are body sections, not required frontmatter fields, so older claim pages remain valid.

Ordinary claims may be `core: false`, may stay `status: stub`, and do not need to be listed in `index.md`.

## Body Template

Use `references/templates/claim-template.md`.

Minimum body structure:

```markdown
# 孝的道德基础是良好照料

## 命题
孝的道德基础不应仅仅放在生育事实上，而应放在长期养育、照料、爱与支持所形成的关系之中。

## 关系
- 支撑：[[孝为仁之本]]
- 反对：[[孝基于生育事实]]
- 限定：无
- 依赖：无

## 支撑理由
...

## 论证位置
- 研究问题：
- 论文位置：
- 可回应的问题：

## 前提与推理
1. 前提一。
2. 前提二。
3. 因此，本命题成立或在某个范围内成立。

## 证据矩阵
| 证据类型 | 来源 | 位置 | 支持力度 | 限制 |
|---|---|---|---|---|
| theory_text | [[Philip J. Ivanhoe（艾文贺）]] | `raw/02-学术研究/Filial Piety as a Virtue.md:31-33` | 中 | 只能支持概念修正，不能直接证明经验普遍性 |

## 关键证据
- [[Philip J. Ivanhoe（艾文贺）]]：反对把孝建立在单纯生育事实上。
  - 证据位置：`raw/02-学术研究/Filial Piety as a Virtue.md:31-33`

## 反驳与限制
...

## 方法边界
说明本 claim 依赖的证据能证明什么，不能证明什么。

## 写作用途
可用于回应“孝是否只是血缘义务”的质疑。

## 关联页面
[[孝（Filial Piety）]]、[[慈（Parental Care）]]、[[家（Family）]]
```

`## 命题` and `## 关系` are mandatory for every claim. The relationship wikilinks make the argument network visible in Obsidian; frontmatter alone is not enough.

## Evidence Rules

Core claims must have evidence. Ordinary claims can temporarily lack evidence only if:

```yaml
status: stub
confidence: low
sources: []
```

and the body includes:

```markdown
## 待补证据
- 需要补充什么类型的证据
- 可能从哪些 raw/ 或 wiki 页面找
```

Claim evidence links to wiki pages, not raw files. Raw source locations are written as plain-text paths:

```markdown
- [[Kochanska（格拉日娜·科汉斯卡）]]：MRO 纵向预测儿童良知发展。
  - 证据位置：`raw/03-心理学文献/母亲与幼儿之间的相互响应取向：良知早期发展的背景.md:52-60`
```

Do not write `[[raw/...]]`.

For social-science projects, prefer a lightweight evidence matrix over a long evidence bank:

| field | meaning |
|---|---|
| 证据类型 | `theory_text`, `classic_text`, `quantitative`, `qualitative`, `mixed_methods`, `review`, `policy_context`, `counterevidence`, `method_limit` |
| 来源 | wiki page link, author page, concept page, or source name |
| 位置 | plain-text raw path with page/line/section if known |
| 支持力度 | high / medium / low, or a short Chinese note |
| 限制 | what this evidence cannot prove |

## Objections and Responses

Core objections should be standalone claim pages when they:

1. directly threaten the main thesis;
2. affect a whole chapter or major section;
3. require several pages or evidence items to answer;
4. are likely advisor/reader/defense questions;
5. have independent graph value.

Examples:

```text
claims/亲亲可能导致偏私.md
claims/孝可能滑向家庭权力压迫.md
claims/心理学不能直接证明儒家伦理.md
```

Minor objections stay in the target claim's `## 反驳与限制` section.

For responses, do not create a new type. Use:

```yaml
claim_type: support
opposes: [亲亲可能导致偏私]
```

and body:

```markdown
## 回应对象
- [[亲亲可能导致偏私]]
```

## Index Rules

`index.md` lists only the main claim and core claims:

```markdown
## 论证节点 / Claims

### 主论题
- [[孝为仁之本]] — 论文核心命题。

### 核心支撑命题
- [[孝的道德基础是良好照料]] — 回应“血缘/生育论证”。
- [[家是道德生成的原初场域]] — 说明家的哲学地位。

### 核心限定命题
- [[心理学不能直接证明儒家伦理]] — 限定跨学科论证边界。
```

Do not list every ordinary claim; discover those through graph links and the `claims/` folder.

## Backlink Rules

Every claim links to related `concepts/`, `entities/`, `comparisons/`, and other `claims/`.

Only core related pages need backlinks. Add a section like:

```markdown
## 相关论证节点
- [[孝的道德基础是良好照料]]
- [[孝为仁之本]]
```

A related page is core if it:

1. is part of the main thesis;
2. is used by 2+ core claims;
3. bridges fields;
4. is necessary for an objection or limitation.

## Procedure: Extract Claims from Argument Material

1. Identify the main thesis and core support/objection/limitation/bridge points.
2. Ignore chapter-order notes and pure writing logistics; keep those in `synthesis/`.
3. For each graph-worthy point, write one sentence under `## 命题`.
4. Create/update the claim page with frontmatter and body wikilinks.
5. Move evidence from any evidence bank into the relevant claim's `## 关键证据`.
6. Update `index.md` only for `core: true` claims.
7. Add backlinks from core concepts/entities/comparisons.
8. Append all created/updated files to `log.md`.

## Pitfalls

- Creating a claim for every quote — use evidence bullets instead.
- Using short titles that are unreadable in graph view.
- Relying on frontmatter arrays only — body wikilinks are required for Obsidian graph visibility.
- Linking raw files as wikilinks — keep raw paths plain text.
- Letting `synthesis/` keep the real argument while claims remain empty shells.
