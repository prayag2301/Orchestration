# ADR-0004 — Evict with recall, don't compact

**Status:** Accepted · **Date:** 2026-08-28

## Context
When context fills, something must go. The question is whether what goes is
*recoverable* and whether the agent *knows* it went.

## Decision
Treat live context as a scored cache with an explicit budget. Evict lowest-score
items to a low-water mark (hysteresis), leaving a ~40-token **stub** naming what
was evicted and how to recall it verbatim. Evicted content returns to the graph
and is one call away. `Correction`, `Constraint`, active `Task`, and pinned items
are never evictable. Summarization survives only as a last tier for
conversational filler.

## Alternatives considered
- **Summarize at a threshold (status quo).** One pass, no infrastructure. Lossy,
  irreversible, and — the real problem — *invisible*: the agent cannot tell what
  it no longer knows, so it confidently proceeds on missing information.
- **Hard truncation of the oldest turns.** Cheap and predictable; drops the
  user's original constraints first, which are usually the most important tokens
  in the window.
- **Full-transcript-in-a-vector-store, retrieve per turn.** Nothing is lost, but
  every turn pays a retrieval tax, and conversational chunks retrieve poorly
  because they're context-dependent.
- **Model-decided ("what should I keep?").** Adaptive, non-deterministic, and it
  spends model calls to save model calls.

## Consequences
+ Nothing is lost, and the agent knows exactly what left and how to get it back.
+ The scoring function is tunable and inspectable (`mog ws show`).
− A stub costs tokens; a working set of many stubs has real overhead.
− Recall costs a round trip, so bad scoring shows up as latency.
− Requires the graph to be present — this cannot ship standalone.
