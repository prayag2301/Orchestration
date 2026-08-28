# Mogestrator

**A context substrate and policy gateway for coding agents.**

Claude Code already orchestrates well — subagents, hooks, skills, MCP, plan mode.
What it doesn't have is memory that can be *checked*. Mogestrator keeps a live,
anchored, self-invalidating graph of your codebase and of what agents have
learned about it, serves precisely-scoped context on demand, and enforces prompt
integrity and network policy on every tool-using agent.

```bash
uvx mogestrator index          # nothing to install
mog serve --mcp                # Claude Code now has a memory that knows when it's wrong
```

> **Status: planning (M0).** The design is complete and documented; no code is
> written. Nothing below is installable today. Every performance and quality
> claim here is a **design target**, not a measurement — see
> [EVALUATION.md](docs/EVALUATION.md) for how each one gets validated, and
> [ROADMAP.md](docs/ROADMAP.md) for progress.

---

## The problem: compaction is a compression answer to a memory problem

Five failures show up in every long agentic session:

| | Failure | Why it happens |
|---|---|---|
| **F1** | After a compact, the agent forgets which file held the flag, the exact test error, the constraint you stated | Summarization keeps prose and drops precise anchors |
| **F2** | The summary says "auth lives in `middleware.py`". Forty edits later it doesn't, and nothing notices | A prose summary has no link to the code it describes, so it can't be invalidated |
| **F3** | Every new session — and every subagent spawn — re-derives the same repo facts from zero | No shared substrate; context is copied as text or re-grepped |
| **F4** | The agent retries the approach it ruled out 30 turns ago, hitting the same wall | The rejection and its reason were the first thing compaction dropped |
| **F5** | The same file gets read six times in a session to answer questions that needed one signature | Retrieval granularity is "the file" |

Compaction treats context as a **compression problem**. Mogestrator treats it as
a **memory-hierarchy problem** — and memory hierarchies are a solved discipline.
You don't compress a cache. You index it, score it, evict it, and fetch it back
on a miss.

## The approach

### 1. A typed graph, not a pile of chunks

Nodes are `Symbol`, `File`, `Module`, `Test`, `Config` — plus the half that
actually matters and that no re-index can rebuild: `Decision`, `Failure`,
`Constraint`, `Convention`, `Correction`. Edges are real relationships:
`calls`, `imports`, `tested_by`, `caused_by`, `supersedes`, and `co_changed`
(mined from git history — two symbols that change together in 8 of 10 commits
are coupled in a way no import graph shows).

### 2. Anchors make memory falsifiable

Every fact carries a content-hash anchor, **never line numbers** — those shift on
every edit above them:

```
anchor: { path: src/auth/middleware.py, symbol: verify_token,
          span_hash: sha256:9f3c…, commit: b4ef335 }
```

Re-index, the hash mismatches, the fact flips to `stale` — labelled and still
served with a warning, never silently wrong. `mog verify` gives you a drift rate:
a number for *how much of what the agent believes is no longer true*. A summary
can't do this, and that's the point.

### 3. Seed-and-spread retrieval

```
query → embed → k-NN → 8 SEEDS → budgeted graph walk (weighted, hop-decayed)
      → fuse structural + semantic + recency → pack to token budget
```

**Vectors find the door; edges walk the building.** "What breaks if I change
`parse_config`?" is answered *exactly* by inverting `calls` + `co_changed`.
Cosine similarity guesses at it and returns files that merely talk like config
code. Cost: one embedding call, then indexed SQL.

Every result carries its path from a seed, so bad retrieval is debuggable:

```console
$ mog search "how are refresh tokens validated" --explain --budget 2000
1. verify_token         src/auth/middleware.py::verify_token   L2  fresh
   seed (cosine 0.83)
2. TokenStore.refresh   src/auth/store.py::refresh             L2  fresh
   verify_token ──calls──> refresh
3. test_refresh_expiry  tests/test_auth.py::test_refresh_expiry L1 fresh
   verify_token ──tested_by──> test_refresh_expiry
⚠ 1 related fact is stale: decision d_71 ("use HS256") — config.py changed 4 commits ago
1,840 tokens · 32ms
```

### 4. Zoom levels — never read a whole file again

**L0** repo map (2–4k tokens) → **L1** file skeleton, signatures only → **L2** one
symbol body + its callers → **L3** full file with blame. Retrieval returns the
lowest zoom that answers the question.

### 5. Eviction with recall, instead of compaction

Live context is a scored cache with an explicit budget:

```
score = relevance × recency_decay × pin × (1 − staleness) × log(1 + hits)
```

Over budget, evict lowest-first — and **leave a stub**:

```
[evicted ctx_8f2a · "auth middleware token-refresh analysis" · 3.2k tokens
 · recall: mog recall ctx_8f2a]
```

40 tokens holding the place of 3,200, and the original is recoverable
**verbatim**. Compaction rewrites those 3.2k tokens into 300 tokens of prose from
which nothing is recoverable — and doesn't tell the agent what it lost.
`Correction`, `Constraint`, and pinned items are never evictable.

### 6. Warm subagents

A subagent gets a **context handle** — `ctx://run_7a1/task_3`, a query plus
pinned nodes — not a 20k-token transcript copy. It materializes exactly what it
needs at the zoom it needs. Cold starts (F3) stop being structural.

> Approaches considered and rejected — RAPTOR-style summarization trees, pure
> chunk RAG, LLMLingua-style token pruning, scratchpad markdown, KV-cache
> offload — are documented with their reasons in
> [ADR-0002](docs/adr/0002-graph-memory-over-summarization.md).

---

## The policy plane — for server-based chats

A hosted agent with tools has two exposures a local CLI mostly doesn't: a prompt
assembled from sources of mixed trust, and a network stack that will fetch
anything. And there's a sharper problem specific to us: **the context graph is
itself an injection vector.** Better memory without flow control is a
better-targeted vulnerability.

**Layered, signed prompts.** `identity → capability → policy → context → task`.
L0–L2 are digest-pinned and immutable at run time — retrieved content is
*structurally incapable* of landing there. Not "the model refuses to be
overridden": it can't reach the layer. Every layer's digest goes in the audit
record, so "what exactly was this agent told on Tuesday?" has an exact answer.

**Taint labels, not regex DLP.** Content carries `secret`, `repo:private`,
`web:untrusted`, `user:pii`, `derived`, `verified`, and labels **propagate
through derivation**. That catches the secret that was base64'd, paraphrased, or
split across two fields — because provenance is tracked, not strings. Rules are
flow constraints:

```yaml
flows:
  - deny: { taint: secret, to: egress }
  - deny: { taint: web:untrusted, to: prompt_layer, at_or_above: policy }
  - deny: { from: untrusted_instruction, to: write_action }
```

**Default-deny egress firewall.** Per-agent host allowlists; private and
link-local CIDRs blocked (`169.254.169.254` — the cloud-metadata SSRF path);
DNS **resolved once and pinned** for the request's lifetime, defeating rebinding;
off-allowlist redirects refused; body-size and rate caps bounding any successful
exfiltration. The ledger records **which rule allowed each request**, not just
that it happened.

**Capability tokens** — short-lived, run-scoped, per-user, so the model never
sees a key and can't be talked into leaking one, and an agent acting for user B
can't use user A's permissions. **Canary tripwire** — a random token in the
policy layer; if it ever appears in an outbound payload, the run dies and the
session is quarantined.

In **proxy mode** the security property comes from network topology, not from the
agent's cooperation. A policy the agent could route around is documentation.

Full threat model (T1–T6) and specification: [SPEC-policy.md](docs/SPEC-policy.md).

---

## Installation

Full channel matrix and build/signing process: [DISTRIBUTION.md](docs/DISTRIBUTION.md).
*None of these work yet — they ship in M6.*

```bash
# zero install — recommended first contact
uvx mogestrator index

# install as a tool
uv tool install mogestrator
pipx install mogestrator
pip install mogestrator

# no Python opinion
brew install prayag2301/tap/mog
curl -fsSL https://get.mogestrator.dev | sh      # signed binary, checksum-verified
irm https://get.mogestrator.dev/ps1 | iex        # Windows

# JS teams
npx @mogestrator/cli index

# containers
docker run --rm -v "$PWD:/w" -w /w ghcr.io/prayag2301/mogestrator index
```

**In Claude Code** — the primary integration:

```bash
claude mcp add mog -- mog serve --mcp --watch
```

Claude Code gains `search_context`, `expand`, `impact`, `why`, `remember`,
`recall`, `pin`, and `verify` as tools. Also planned: a plugin marketplace entry
(`/mog-search`, `/mog-why`), `mise`, Nix, Scoop, and a VS Code extension.

## Usage

```bash
mog init                      # scaffold mogestrator.yaml, .mog/, .mogignore
mog index --watch             # build the graph; incremental, stays live
mog status                    # counts, index age, anchor drift rate

mog search "where are refresh tokens validated" --explain --budget 2000
mog impact verify_token --tests          # what breaks, and which tests cover it
mog why "why not RS256"                  # decisions, failures, constraints
mog map                                  # L0 repo map

mog remember failure "RS256 rejected: key rotation needs infra we don't have" \
    --anchor src/auth/config.py::load_keys
mog recall ctx_8f2a          # restore an evicted item verbatim
mog pin n_9f3c

mog verify --fix             # re-check every anchor, report drift
mog ws show                  # working set, scores, budget usage

mog serve --mcp --watch                  # expose to Claude Code / any MCP client
mog gateway --policy policy/ --port 8080 # policy plane for server-based chats
mog policy explain api.github.com        # which rule allows this, and why
mog audit --egress --since 24h
```

Full command reference: [SPEC-cli.md](docs/SPEC-cli.md).
Config: [SPEC-config.md](docs/SPEC-config.md).

## What this is not

Not an agent framework or workflow engine — Claude Code orchestrates, we remember
and govern. Not a model or router. Not a RAG-over-chunks library (that's the
baseline we must beat). Not a hosted service in v1. Not a code-search UI for
humans — the consumer is an agent.

## Does it actually work?

Unknown, and we refuse to pretend otherwise. Every claim above is a hypothesis
until [EVALUATION.md](docs/EVALUATION.md) says otherwise. The harness measures
against four baselines — `rg` + full file reads (**B0**), chunk RAG (**B1**),
no management (**B2**), and summarization compaction (**B3**) — on localization,
impact, multi-session continuity, repeat-failure avoidance, staleness handling,
and cold subagent start.

Hard gates: **M2 doesn't ship** unless seed-and-spread beats both `rg` and chunk
RAG on tokens-to-correct-answer. **M4 doesn't ship** unless eviction-and-recall
beats compaction on continuity. **M5 doesn't ship** unless zero injected
memories reach a high-trust prompt layer.

If the graph loses to ripgrep, we publish that and change course. Negative
results go in `docs/results/` too.

## Documentation

| Document | Contents |
|---|---|
| [PLAN.md](docs/PLAN.md) | The five failures, the three planes, scope, milestones, risks, open questions |
| [SPEC-context-graph.md](docs/SPEC-context-graph.md) | **The core** — nodes, edges, anchors, zoom, seed-and-spread, working set, storage, MCP tools |
| [SPEC-policy.md](docs/SPEC-policy.md) | Threat model, prompt layers, taint flow, egress firewall, capabilities, audit |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module layout, protocols, request paths, degradation, perf targets |
| [EVALUATION.md](docs/EVALUATION.md) | Baselines, suites, metrics, ship gates |
| [SPEC-cli.md](docs/SPEC-cli.md) · [SPEC-config.md](docs/SPEC-config.md) | `mog` commands · `mogestrator.yaml` |
| [DISTRIBUTION.md](docs/DISTRIBUTION.md) | 16 install channels, build and signing |
| [ROADMAP.md](docs/ROADMAP.md) | M1–M6 checklists — the work queue |
| [adr/](docs/adr/) | Six decisions, each with the alternatives rejected |

## Requirements

Python 3.11+ (pip/uv/pipx channels only — binary, Homebrew, npm, and Docker
bundle their own runtime) · Git · a tree-sitter-supported language for symbol-level
indexing (Python, TypeScript, Go, Rust at M1; others degrade to file-level).
No API key needed: embeddings run locally by default and your code never leaves
the machine.

## Contributing

M0 is done; M1 is open. [CONTRIBUTING.md](CONTRIBUTING.md) — specs lead code,
decisions get an ADR, and context claims need numbers.

## License

MIT.
