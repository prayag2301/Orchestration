# Roadmap

Sequencing, not dates. Every milestone ends in a demo a stranger can reproduce.

| M | Theme | Exit demo |
|---|-------|-----------|
| **M0** ✅ | Planning | This docs set |
| **M1** | Graph + index | `mog index` a 50k-LOC repo < 60s; `mog search` returns anchored results |
| **M2** | Retrieval + zoom | Seed-and-spread beats chunk-RAG (B1) and `rg` (B0) on the harness |
| **M3** | MCP server | Claude Code uses `search_context` / `why` in a real session |
| **M4** | Ledger + working set | Eviction-and-recall survives a reset that compaction (B3) does not |
| **M5** | Policy plane | Gateway blocks scripted exfiltration; audit names the rule |
| **M6** | Distribution | `uvx mogestrator` green on macOS/Linux/Windows |

## M1 — Graph and index
- [ ] SQLite schema + migrations; `sqlite-vec` and FTS5 wired (resolve **Q2**)
- [ ] tree-sitter parsers: Python, TypeScript, Go, Rust
- [ ] Node/edge extraction: `defines`, `calls`, `imports`, `tested_by`
- [ ] Anchors: normalized span hashing, drift detection, rename continuity
- [ ] Git miner for `co_changed`
- [ ] Local embedder + content-hash cache (resolve **Q1**)
- [ ] `mog init/index/status/verify/show/map`
- [ ] Perf harness for the ARCHITECTURE §6 targets

## M2 — Retrieval
- [ ] k-NN seeding + FTS5 exact fallback
- [ ] Budgeted weighted spread with hop decay
- [ ] Weighted RRF fusion; `--explain` provenance paths
- [ ] L0–L3 zoom renderers; automatic zoom selection
- [ ] Token-budgeted packing
- [ ] `mog search/impact/neighbors`
- [ ] **Eval gate:** beat B0 and B1 on localization and token cost

## M3 — MCP
- [ ] `mog serve --mcp` (stdio + http), `--watch` incremental reindex
- [ ] Eight tools per SPEC-context-graph §9
- [ ] Every result stamped with state, anchor, provenance, trust label
- [ ] Context handles for subagent warm starts
- [ ] Claude Code plugin wrapping the server

## M4 — Memory
- [ ] Episodic ledger: Decision, Failure, Constraint, Convention, Correction
- [ ] Working set scoring, hysteresis eviction, stubs, `recall`
- [ ] `contradicts` detection and surfacing
- [ ] `mog remember/recall/why/ledger/ws`
- [ ] Auto-capture via Claude Code hooks (resolve **Q3**)
- [ ] **Eval gate:** beat B3 on continuity and repeat-failure avoidance

## M5 — Policy plane
- [ ] Signed layered prompt assembly with digest pinning
- [ ] Taint labels and propagation; declarative flow rules
- [ ] Egress firewall: default-deny, CIDR blocks, resolve-and-pin, no redirects
- [ ] Capability tokens; per-user scoping
- [ ] Canary tripwire; memory-write policy (T2)
- [ ] Audit ledger + `mog audit`, `mog policy explain/test`
- [ ] Proxy deployment mode (resolve **Q4**)
- [ ] **Eval gate:** zero poisoning through, full exfiltration suite blocked

## M6 — Distribution
- [ ] PyPI `mogestrator`, uv/pipx, Homebrew, binaries, Docker, npm wrapper
- [ ] Signed releases, checksums, SBOM, install smoke matrix

## Deferred
Hosted multi-tenant service · team dashboards · IDE UI · cross-repo federated
graphs · fine-tuned retrievers. Revisit after M6, with evidence.
