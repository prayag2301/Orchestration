# ADR-0001 — Pivot from workflow orchestrator to context substrate

**Status:** Accepted · **Date:** 2026-08-28 · **Supersedes:** the entire first planning pass

## Context
The initial plan was a config-as-code workflow runner (`orch`) for AI dev tasks.
Reviewing it against what Claude Code already ships — subagents, hooks, skills,
MCP, background tasks, plan mode, permissions — the overlap was almost total. We
would have been rebuilding the part that works, and competing on ergonomics with
a first-party tool.

Meanwhile the durable failures in agentic coding are all about **context**:
lossy compaction, memory that cannot be checked against the code, cold starts on
every session and subagent, forgotten failed approaches, and the same files read
over and over.

## Decision
Mogestrator is a **context substrate and policy gateway**, not an orchestrator.
It integrates as an MCP server so existing tools gain the capability without
changing. No DAGs, no step runner, no workflow YAML.

## Alternatives considered
- **Keep the orchestrator, add memory as a feature.** Memory becomes a
  second-class add-on to a product that competes head-on with Claude Code.
- **Ship both planes.** Doubles surface area before either is proven.
- **A pure MCP memory server, no policy plane.** Smaller and cleaner, but
  server-hosted agents are precisely where memory becomes an attack surface
  (memory poisoning); shipping retrieval without the flow controls would be
  shipping the vulnerability. ADR-0006.

## Consequences
+ Complements the ecosystem instead of competing with it; MCP means adoption
  costs one config line.
+ A sharp, testable thesis: less context, better answers, verifiable memory.
− Discards the previous planning pass; `orchestration.yaml` is gone.
− Harder to demo. "Fewer tokens for the same answer" needs a benchmark, which is
  why [EVALUATION.md](../EVALUATION.md) is a gate rather than a nicety.
