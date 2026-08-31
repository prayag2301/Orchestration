"""Core graph types. See docs/SPEC-context-graph.md §1-§3."""

from __future__ import annotations

import os
import secrets
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


def new_id(prefix: str) -> str:
    """Time-ordered id: sorts chronologically, collision-resistant enough for one repo."""
    return f"{prefix}_{int(time.time() * 1000):011x}{secrets.token_hex(4)}"


class NodeKind(StrEnum):
    # structural — derived from the repo, safe to rebuild
    REPO = "repo"
    MODULE = "module"
    FILE = "file"
    SYMBOL = "symbol"
    TEST = "test"
    CONFIG = "config"
    # episodic — learned, NOT rebuildable (SPEC-context-graph §1)
    DECISION = "decision"
    FAILURE = "failure"
    CONSTRAINT = "constraint"
    CONVENTION = "convention"
    CORRECTION = "correction"
    TASK = "task"
    EPISODE = "episode"

    @property
    def is_structural(self) -> bool:
        return self in _STRUCTURAL


_STRUCTURAL = frozenset(
    {NodeKind.REPO, NodeKind.MODULE, NodeKind.FILE, NodeKind.SYMBOL, NodeKind.TEST, NodeKind.CONFIG}
)


class EdgeKind(StrEnum):
    DEFINES = "defines"
    CALLS = "calls"
    IMPORTS = "imports"
    TESTED_BY = "tested_by"
    CONFIGURES = "configures"
    CO_CHANGED = "co_changed"
    ABOUT = "about"
    CAUSED_BY = "caused_by"
    SUPERSEDES = "supersedes"
    CONTRADICTS = "contradicts"
    DERIVED_FROM = "derived_from"


#: Defaults from SPEC-context-graph §2; overridable via retrieval.edge_weights.
EDGE_WEIGHTS: dict[EdgeKind, float] = {
    EdgeKind.DEFINES: 0.9,
    EdgeKind.CALLS: 0.8,
    EdgeKind.IMPORTS: 0.6,
    EdgeKind.TESTED_BY: 0.85,
    EdgeKind.CONFIGURES: 0.7,
    EdgeKind.CO_CHANGED: 0.5,
    EdgeKind.ABOUT: 0.95,
    EdgeKind.CAUSED_BY: 0.9,
    EdgeKind.SUPERSEDES: 1.0,
    EdgeKind.CONTRADICTS: 0.0,
    EdgeKind.DERIVED_FROM: 0.0,
}


class State(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


@dataclass(frozen=True, slots=True)
class Anchor:
    """Provenance for a fact, hashed by content so it survives unrelated edits.

    Never store line numbers as identity — they shift on every edit above the
    span (ADR-0003). ``start_line`` is a display hint only and is deliberately
    excluded from equality and from the hash.
    """

    path: str
    span_hash: str
    #: Optional: the authoritative per-file hash lives in the ``files`` table,
    #: keyed by the same path. Duplicating it on every node cost ~70 bytes each.
    file_hash: str | None = None
    symbol: str | None = None
    commit: str | None = None
    captured_at: float = field(default_factory=time.time)
    start_line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Omit empty fields: this dict is stored as JSON on every node."""
        out: dict[str, Any] = {"path": self.path, "span_hash": self.span_hash}
        for key in ("symbol", "file_hash", "commit", "start_line"):
            if (value := getattr(self, key)) is not None:
                out[key] = value
        out["captured_at"] = round(self.captured_at, 1)
        return out

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Anchor:
        return cls(**{k: d.get(k) for k in cls.__slots__ if k in d})  # type: ignore[arg-type]

    def matches(self, span_hash: str) -> bool:
        return self.span_hash == span_hash


@dataclass(slots=True)
class Node:
    kind: NodeKind
    name: str
    id: str = ""
    content: str = ""
    anchor: Anchor | None = None
    state: State = State.FRESH
    labels: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = new_id(self.kind.value[:4])

    @property
    def path(self) -> str | None:
        return self.anchor.path if self.anchor else self.meta.get("path")

    def display(self) -> str:
        """Human-readable location, e.g. ``src/a.py::Foo.bar``."""
        if self.anchor and self.anchor.symbol:
            return f"{self.anchor.path}::{self.anchor.symbol}"
        return self.path or self.name


@dataclass(slots=True)
class Edge:
    src: str
    dst: str
    kind: EdgeKind
    weight: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.weight is None:
            self.weight = EDGE_WEIGHTS.get(self.kind, 0.5)


def rel_path(path: str, root: str) -> str:
    """Repo-relative, forward-slashed — identity must not vary by OS (ARCH §7)."""
    return os.path.relpath(path, root).replace(os.sep, "/")
