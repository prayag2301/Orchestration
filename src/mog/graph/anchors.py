"""Content-hash anchoring and drift detection (ADR-0003, SPEC-context-graph §3).

The contract: a fact anchored to a span goes ``stale`` when that span's meaning
changes, and does NOT go stale when the file is merely reformatted, recommented,
or edited elsewhere. Getting this wrong produces either false staleness (noise
until users stop believing the labels) or missed drift (silent wrongness).
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tree_sitter import Node as TSNode

#: Node types excluded from the normalized form. Comments carry no behaviour, so
#: editing one must not invalidate a fact about the code around it.
_IGNORED_TYPES = frozenset({"comment", "line_comment", "block_comment"})


def sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def file_hash(source: bytes) -> str:
    return sha256(source)


def normalize_span(node: TSNode, source: bytes) -> str:
    """Token stream of ``node``, comments dropped and whitespace collapsed.

    Uses the parse tree rather than a regex so that a ``#`` inside a string
    literal is not mistaken for a comment.
    """
    tokens: list[str] = []

    def visit(n: TSNode) -> None:
        if n.type in _IGNORED_TYPES:
            return
        if n.child_count == 0:
            text = source[n.start_byte : n.end_byte].decode("utf-8", "replace").strip()
            if text:
                tokens.append(text)
            return
        for child in n.children:
            visit(child)

    visit(node)
    return " ".join(tokens)


def span_hash(node: TSNode, source: bytes) -> str:
    """Stable identity for a span: survives reformatting, changes with behaviour."""
    return sha256(normalize_span(node, source))


def span_hash_text(text: str) -> str:
    """Fallback for languages with no parser: collapse whitespace only."""
    return sha256(" ".join(text.split()))


def drift(anchor_span_hash: str, current_span_hash: str | None) -> str | None:
    """Classify an anchor against the current tree.

    Returns ``None`` when the anchor still holds, otherwise a reason. A missing
    span (``current_span_hash is None``) means the symbol was removed or renamed
    beyond recognition.
    """
    if current_span_hash is None:
        return "span_missing"
    if anchor_span_hash != current_span_hash:
        return "span_changed"
    return None
