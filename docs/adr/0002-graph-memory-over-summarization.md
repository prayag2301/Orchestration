# ADR-0002 — Typed graph memory instead of summarization

**Status:** Accepted · **Date:** 2026-08-28

## Context
The standard response to a full context window is to summarize it. That is a
compression framing. Compression of natural language is lossy in an unbounded
way: you cannot say what was lost, you cannot get it back, and the summary
cannot be checked against reality.

## Decision
Model context as a **typed, anchored, embedded graph** with hybrid
seed-and-spread retrieval (SPEC-context-graph §5) and zoom levels. Structural
edges do the precision work; embeddings only find entry points.

## Alternatives considered
- **Hierarchical summarization trees (RAPTOR-style).** Cluster and summarize
  recursively, retrieve at the right level. Elegant, and still lossy at every
  level; summaries drift from code with no invalidation path, and every level
  costs model calls to build and rebuild.
- **Pure vector RAG over chunks.** Simple, language-agnostic, and the baseline
  we must beat (B1). Loses on code: chunk boundaries cut functions in half,
  "what calls this?" is not a similarity question, and the same code is
  re-embedded and re-returned repeatedly.
- **Token-level prompt pruning (LLMLingua-style).** Genuinely reduces tokens and
  is complementary, but it optimizes a prompt in flight — it builds nothing
  durable, so session #40 is as expensive as session #1.
- **External scratchpad markdown files** (what CLAUDE.md effectively is). Zero
  infrastructure, human-readable, and it is exactly what we're improving on:
  unstructured, hand-maintained, unqueryable, and silently stale.
- **KV-cache offload / attention-sink tricks.** Real wins, but they live inside
  the inference stack. Unavailable to us over a provider API.

## Consequences
+ Retrieval is explainable and exact where structure exists.
+ Deduplication is free: one symbol, one node, however often it's read.
+ Facts can be invalidated (ADR-0003) — impossible for a summary.
− Much heavier than summarization: parsers per language, a real index, an
  embedding pipeline, incremental maintenance.
− Fails soft on unsupported languages (file-level + FTS only).
− Must be *proved* faster and cheaper than `rg`, which is a high bar.
