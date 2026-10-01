"""Module 2 - AST Analyzer: walk a Java syntax tree and record declarations and raw references.

The analyzer only knows about a single file. It records type names exactly as written
(`SymbolReference.name`); turning those into fully-qualified, repository-wide identities
is the job of the dependency extractor.
"""

from __future__ import annotations

import re
import sys

from tree_sitter import Node

from . import models as m
from .models import FileFacts, ImportDecl, MethodDecl, SymbolReference, TypeDecl
from .repository import ParsedFile

TYPE_DECLARATIONS = {
    "class_declaration": "class",
    "interface_declaration": "interface",
    "enum_declaration": "enum",
    "record_declaration": "record",
    "annotation_type_declaration": "annotation",
}
PRIMITIVE_TYPES = {"integral_type", "floating_point_type", "boolean_type", "void_type"}
SCOPE_NODES = {"block", "lambda_expression", "for_statement", "enhanced_for_statement",
               "catch_clause", "try_with_resources_statement", "switch_block_statement_group"}
_TYPE_ARGS = re.compile(r"<[^<>]*>")
_UNKNOWN = object()


def _text(node: Node | None) -> str:
    return node.text.decode("utf-8", errors="replace") if node is not None else ""


def _line(node: Node) -> int:
    return node.start_point[0] + 1


def _strip_generics(name: str) -> str:
    name = re.sub(r"\s+", "", name)
    while "<" in name:
        stripped = _TYPE_ARGS.sub("", name)
        if stripped == name:
            break
        name = stripped
    return name.replace("[]", "")


def base_type_name(node: Node | None) -> str | None:
    """`List<Foo>` -> "List", `Foo[]` -> "Foo", `int` -> None."""
    if node is None:
        return None
    if node.type == "type_identifier":
        name = _text(node)
        return None if name == "var" else name
    if node.type == "scoped_type_identifier":
        return _strip_generics(_text(node))
    if node.type in ("generic_type", "array_type", "annotated_type"):
        for child in node.named_children:
            if child.type not in ("type_arguments", "dimensions", "marker_annotation", "annotation"):
                return base_type_name(child)
    return None


class JavaFileAnalyzer:
    def __init__(self, parsed: ParsedFile) -> None:
        self.parsed = parsed
        self.facts = FileFacts(path=parsed.rel_path, package="", has_syntax_errors=parsed.has_syntax_errors)
        self._type_stack: list[tuple[TypeDecl, Node]] = []
        self._scopes: list[dict[str, object]] = []   # name -> type name as written, or None if unknown
        self._class_scopes: list[dict[str, object]] = []
        self._member: str | None = None

    # ------------------------------------------------------------------ entry point

    def analyze(self) -> FileFacts:
        self._walk(self.parsed.tree.root_node)
        return self.facts

    # ------------------------------------------------------------------ helpers

    @property
    def _owner(self) -> TypeDecl | None:
        return self._type_stack[-1][0] if self._type_stack else None

    def _ref(self, name: str | None, kind: str, node: Node, detail: str | None = None) -> None:
        owner = self._owner
        if owner is None or not name:
            return
        self.facts.references.append(SymbolReference(
            owner=owner.fqn, name=name, kind=kind, line=_line(node), member=self._member, detail=detail))

    def _use_types(self, node: Node | None, kind: str) -> None:
        """Record every type named inside a type expression, including generic arguments."""
        if node is None:
            return
        if node.type == "type_identifier":
            if _text(node) != "var":
                self._ref(_text(node), kind, node)
        elif node.type == "scoped_type_identifier":
            self._ref(_strip_generics(_text(node)), kind, node)
            for arg in node.named_children:
                if arg.type == "type_arguments":
                    self._use_types(arg, kind)
        elif node.type in ("marker_annotation", "annotation"):
            self._walk(node)
        elif node.type not in PRIMITIVE_TYPES:
            for child in node.named_children:
                self._use_types(child, kind)

    def _declare(self, name: str, type_name: object) -> None:
        if self._scopes and name:
            self._scopes[-1][name] = type_name

    def _lookup(self, name: str) -> object:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return _UNKNOWN

    def _walk_children(self, node: Node) -> None:
        for child in node.named_children:
            self._walk(child)

    # ------------------------------------------------------------------ dispatcher

    def _walk(self, node: Node | None) -> None:
        if node is None:
            return
        handler = getattr(self, f"_on_{node.type}", None)
        if node.type in TYPE_DECLARATIONS:
            self._on_type_declaration(node)
        elif handler is not None:
            handler(node)
        elif node.type in SCOPE_NODES:
            self._scopes.append({})
            try:
                self._walk_children(node)
            finally:
                self._scopes.pop()
        else:
            self._walk_children(node)

    # ------------------------------------------------------------------ file level

    def _on_package_declaration(self, node: Node) -> None:
        for child in node.named_children:
            if child.type in ("scoped_identifier", "identifier"):
                self.facts.package = _text(child)

    def _on_import_declaration(self, node: Node) -> None:
        static = any(c.type == "static" for c in node.children)
        wildcard = any(c.type == "asterisk" for c in node.children)
        path = next((_text(c) for c in node.named_children if c.type in ("scoped_identifier", "identifier")), "")
        if path:
            self.facts.imports.append(ImportDecl(path=path, static=static, wildcard=wildcard, line=_line(node)))

    # ------------------------------------------------------------------ declarations

    def _on_type_declaration(self, node: Node) -> None:
        name = _text(node.child_by_field_name("name"))
        outer = self._owner
        if outer is not None:
            fqn = f"{outer.fqn}.{name}"
        else:
            fqn = f"{self.facts.package}.{name}" if self.facts.package else name
        modifiers_node = next((c for c in node.named_children if c.type == "modifiers"), None)
        decl = TypeDecl(
            fqn=fqn, name=name, kind=TYPE_DECLARATIONS[node.type], package=self.facts.package,
            file=self.parsed.rel_path, line=_line(node), end_line=node.end_point[0] + 1,
            outer=outer.fqn if outer else None, is_test=self.parsed.is_test,
        )
        if modifiers_node is not None:
            for mod in modifiers_node.children:
                if mod.type in ("marker_annotation", "annotation"):
                    decl.annotations.append(_text(mod.child_by_field_name("name")))
                elif not mod.is_named:
                    decl.modifiers.append(_text(mod))
        self.facts.types.append(decl)

        body = node.child_by_field_name("body")
        decl.fields = self._collect_fields(node, body)

        saved_member, self._member = self._member, "<declaration>"
        self._type_stack.append((decl, node))
        class_scope: dict[str, object] = dict(decl.fields)
        self._class_scopes.append(class_scope)
        self._scopes.append(class_scope)
        if outer is not None:
            self._ref(outer.fqn, m.ENCLOSED_BY, node)
        try:
            if modifiers_node is not None:
                self._walk(modifiers_node)
            superclass = node.child_by_field_name("superclass")
            if superclass is not None:
                self._use_types(superclass, m.EXTENDS)
            interfaces = node.child_by_field_name("interfaces")
            if interfaces is not None:
                self._use_types(interfaces, m.IMPLEMENTS)
            for child in node.named_children:
                if child.type == "extends_interfaces":
                    self._use_types(child, m.EXTENDS)
                elif child.type == "type_parameters":
                    self._walk(child)
            if decl.kind == "record":
                self._member = "<field>"
                for param in (node.child_by_field_name("parameters") or node).named_children:
                    if param.type == "formal_parameter":
                        self._use_types(param.child_by_field_name("type"), m.FIELD)
            self._member = None
            self._walk(body)
        finally:
            self._scopes.pop()
            self._class_scopes.pop()
            self._type_stack.pop()
            self._member = saved_member

    def _collect_fields(self, decl_node: Node, body: Node | None) -> dict[str, str | None]:
        fields: dict[str, str | None] = {}
        if decl_node.type == "record_declaration":
            for param in (decl_node.child_by_field_name("parameters") or decl_node).named_children:
                if param.type == "formal_parameter":
                    fields[_text(param.child_by_field_name("name"))] = base_type_name(param.child_by_field_name("type"))
        if body is None:
            return fields
        members = list(body.named_children)
        for child in body.named_children:
            if child.type == "enum_body_declarations":
                members.extend(child.named_children)
        for member in members:
            if member.type in ("field_declaration", "constant_declaration"):
                type_name = base_type_name(member.child_by_field_name("type"))
                for declarator in member.children_by_field_name("declarator"):
                    fields[_text(declarator.child_by_field_name("name"))] = type_name
        if decl_node.type == "enum_declaration":
            for member in members:
                if member.type == "enum_constant":
                    fields[_text(member.child_by_field_name("name"))] = _text(decl_node.child_by_field_name("name"))
        return fields

    def _on_field_declaration(self, node: Node) -> None:
        saved, self._member = self._member, "<field>"
        for child in node.named_children:
            if child.type == "modifiers":
                self._walk(child)
        self._use_types(node.child_by_field_name("type"), m.FIELD)
        for declarator in node.children_by_field_name("declarator"):
            self._walk(declarator.child_by_field_name("value"))
        self._member = saved

    _on_constant_declaration = _on_field_declaration

    def _on_method_declaration(self, node: Node) -> None:
        owner_entry = self._type_stack[-1] if self._type_stack else None
        is_constructor = node.type in ("constructor_declaration", "compact_constructor_declaration")
        name = "<init>" if is_constructor else _text(node.child_by_field_name("name"))
        params = node.child_by_field_name("parameters")
        return_type = node.child_by_field_name("type")

        # Methods of anonymous classes are walked but not registered on the enclosing type.
        container = node.parent.parent if node.parent is not None else None
        if container is not None and container.type == "enum_body":
            container = container.parent
        if owner_entry is not None and container is not None and container.id == owner_entry[1].id:
            owner_entry[0].methods.append(MethodDecl(
                name=name, line=_line(node), end_line=node.end_point[0] + 1,
                parameter_types=[_text(p.child_by_field_name("type")) for p in (params.named_children if params else [])
                                 if p.type == "formal_parameter"],
                return_type=_text(return_type) or None,
            ))

        saved, self._member = self._member, name
        self._scopes.append({})
        try:
            for child in node.named_children:
                if child.type in ("modifiers", "type_parameters"):
                    self._walk(child)
                elif child.type == "throws":
                    self._use_types(child, m.TYPE_REFERENCE)
            self._use_types(return_type, m.RETURN_TYPE)
            if params is not None:
                self._walk(params)
            self._walk(node.child_by_field_name("body"))
        finally:
            self._scopes.pop()
            self._member = saved

    _on_constructor_declaration = _on_method_declaration
    _on_compact_constructor_declaration = _on_method_declaration
    _on_annotation_type_element_declaration = _on_method_declaration

    def _on_formal_parameter(self, node: Node) -> None:
        for child in node.named_children:
            if child.type == "modifiers":
                self._walk(child)
        type_node = node.child_by_field_name("type")
        self._use_types(type_node, m.PARAMETER)
        self._declare(_text(node.child_by_field_name("name")), base_type_name(type_node))

    def _on_spread_parameter(self, node: Node) -> None:
        type_node = next((c for c in node.named_children
                          if c.type not in ("modifiers", "variable_declarator", "marker_annotation", "annotation")), None)
        self._use_types(type_node, m.PARAMETER)
        for child in node.named_children:
            if child.type == "variable_declarator":
                self._declare(_text(child.child_by_field_name("name")), base_type_name(type_node))

    # ------------------------------------------------------------------ statements

    def _declare_typed(self, type_node: Node | None, names: list[str], value: Node | None) -> None:
        if type_node is not None and _text(type_node) == "var":
            inferred = None
            if value is not None and value.type == "object_creation_expression":
                inferred = base_type_name(value.child_by_field_name("type"))
            elif value is not None and value.type == "cast_expression":
                inferred = base_type_name(value.child_by_field_name("type"))
            for name in names:
                self._declare(name, inferred)
        else:
            for name in names:
                self._declare(name, base_type_name(type_node))

    def _on_local_variable_declaration(self, node: Node) -> None:
        for child in node.named_children:
            if child.type == "modifiers":
                self._walk(child)
        type_node = node.child_by_field_name("type")
        self._use_types(type_node, m.LOCAL_VARIABLE)
        for declarator in node.children_by_field_name("declarator"):
            value = declarator.child_by_field_name("value")
            self._walk(value)
            self._declare_typed(type_node, [_text(declarator.child_by_field_name("name"))], value)

    def _on_enhanced_for_statement(self, node: Node) -> None:
        self._scopes.append({})
        try:
            type_node = node.child_by_field_name("type")
            self._use_types(type_node, m.LOCAL_VARIABLE)
            self._walk(node.child_by_field_name("value"))
            self._declare_typed(type_node, [_text(node.child_by_field_name("name"))], None)
            self._walk(node.child_by_field_name("body"))
        finally:
            self._scopes.pop()

    def _on_resource(self, node: Node) -> None:
        type_node = node.child_by_field_name("type")
        if type_node is None:
            self._walk_children(node)
            return
        self._use_types(type_node, m.LOCAL_VARIABLE)
        value = node.child_by_field_name("value")
        self._walk(value)
        self._declare_typed(type_node, [_text(node.child_by_field_name("name"))], value)

    def _on_catch_formal_parameter(self, node: Node) -> None:
        catch_type = next((c for c in node.named_children if c.type == "catch_type"), None)
        self._use_types(catch_type, m.TYPE_REFERENCE)
        types = [base_type_name(c) for c in (catch_type.named_children if catch_type else [])]
        self._declare(_text(node.child_by_field_name("name")), types[0] if len(types) == 1 else None)

    def _on_instanceof_expression(self, node: Node) -> None:
        self._walk(node.child_by_field_name("left"))
        right = node.child_by_field_name("right")
        self._use_types(right, m.TYPE_REFERENCE)
        name = node.child_by_field_name("name")
        if name is not None:
            self._declare(_text(name), base_type_name(right))
        for child in node.named_children:
            if child.type in ("record_pattern", "type_pattern"):
                self._walk(child)

    # ------------------------------------------------------------------ expressions

    def _on_object_creation_expression(self, node: Node) -> None:
        type_node = node.child_by_field_name("type")
        self._use_types(type_node, m.INSTANTIATION)
        for child in node.named_children:
            if child.type == "class_body":
                self._scopes.append({})
                try:
                    self._walk(child)
                finally:
                    self._scopes.pop()
            elif type_node is None or child.id != type_node.id:
                self._walk(child)

    def _receiver(self, obj: Node | None) -> tuple[str | None, bool]:
        """Return (type name as written, is_static) for a method-call receiver expression."""
        if obj is None:
            return None, False
        if obj.type == "identifier":
            name = _text(obj)
            found = self._lookup(name)
            if found is not _UNKNOWN:
                return found, False  # type: ignore[return-value]
            return (name, True) if name[:1].isupper() else (None, False)
        if obj.type == "field_access":
            target = obj.child_by_field_name("object")
            field_name = _text(obj.child_by_field_name("field"))
            if target is not None and target.type == "this" and self._class_scopes:
                return self._class_scopes[-1].get(field_name), False  # type: ignore[return-value]
            text = re.sub(r"\s+", "", _text(obj))
            if re.fullmatch(r"[\w.]+", text) and field_name[:1].isupper():
                return text, True
            return None, False
        if obj.type == "object_creation_expression":
            return base_type_name(obj.child_by_field_name("type")), False
        if obj.type == "parenthesized_expression" and obj.named_children:
            return self._receiver(obj.named_children[0])
        if obj.type == "cast_expression":
            return base_type_name(obj.child_by_field_name("type")), False
        return None, False

    def _on_method_invocation(self, node: Node) -> None:
        obj = node.child_by_field_name("object")
        method = _text(node.child_by_field_name("name"))
        type_name, is_static = self._receiver(obj)
        if type_name:
            self._ref(type_name, m.STATIC_CALL if is_static else m.METHOD_CALL, node, detail=method)
        if not is_static:  # a static receiver is a type name, already recorded above
            self._walk(obj)
        for child in node.named_children:
            if child.type in ("argument_list", "type_arguments"):
                self._walk(child)

    def _on_field_access(self, node: Node) -> None:
        obj = node.child_by_field_name("object")
        if obj is not None and obj.type == "identifier":
            name = _text(obj)
            if self._lookup(name) is _UNKNOWN and name[:1].isupper():
                self._ref(name, m.STATIC_REFERENCE, node, detail=_text(node.child_by_field_name("field")))
                return
        self._walk(obj)

    def _on_method_reference(self, node: Node) -> None:
        if not node.named_children:
            return
        head = node.named_children[0]
        member = _text(node.named_children[-1]) if len(node.named_children) > 1 else "new"
        if head.type == "identifier" and self._lookup(_text(head)) is _UNKNOWN and _text(head)[:1].isupper():
            self._ref(_text(head), m.STATIC_REFERENCE, node, detail=member)
        elif head.type in ("type_identifier", "scoped_type_identifier", "generic_type", "array_type"):
            self._use_types(head, m.STATIC_REFERENCE)
        else:
            self._walk(head)

    def _on_marker_annotation(self, node: Node) -> None:
        self._ref(_text(node.child_by_field_name("name")), m.ANNOTATION, node)

    def _on_annotation(self, node: Node) -> None:
        self._ref(_text(node.child_by_field_name("name")), m.ANNOTATION, node)
        self._walk(node.child_by_field_name("arguments"))

    # Any type name not consumed by a more specific handler (casts, generics, X.class, bounds ...)
    def _on_type_identifier(self, node: Node) -> None:
        self._use_types(node, m.TYPE_REFERENCE)

    _on_scoped_type_identifier = _on_type_identifier

    def _on_scoped_identifier(self, node: Node) -> None:
        pass  # only appears in package/import names and annotation names


# The walker recurses once per syntax-tree level, and long expression chains (e.g. generated
# string concatenations) nest thousands of levels deep.
_RECURSION_LIMIT = 50_000


def analyze_file(parsed: ParsedFile) -> FileFacts:
    analyzer = JavaFileAnalyzer(parsed)
    previous = sys.getrecursionlimit()
    sys.setrecursionlimit(max(previous, _RECURSION_LIMIT))
    try:
        return analyzer.analyze()
    except RecursionError:
        # Keep what was collected and report the file alongside unparseable ones.
        analyzer.facts.has_syntax_errors = True
        return analyzer.facts
    finally:
        sys.setrecursionlimit(previous)
