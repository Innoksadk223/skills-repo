# Social Science Profile

Use this profile when the wiki supports social-science research: literature reviews, thesis writing, theory comparison, empirical evidence, policy analysis, interview/fieldwork materials, or mixed-methods work.

This profile is intentionally broader than philosophy. It covers sociology, education, psychology, political science, communication, management, social work, anthropology, public policy, and theory-heavy humanities/social-science projects.

## Core Difference From A General Wiki

A social-science wiki is not mainly a topic encyclopedia. It is a research argument system:

- concepts have competing definitions across authors, traditions, methods, periods, and translations;
- evidence has types and limits: empirical finding, interview material, archive, theory text, policy document, secondary review, counterevidence, or method caveat;
- disagreements are durable research assets, not noise to smooth away;
- literature must be reusable for writing: contribution, method, object, limitation, usable chapter, and relation to claims;
- claims must preserve method boundaries, especially when moving from descriptive evidence to normative, causal, or interpretive conclusions.

## When To Load This Profile

Load this file before `ingest`, `claims`, `synthesis`, or `query` when the user mentions:

- 社科、社会科学、文献综述、毕业论文、开题、理论框架、研究问题;
- 定性/定量/混合方法、访谈、田野、问卷、实验、政策文本;
- 学派争议、理论争议、概念界定、操作化、变量、机制、因果;
- 需要把文献整理成论文可写的结构。

## Page Pattern Additions

### Concept pages

For social-science concepts, add these sections when useful:

```markdown
## 术语与译名
- 中文名、英文名、常见译名、缩写、相邻术语。

## 定义谱系
| 作者/传统 | 定义或用法 | 方法/语境 | 与本库关系 |
|---|---|---|---|

## 操作化与测量
若该概念进入实证研究，说明常见指标、量表、变量或编码方式。

## 本库采用定义
说明当前 wiki/论文暂采用哪一种定义，以及不用哪一种定义。
```

Do not force these sections onto small stubs. Use them when the concept is important, contested, or reused by multiple claims.

### Claims

Use `references/claims.md`, but strengthen each core claim with:

- writing location: research question, chapter, section, or paragraph use;
- premise and reasoning bridge;
- evidence matrix with evidence type, source, location, strength, and limits;
- method boundary: what the evidence can and cannot prove;
- response path for major objections.

### Debates

Use `references/debates.md` for durable controversies, not ordinary two-column comparisons. A debate page is appropriate when several authors, methods, claims, or periods disagree around the same research question.

### Literature Review Matrices

Use `references/literature-review.md` when a batch of papers must become a thesis-ready literature review. Keep the matrix as a route map; put durable propositions in `claims/` and concept definitions in `concepts/`.

## Evidence Types

Use these labels in claim evidence matrices and literature-review tables:

| evidence_type | Use for |
|---|---|
| `theory_text` | theoretical, philosophical, or conceptual argument text |
| `classic_text` | canonical source, historical text, legal/policy source, or primary text |
| `quantitative` | survey, experiment, statistical model, meta-analysis |
| `qualitative` | interview, fieldnote, ethnography, coding, case narrative |
| `mixed_methods` | explicit combination of qualitative and quantitative evidence |
| `review` | literature review, systematic review, meta-review |
| `policy_context` | policy, law, institution, governance background |
| `counterevidence` | evidence that weakens or complicates a claim |
| `method_limit` | limitation about design, sample, scope, inference, or measurement |

These labels are not tags by default. Add them to `SCHEMA.md` only if the project wants to filter by them.

## Method Boundary Rule

Do not let evidence do more than it can do:

- quantitative association does not automatically prove causation;
- qualitative material does not automatically generalize to a population;
- empirical evidence does not by itself prove a normative conclusion;
- theory text does not by itself prove empirical prevalence;
- policy documents show institutional framing, not necessarily real practice.

When a claim crosses one of these boundaries, add a limitation claim or a `## 方法边界` subsection.

## Minimal Workflow

1. Read `SCHEMA.md`, `index.md`, recent `log.md`, and this profile.
2. Identify whether the task needs concepts, claims, debates, or a literature-review matrix.
3. Extract durable propositions into `claims/` before writing long synthesis.
4. Preserve disagreements in `debates/` or debate-style `comparisons/`.
5. Keep raw evidence locations as plain-text paths.
6. Update `index.md` and `log.md`.
