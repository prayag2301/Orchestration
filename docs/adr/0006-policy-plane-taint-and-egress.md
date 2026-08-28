# ADR-0006 — Taint tracking and default-deny egress over content filtering

**Status:** Accepted · **Date:** 2026-08-28

## Context
Server-hosted agents with tools face prompt injection, exfiltration, SSRF, and
confused-deputy attacks. Worse for us specifically: **the context graph is itself
an injection vector** (memory poisoning, T2). Shipping better memory without
flow controls would be shipping a better-targeted vulnerability.

## Decision
Structural controls at four levels: signed, layered, digest-pinned prompt
assembly where retrieved content is structurally unable to reach a policy layer;
taint labels that propagate through derivation; declarative flow rules over those
labels; and a default-deny egress firewall with CIDR blocks, resolve-and-pin DNS,
and no off-allowlist redirects. Plus run-scoped capability tokens and a canary
tripwire. Specified in [SPEC-policy.md](../SPEC-policy.md).

## Alternatives considered
- **Output filtering / regex DLP.** Cheap and near-useless: it sees strings, so
  base64, paraphrase, or splitting across fields defeats it. Taint tracks
  provenance, which survives all three.
- **"Be careful" in the system prompt.** Free, and it asks the credulous
  component to be the security boundary.
- **A classifier on every tool call.** Catches novel phrasings a rule list
  misses; adds latency and cost to every call and fails open under load. Useful
  as defense-in-depth, wrong as the primary control.
- **Full allowlist of tool calls, no network policy.** Insufficient — an allowed
  tool (`http_get`) is exactly how exfiltration happens.
- **Sandbox with no network at all.** Genuinely secure and useless for agents
  that must reach GitHub or an internal API.

## Consequences
+ The security property comes from network topology in proxy mode, so it does
  not depend on the agent cooperating.
+ Audit records answer "what was it told, what did it touch, which rule allowed
  it" exactly, months later.
+ Taint catches encoded and paraphrased exfiltration that string matching cannot.
− Label propagation is invasive: every content path in the codebase must carry
  labels, and one un-instrumented path is a hole.
− Over-tainting leads to false denials and, eventually, to users disabling it —
  a real adoption risk that needs tuning and good `mog policy explain` output.
− Proxy mode is the strong deployment and the hardest to set up (Q4).
