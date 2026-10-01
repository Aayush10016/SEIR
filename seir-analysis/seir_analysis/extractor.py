"""Module 3 - Dependency Extractor: resolve raw type names into repository-wide relationships.

Resolution follows Java's own lookup order as closely as is possible without a compiler:
nested types of the enclosing class -> single-type imports -> same package ->
on-demand (wildcard) imports -> fully-qualified names. Anything that resolves to a type
declared in the repository becomes an internal `Relationship`; anything that resolves to
an imported, non-repository type is recorded as an external reference.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from . import models as m
from .models import FileFacts, Relationship, TypeDecl


@dataclass
class ExtractionResult:
    types: dict[str, TypeDecl]
    relationships: list[Relationship]
    external_references: dict[str, set[str]] = field(default_factory=dict)   # type FQN -> external names
    unresolved: dict[str, int] = field(default_factory=dict)                 # name -> occurrences


class _FileScope:
    """What a single compilation unit can see by simple name."""

    def __init__(self, facts: FileFacts, known: dict[str, TypeDecl]) -> None:
        self.facts = facts
        self.known = known
        self.single: dict[str, str] = {}          # simple name -> FQN (internal or external)
        self.on_demand: list[str] = []            # package / type prefixes from `import x.*`
        for imp in facts.imports:
            if imp.static:
                # `import static a.B.member` / `import static a.B.*` make B a compile-time dependency
                # but do not bring B's simple name into scope.
                continue
            if imp.wildcard:
                self.on_demand.append(imp.path)
            else:
                self.single[imp.path.rsplit(".", 1)[-1]] = imp.path

    def resolve(self, name: str, owner: str) -> tuple[str | None, bool]:
        """Return (fqn, is_internal). fqn is None when the name cannot be identified."""
        name = name.strip()
        if not name:
            return None, False
        if "." in name:
            if name in self.known:
                return name, True
            head, rest = name.split(".", 1)
            head_fqn, internal = self.resolve(head, owner)
            if head_fqn and internal:
                candidate = f"{head_fqn}.{rest}"
                return (candidate, True) if candidate in self.known else (head_fqn, True)
            if head_fqn:
                return f"{head_fqn}.{rest}", False
            if head[:1].islower():           # looks fully qualified: com.vendor.Thing
                return name, False
            return None, False

        # 1. member types of the enclosing type and its outer types
        scope = owner
        while scope:
            candidate = f"{scope}.{name}"
            if candidate in self.known:
                return candidate, True
            scope = self.known[scope].outer if scope in self.known else None
        # 2. single-type imports
        if name in self.single:
            fqn = self.single[name]
            return fqn, fqn in self.known
        # 3. same package
        package = self.facts.package
        candidate = f"{package}.{name}" if package else name
        if candidate in self.known:
            return candidate, True
        # 4. on-demand imports
        for prefix in self.on_demand:
            candidate = f"{prefix}.{name}"
            if candidate in self.known:
                return candidate, True
        return None, False


def _static_import_target(path: str, wildcard: bool, known: dict[str, TypeDecl]) -> str | None:
    if wildcard:
        return path if path in known else None
    owner = path.rsplit(".", 1)[0]
    if owner in known:
        return owner
    return path if path in known else None


def extract_dependencies(files: list[FileFacts]) -> ExtractionResult:
    known: dict[str, TypeDecl] = {}
    for facts in files:
        for decl in facts.types:
            known.setdefault(decl.fqn, decl)

    relationships: set[Relationship] = set()
    externals: dict[str, set[str]] = defaultdict(set)
    unresolved: dict[str, int] = defaultdict(int)

    for facts in files:
        scope = _FileScope(facts, known)
        top_level = [t.fqn for t in facts.types if t.outer is None]

        for ref in facts.references:
            fqn, internal = scope.resolve(ref.name, ref.owner)
            if fqn is None:
                unresolved[ref.name] += 1
            elif not internal:
                externals[ref.owner].add(fqn)
            elif fqn != ref.owner:
                relationships.add(Relationship(
                    source=ref.owner, target=fqn, kind=ref.kind, file=facts.path,
                    line=ref.line, member=ref.member, detail=ref.detail))

        # Imports are file-level: attribute them to every top-level type in the file.
        for imp in facts.imports:
            if imp.static:
                target = _static_import_target(imp.path, imp.wildcard, known)
            else:
                target = None if imp.wildcard else (imp.path if imp.path in known else None)
            if target is not None:
                for owner in top_level:
                    if owner != target:
                        relationships.add(Relationship(
                            source=owner, target=target, kind=m.IMPORT, file=facts.path,
                            line=imp.line, detail="static" if imp.static else None))
            else:
                is_internal_package = imp.wildcard and any(
                    t.package == imp.path or t.fqn == imp.path for t in known.values())
                if not is_internal_package and not imp.path.startswith("java.lang."):
                    for owner in top_level:
                        externals[owner].add(imp.path + (".*" if imp.wildcard else ""))

    ordered = sorted(relationships, key=lambda r: (r.source, r.target, r.file, r.line, r.kind, r.detail or ""))
    return ExtractionResult(types=known, relationships=ordered,
                            external_references=dict(externals), unresolved=dict(unresolved))
