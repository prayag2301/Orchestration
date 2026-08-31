"""Language-agnostic symbol extraction driven by per-language specs.

Adding a language should be a :class:`LangSpec`, not a new module. Anything a
spec cannot express degrades to file-level nodes plus FTS (ARCHITECTURE §5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tree_sitter import Node as TSNode


@dataclass(frozen=True, slots=True)
class LangSpec:
    """How to find symbols, calls and imports in one language's parse tree."""

    name: str
    extensions: tuple[str, ...]
    symbol_types: frozenset[str]
    call_types: frozenset[str] = frozenset()
    import_types: frozenset[str] = frozenset()
    #: Types that nest symbols (a class body holding methods), used to build
    #: qualified names like ``Foo.bar``.
    container_types: frozenset[str] = frozenset()
    test_path_markers: tuple[str, ...] = ("test_", "_test.", "/tests/", "spec.")
    test_name_prefixes: tuple[str, ...] = ("test_", "Test")


@dataclass(slots=True)
class Symbol:
    name: str
    qualname: str
    kind: str
    node: TSNode
    calls: list[str] = field(default_factory=list)
    is_test: bool = False


SPECS: dict[str, LangSpec] = {
    "python": LangSpec(
        name="python",
        extensions=(".py", ".pyi"),
        symbol_types=frozenset({"function_definition", "class_definition"}),
        call_types=frozenset({"call"}),
        import_types=frozenset({"import_statement", "import_from_statement"}),
        container_types=frozenset({"class_definition"}),
    ),
    "typescript": LangSpec(
        name="typescript",
        extensions=(".ts", ".tsx", ".js", ".jsx", ".mjs"),
        symbol_types=frozenset(
            {"function_declaration", "class_declaration", "method_definition",
             "generator_function_declaration"}
        ),
        call_types=frozenset({"call_expression", "new_expression"}),
        import_types=frozenset({"import_statement"}),
        container_types=frozenset({"class_declaration"}),
        test_name_prefixes=("test", "it", "describe"),
    ),
    "go": LangSpec(
        name="go",
        extensions=(".go",),
        symbol_types=frozenset({"function_declaration", "method_declaration", "type_declaration"}),
        call_types=frozenset({"call_expression"}),
        import_types=frozenset({"import_declaration"}),
        test_path_markers=("_test.go",),
        test_name_prefixes=("Test", "Benchmark", "Fuzz"),
    ),
    "rust": LangSpec(
        name="rust",
        extensions=(".rs",),
        symbol_types=frozenset({"function_item", "struct_item", "enum_item", "trait_item"}),
        call_types=frozenset({"call_expression", "macro_invocation"}),
        import_types=frozenset({"use_declaration"}),
        container_types=frozenset({"impl_item", "trait_item"}),
        test_path_markers=("/tests/", "_test.rs"),
        test_name_prefixes=("test_",),
    ),
}

_BY_EXT: dict[str, LangSpec] = {ext: spec for spec in SPECS.values() for ext in spec.extensions}


def spec_for_path(path: str) -> LangSpec | None:
    dot = path.rfind(".")
    return _BY_EXT.get(path[dot:]) if dot != -1 else None


def _text(node: TSNode, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _name_of(node: TSNode, src: bytes) -> str | None:
    named = node.child_by_field_name("name")
    if named is not None:
        return _text(named, src)
    # Rust impl blocks and similar name themselves through a type field.
    for field_name in ("type", "declarator", "pattern"):
        alt = node.child_by_field_name(field_name)
        if alt is not None:
            return _text(alt, src).split("(")[0].strip()
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "field_identifier"):
            return _text(child, src)
    return None


def _callee_name(call: TSNode, src: bytes) -> str | None:
    """Best-effort callee name. ``a.b.c()`` resolves to ``c``.

    Deliberately unresolved across modules: cross-file resolution happens in the
    indexer, which is the only place that knows every symbol in the repo.
    """
    fn = call.child_by_field_name("function") or (call.children[0] if call.children else None)
    if fn is None:
        return None
    if fn.type in ("identifier", "type_identifier"):
        return _text(fn, src)
    if fn.type in (
        "attribute", "member_expression", "selector_expression",
        "field_expression", "scoped_identifier",
    ):
        for field_name in ("attribute", "property", "field", "name"):
            part = fn.child_by_field_name(field_name)
            if part is not None:
                return _text(part, src)
        if fn.children:
            return _text(fn.children[-1], src)
    if fn.type == "identifier" or fn.child_count == 0:
        return _text(fn, src)
    return None


def extract(
    tree_root: TSNode, src: bytes, spec: LangSpec, path: str
) -> tuple[list[Symbol], list[str]]:
    """Return (symbols, imported module strings) for one file."""
    symbols: list[Symbol] = []
    imports: list[str] = []
    path_is_test = any(marker in path for marker in spec.test_path_markers)

    def visit(node: TSNode, container: str | None) -> None:
        if node.type in spec.import_types:
            imports.append(" ".join(_text(node, src).split())[:200])
            return
        if node.type in spec.symbol_types:
            name = _name_of(node, src)
            if name:
                qualname = f"{container}.{name}" if container else name
                sym = Symbol(
                    name=name,
                    qualname=qualname,
                    kind=node.type,
                    node=node,
                    calls=_calls_within(node, spec, src),
                    is_test=path_is_test
                    or name.startswith(tuple(spec.test_name_prefixes)),
                )
                symbols.append(sym)
                # Always descend with this symbol as the container: a function
                # nested in another function is `outer.inner`, not `inner`.
                for child in node.children:
                    visit(child, qualname)
                return
        next_container = container
        if node.type in spec.container_types:
            named = _name_of(node, src)
            if named:
                next_container = named
        for child in node.children:
            visit(child, next_container)

    visit(tree_root, None)
    return symbols, imports


def _calls_within(symbol_node: TSNode, spec: LangSpec, src: bytes) -> list[str]:
    """Calls made directly by this symbol, excluding those in nested symbols."""
    found: list[str] = []

    def visit(node: TSNode, depth: int) -> None:
        if depth > 0 and node.type in spec.symbol_types:
            return  # belongs to the nested symbol, not this one
        if node.type in spec.call_types:
            name = _callee_name(node, src)
            if name:
                found.append(name)
        for child in node.children:
            visit(child, depth + 1)

    visit(symbol_node, 0)
    return list(dict.fromkeys(found))
