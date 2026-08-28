# ADR-0005 — Local-first, one SQLite file, Python core

**Status:** Accepted · **Date:** 2026-08-28

## Context
The artifact indexes an entire private codebase and stores what a team has
learned about it. That is among the most sensitive things a developer owns. It
must also install in seconds, or nobody tries it.

## Decision
Local-first: everything in one SQLite file (`.mog/graph.db`) with `sqlite-vec`
and FTS5, local ONNX embeddings by default, no account, no telemetry, no network
unless the user points at a remote provider. Core in Python 3.11+, pure-Python,
distributed as a wheel plus standalone binaries.

## Alternatives considered
- **Dedicated vector DB (Qdrant/LanceDB/FAISS).** Better recall at scale and a
  second thing to install, back up, and keep in sync with the graph. Revisit if
  Q2 shows `sqlite-vec` failing at 10⁶ vectors.
- **Postgres + pgvector.** One store for graph and vectors with real query
  power; requires a server, which kills the try-it-in-30-seconds property.
- **Hosted index.** Best cross-machine sharing, and it means shipping every
  customer's private source to us. Not in v1, plausibly not ever.
- **Rust or Go core.** Faster indexing and a smaller binary; the tree-sitter,
  MCP, and embedding ecosystems and our likely contributors are in Python.
  Revisit if indexing throughput becomes the binding constraint.
- **API embeddings by default.** Better quality, and it sends the whole codebase
  to a third party on first run — a terrible default, a reasonable opt-in.

## Consequences
+ `uvx mogestrator index` works offline with nothing preinstalled.
+ The graph is a single file: trivially backed up, gitignored, deleted.
+ No procurement conversation needed to try it.
− SQLite vector search will not match a purpose-built engine at large scale.
− Local embeddings are weaker than frontier API embeddings (Q1).
− Python startup cost is real; imports must stay lazy.
