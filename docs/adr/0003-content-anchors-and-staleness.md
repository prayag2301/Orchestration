# ADR-0003 — Content-hash anchors, not line numbers

**Status:** Accepted · **Date:** 2026-08-28

## Context
A remembered fact ("token validation happens in `verify_token`") is only useful
while it is true. Code moves constantly. We need identity for a span of code
that survives unrelated edits and detects relevant ones.

## Decision
Every derived fact carries `(path, symbol, span_hash, file_hash, commit)` where
`span_hash` is over the **normalized** symbol body. On re-index, a mismatch flips
dependent facts to `stale`. Stale facts are labelled and still served with a
warning, never silently served and never silently dropped. Renames are tracked by
body-hash continuity.

## Alternatives considered
- **Line numbers.** Break on any edit above the span. Non-starter.
- **Raw file hash only.** Any change anywhere invalidates everything in the file
  — so much false staleness that the signal becomes noise.
- **Git blame ranges.** Accurate and expensive; requires git for every check and
  fails on uncommitted working-tree state, which is exactly when an agent is
  working.
- **Semantic equivalence via embeddings.** Tolerant of refactors, but fuzzy and
  costly, and it can't answer "did this change?" with a yes or no.
- **Delete on drift.** Simpler, and it throws away the fact most likely to be
  *nearly* right — often the fastest route to a correct answer.

## Consequences
+ Memory is falsifiable; `mog verify` yields a drift rate, so "how much does the
  agent believe that is now wrong?" is a number.
+ Normalization means reformatting and comment edits don't cause false staleness.
− Normalization is per-language work, and getting it wrong causes either false
  staleness or missed drift.
− Storing anchors costs space on every fact.
