# ADR-0007 — Index scale findings from M1, and a revised size target

**Status:** Accepted · **Date:** 2026-08-31 · **Resolves:** Q2, Q5

## Context
M1 built the graph and index. Measuring it on a real repo (django/django,
4,989 indexed files, 44.6 MB of source, ~525k LOC) rather than on fixtures
falsified three assumptions from the planning phase. Recording them here rather
than silently re-baselining, per PLAN.md §4 ("prove it or drop it").

## Findings

**1. `sqlite-vec` is fine; the runtime that loads it is the risk (Q2).**
v0.1.9 loads, and `vec0` is an exhaustive scan — so recall is *exact*, not
approximate, which resolves the recall question outright. 50k vectors at 384
dims: 4.3 ms for k=10, scaling linearly, so ~86 ms projected at 10⁶ — inside the
250 ms retrieval budget. The real problem is that **macOS system Python is built
without SQLite extension support** (`enable_load_extension` is absent), so
`sqlite-vec` cannot load there at all. The store now probes for this and reports
a reason, and FTS5 + graph expansion is a first-class degraded mode.

**2. Storing bodies duplicates the repo (Q5).** Full symbol bodies cost ~16 MB
on Django for little benefit: the working tree is already the source of truth
and the anchor already detects when it moves. We store a 600-char L1 preview
plus byte offsets, and read bodies from disk at L2.

**3. Naive call resolution explodes combinatorially.** Linking every call to
every same-named definition produced **1,991,411 edges**, of which 98.3% were
ambiguous. `__init__` alone generated 534,473. Capping fan-out at 8 (a name
matching more definitions than that discriminates nothing — the IDF argument)
cut edges to 198,581, full index time from 29.6s to 11.2s, and the database from
624 MB to 145 MB.

## Decision
Cap call fan-out at 8. Store previews plus offsets, not bodies. Treat
FTS-only as a supported mode, not an error path. And **revise the DB-size target
from "< 15% of source" to "< 400% of source at symbol granularity"**, because
the original number was a guess with no analysis behind it and is not reachable:
an anchor, a preview, and a token-level FTS entry cost ~1 KB per symbol before a
single vector exists.

## Alternatives considered
- **Down-weight ambiguous edges instead of dropping them.** Keeps information in
  principle; in practice a 0.4-weight edge still costs a row, still costs index
  space, and still pollutes graph expansion. Dropping is honest about the fact
  that the edge carries no signal.
- **Resolve calls properly** with scope and import analysis per language. The
  correct fix, and a large one — real name resolution is most of a type checker.
  Deferred to M2, where retrieval quality will show whether it is worth it.
- **Keep the 15% target and shrink aggressively** (drop FTS, drop previews,
  hashes as BLOBs). Would reach maybe 60–80 MB, still ~150%, while giving up
  exact symbol search — the fallback that must work when embeddings do not.
- **Chase the target by indexing fewer symbols** (skip tests, skip private
  symbols). Hits the number by degrading the product.

## Consequences
+ Index is 4× faster and 4× smaller than the first working version, with the
  same node count.
+ Q2 and Q5 are closed with measurements rather than opinion.
+ Degraded FTS-only mode is designed for and tested, not discovered in the field.
− The revised size target is still unattractive: ~145 MB for a large repo, before
  vectors, which will add ~1.5 KB/node at 384 dims (another ~70 MB). Options for
  M2: quantized embeddings (int8, 4× smaller), embedding only exported symbols,
  or an optional external vector store. This is now a tracked risk, not a
  surprise.
− Dropped ambiguous calls mean some real edges are missing. Retrieval quality in
  M2 must be measured with this in mind.
