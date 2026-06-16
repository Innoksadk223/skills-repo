---
name: deep-reading-to-wiki
description: Use when books, chapters, papers, source-discovery shortlists, or long Markdown sources must be read before karpathy-wiki, especially when raw-to-wiki ingest risks shallow summaries, missing claims, weak context, or low evidence density.
---

# Deep Reading To Wiki

## Core Idea

This skill is a pre-wiki deep-reading layer. It reads a long source with a limited token budget, produces a structured `reading_dossiers/` file, and hands that file to `karpathy-wiki` for graph compilation.

It does not replace `karpathy-wiki`, does not write formal wiki pages, and does not treat the dossier as raw evidence.

It may start from an explicit raw file or from a user-directed expansion shortlist produced by `SiliconFlow-rag`, such as "补充儿童教育" → candidate `wiki/raw/` sources.

## Output Contract

Write one Markdown dossier under the project root:

```text
reading_dossiers/<source-title>-深读档案.md
```

The dossier must use frontmatter and fixed headings. Load `references/dossier-template.md` before writing.

If the source is later compiled into wiki pages, update the dossier frontmatter:

```yaml
status: compiled
compiled_to:
  - wiki/claims/...
  - wiki/concepts/...
```

Do not delete dossiers by default. Treat them as durable audit and handoff records for how raw evidence was selected, compressed, and compiled.

## Dossier Retention Policy

Default lifecycle:

1. Keep new dossiers in `reading_dossiers/` with `status: draft` until they pass the quality gates.
2. After `karpathy-wiki` compilation, keep the dossier and update frontmatter to `status: compiled` plus `compiled_to:`.
3. If compiled dossiers become noisy, move them to `reading_dossiers/_archive/` and update frontmatter to `status: archived`.
4. Hard-delete a dossier only after explicit user approval.

Prefer archiving over deletion. A compiled dossier may still explain why a claim was created, why a candidate was rejected, what context risks were known, and which raw anchors must be rechecked. It is not raw evidence, not a formal wiki node, and not part of the default RAG index.

Ask the user before deleting any dossier unless the project has an explicit written cleanup policy. Only propose deletion when all of these are true:

- the dossier has been compiled or deliberately rejected;
- the relevant raw sources still exist under `wiki/raw/`;
- any useful wiki outputs are listed in `compiled_to:` or in the dossier handoff section;
- there is no unresolved context risk, pending RAG follow-up, or user-facing writing task depending on it.

Never delete original source files or `wiki/raw/` materials from this skill.

## Input Modes

Use the smallest input that can support a strong dossier:

| Mode | Input | What to do |
|---|---|---|
| Explicit source | One or more `wiki/raw/...md` paths | Create source-specific dossier(s). |
| Source-discovery shortlist | Candidate raw paths from `SiliconFlow-rag` with user intent and key terms | Pick high-value candidates, note weak candidates, then create dossier(s). |
| User-directed gap | A topic/gap from `social-science-km`, such as "补充儿童教育" | Require source discovery first unless raw paths are already known. |

Do not deep-read from the user's topic alone. If no raw path is located, stop and report the source-discovery blocker instead of inventing a dossier.

## Role Boundaries

| Layer | Responsibility |
|---|---|
| `wiki/raw/` | Original or converted source text. Never modify for interpretation. |
| `reading_dossiers/` | Pre-compiled deep-reading materials, context capsules, candidate nodes, handoff notes. |
| `karpathy-wiki` | Formal graph nodes, backlinks, `index.md`, `log.md`, claims, concepts, comparisons. |
| RAG index | Evidence recall, context expansion, citation checking, and local zoom-in. |

## Required Orientation

Before reading the long source, orient to the target wiki when available:

1. Read `wiki/SCHEMA.md`.
2. Read `wiki/index.md`.
3. Read the recent part of `wiki/log.md`.
4. Search existing wiki pages for obvious overlapping concepts, authors, claims, and comparisons.

If using the `social-science-km` workflow, run its RAG staleness check before RAG-assisted reading.

For topic-initiated dossiers, preserve the search context in frontmatter:

```yaml
trigger: user_directed_expansion
user_intent: "补充儿童教育"
source_discovery:
  - path: wiki/raw/...
    reason: "命中儿童教育、爱敬、积浸等关键词"
```

## Reading Budget

Never default to full-book reading. Use the cheapest level that can answer the quality gate:

| Level | Read | Purpose |
|---|---|---|
| L0 structure scan | TOC, introduction, conclusion, headings, chapter openings/endings | Map the source and select likely high-value regions. |
| L1 sparse sampling | Definitions, thesis paragraphs, transitions, summaries, tables, key notes | Build the candidate node pool. |
| L2 targeted close reading | Surrounding paragraphs or sections for high-value candidates | Build context capsules and evidence anchors. |
| L3 local full-section/chapter reading | Only for core claims, major disputes, or thesis-critical chapters | Resolve high-stakes context and compression risk. |

Only move upward when the lower level cannot support a candidate with enough context.

## Minimum Dossier Blocks

Every dossier must include only these default blocks:

1. Reading map.
2. Candidate node pool.
3. High-value deep dives.
4. Wiki handoff checklist.
5. Anti-slack self-check.

Conditional modules are allowed only when triggered:

| Trigger | Add |
|---|---|
| A concept has conflicting meanings, translations, or measurements | Concept lineage module. |
| The source challenges existing wiki claims or authors | Dispute / objection module. |
| One section is thesis-critical | Local full-section reading module. |
| The user is writing prose now | Writing-use module. |

## Context Capsules

Each high-value candidate claim, concept, or comparison must include a context capsule:

- raw anchor: file path, chapter/section if available, and short exact excerpt;
- local context: what problem the passage addresses and what it leads to;
- whole-source role: definition, premise, support, bridge, objection, limitation, conclusion, or method note;
- compression risk: what would be distorted if compressed into a wiki node;
- method boundary: normative claim, empirical finding, concept definition, interpretation, analogy, or AI inference;
- RAG follow-up questions: questions that can recover the source context later.

If a candidate lacks a raw anchor and context capsule, do not label it high value.

## Quality Gates

Load `references/quality-gates.md` before finalizing the dossier.

At minimum, the dossier must show:

- high-value areas and skipped areas;
- candidate concepts and claims;
- at least two of support, objection, limitation, or bridge claims when the source supports them;
- context capsules for high-value candidates;
- wiki relationship notes: update existing, create new, challenge existing, ignore as duplicate;
- clear separation between author claims, raw evidence, AI inference, and wiki migration suggestions.

If the gate fails, do not hand the dossier to `karpathy-wiki`. Continue targeted reading or report the blocker.

## Handoff To Karpathy-Wiki

The final section must tell the next agent:

- which existing wiki pages to update;
- which new `concepts/`, `claims/`, `comparisons/`, or `entities/` pages may be needed;
- which candidates are too weak for wiki entry;
- which raw anchors must be checked before formal compilation;
- which context risks must be preserved in formal wiki pages.

Formal wiki writing remains the job of `karpathy-wiki`.
