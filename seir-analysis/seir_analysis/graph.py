"""Module 4 - Graph Builder: turn relationships into a queryable dependency graph.

Edge direction: `A -> B` means "A depends on B". Change impact therefore flows
*against* the edges: if B changes, its predecessors (A) are affected.
"""

from __future__ import annotations

import difflib
from collections import Counter

import networkx as nx

from .extractor import ExtractionResult
from .models import Relationship, TypeDecl


class ComponentNotFoundError(LookupError):
    def __init__(self, query: str, suggestions: list[str]) -> None:
        self.query, self.suggestions = query, suggestions
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        super().__init__(f"No component matches '{query}'.{hint}")


class AmbiguousComponentError(LookupError):
    def __init__(self, query: str, candidates: list[str]) -> None:
        self.query, self.candidates = query, candidates
        super().__init__(f"'{query}' matches several components; use a fully-qualified name: {', '.join(candidates)}")


class DependencyGraph:
    def __init__(self, extraction: ExtractionResult) -> None:
        self.types: dict[str, TypeDecl] = extraction.types
        self.external_references = extraction.external_references
        self.g = nx.DiGraph()

        for fqn, decl in self.types.items():
            self.g.add_node(fqn, name=decl.name, kind=decl.kind, package=decl.package, file=decl.file,
                            line=decl.line, loc=decl.loc, is_test=decl.is_test,
                            annotations=list(decl.annotations), methods=len(decl.methods))
        for rel in extraction.relationships:
            if not self.g.has_edge(rel.source, rel.target):
                self.g.add_edge(rel.source, rel.target, kinds=Counter(), evidence=[])
            edge = self.g.edges[rel.source, rel.target]
            edge["kinds"][rel.kind] += 1
            edge["evidence"].append(rel)

    # ------------------------------------------------------------------ lookup

    def __contains__(self, fqn: str) -> bool:
        return fqn in self.g

    def __len__(self) -> int:
        return self.g.number_of_nodes()

    def resolve(self, query: str) -> str:
        """Find a component by FQN, simple name, nested name, or file path."""
        q = query.strip().replace("\\", "/")
        if q in self.g:
            return q
        if q.endswith(".java"):
            stem = q.rsplit("/", 1)[-1][:-5]
            matches = [f for f, d in self.types.items()
                       if d.outer is None and (d.file == q or d.file.endswith("/" + q) or q.endswith("/" + d.file) or
                                               (("/" not in q) and d.file.rsplit("/", 1)[-1] == q))]
            primary = [f for f in matches if self.types[f].name == stem]
            matches = primary or matches
        else:
            matches = [f for f in self.types if f.endswith("." + q)] or \
                      [f for f, d in self.types.items() if d.name.lower() == q.lower()]
        if len(matches) == 1:
            return matches[0]
        if matches:
            raise AmbiguousComponentError(query, sorted(matches))
        names = {d.name for d in self.types.values()}
        close = difflib.get_close_matches(q.removesuffix(".java").rsplit(".", 1)[-1], names, n=3, cutoff=0.6)
        raise ComponentNotFoundError(query, sorted(f for f, d in self.types.items() if d.name in close))

    # ------------------------------------------------------------------ structure

    def dependents(self, fqn: str) -> list[str]:
        """Components that directly depend on `fqn` (who breaks if it changes)."""
        return sorted(self.g.predecessors(fqn))

    def dependencies(self, fqn: str) -> list[str]:
        """Components `fqn` directly depends on."""
        return sorted(self.g.successors(fqn))

    def edge_kinds(self, source: str, target: str) -> dict[str, int]:
        return dict(self.g.edges[source, target]["kinds"])

    def evidence(self, source: str, target: str) -> list[Relationship]:
        return list(self.g.edges[source, target]["evidence"])

    def supertypes(self, fqn: str) -> list[str]:
        return sorted(t for t in self.g.successors(fqn)
                      if {"extends", "implements"} & set(self.g.edges[fqn, t]["kinds"]))

    def _cycle_view(self) -> nx.DiGraph:
        # An outer type using its own nested type is not a meaningful cycle, so ignore
        # edges that exist only because a type is nested inside another.
        return nx.subgraph_view(self.g, filter_edge=lambda s, t: set(self.g.edges[s, t]["kinds"]) != {"enclosed_by"})

    def cycles(self) -> list[list[str]]:
        """Strongly connected groups of 2+ components (mutual dependencies)."""
        return sorted((sorted(c) for c in nx.strongly_connected_components(self._cycle_view()) if len(c) > 1),
                      key=lambda c: (-len(c), c))

    def cycle_containing(self, fqn: str) -> list[str]:
        return next((c for c in self.cycles() if fqn in c), [])

    def package_dependencies(self) -> dict[tuple[str, str], int]:
        weights: Counter = Counter()
        for s, t, data in self.g.edges(data=True):
            ps, pt = self.g.nodes[s]["package"], self.g.nodes[t]["package"]
            if ps != pt:
                weights[(ps, pt)] += sum(data["kinds"].values())
        return dict(weights)

    def component_metrics(self) -> list[dict]:
        rows = []
        for fqn in sorted(self.g):
            node = self.g.nodes[fqn]
            rows.append({
                "component": fqn, "name": node["name"], "kind": node["kind"], "file": node["file"],
                "fan_in": self.g.in_degree(fqn), "fan_out": self.g.out_degree(fqn),
                "transitive_dependents": len(nx.ancestors(self.g, fqn)),
                "external_references": len(self.external_references.get(fqn, ())), "loc": node["loc"],
            })
        return rows

    # ------------------------------------------------------------------ export

    def to_dict(self, nodes: set[str] | None = None) -> dict:
        """Nodes/edges JSON for the backend and frontend visualisation."""
        keep = set(self.g) if nodes is None else nodes
        return {
            "nodes": [{"id": n, "label": self.g.nodes[n]["name"], "kind": self.g.nodes[n]["kind"],
                       "package": self.g.nodes[n]["package"], "file": self.g.nodes[n]["file"],
                       "is_test": self.g.nodes[n]["is_test"],
                       "annotations": self.g.nodes[n]["annotations"]} for n in sorted(keep)],
            "edges": [{"source": s, "target": t, "kinds": dict(d["kinds"]), "weight": sum(d["kinds"].values())}
                      for s, t, d in sorted(self.g.edges(data=True), key=lambda e: (e[0], e[1]))
                      if s in keep and t in keep],
        }

    def to_mermaid(self, nodes: set[str] | None = None, highlight: str | None = None) -> str:
        keep = set(self.g) if nodes is None else nodes
        ids = {n: f"n{i}" for i, n in enumerate(sorted(keep))}
        lines = ["graph LR"]
        for n, nid in ids.items():
            lines.append(f'    {nid}["{self.g.nodes[n]["name"]}"]')
        for s, t, d in sorted(self.g.edges(data=True), key=lambda e: (e[0], e[1])):
            if s in keep and t in keep:
                label = ", ".join(sorted(d["kinds"]))
                lines.append(f"    {ids[s]} -->|{label}| {ids[t]}")
        if highlight in ids:
            lines.append(f"    style {ids[highlight]} fill:#f96,stroke:#333,stroke-width:2px")
        return "\n".join(lines)

    def to_dot(self, nodes: set[str] | None = None) -> str:
        keep = set(self.g) if nodes is None else nodes
        lines = ["digraph dependencies {", "  rankdir=LR;", "  node [shape=box];"]
        for n in sorted(keep):
            lines.append(f'  "{n}" [label="{self.g.nodes[n]["name"]}"];')
        for s, t, d in sorted(self.g.edges(data=True), key=lambda e: (e[0], e[1])):
            if s in keep and t in keep:
                lines.append(f'  "{s}" -> "{t}" [label="{", ".join(sorted(d["kinds"]))}"];')
        lines.append("}")
        return "\n".join(lines)
