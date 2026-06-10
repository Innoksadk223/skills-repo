# Retrieval Architecture

Use two retrieval modes. Wiki pages guide recall; raw chunks provide evidence.

## Raw-only retrieval

Use when the user wants direct evidence from source materials.

```text
question → embedding → vector + BM25 → RRF → optional rerank → evidence
```

## Wiki-first retrieval

Use when a `karpathy-wiki` structure exists and the user asks conceptual, argumentative, cross-source, or thesis-writing questions.

```text
question
→ retrieve wiki index
→ extract titles/frontmatter/wikilinks/claim relations
→ build expanded query locally
→ retrieve raw index
→ optional rerank raw candidates
→ output Wiki Hits + Expanded Query + Raw Evidence
```

Recommended layout:

```text
检索索引/wiki    # claims/concepts/entities/comparisons/synthesis/queries
检索索引/raw     # wiki/raw original evidence
```

## RAG norm

- **Dual retrieval**: vector similarity + lightweight BM25 lexical search.
- **RRF**: vector and BM25 ranks are fused with `1/(k+rank)`.
- **Multi-query**: optional; disabled by default; calls chat completions to generate 3 additional queries.
- **Rerank**: optional; use only when the user asks for better ordering, precise ranking, rerank mode, or similar wording.

## Evidence boundary

- Wiki hits are recall guides, not proof.
- Raw evidence is the citation basis.
- Do not claim a paper says something unless raw evidence supports it.
