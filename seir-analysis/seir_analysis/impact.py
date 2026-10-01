"""Module 5 - Impact Engine: compute the blast radius of changing or removing a component.

Starting from the selected component, a breadth-first search walks the graph *backwards*
(from a component to the components that depend on it). The BFS level of each component
is its propagation depth: 1 = direct dependent, 2+ = indirect dependent.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field

from . import models as m
from .graph import DependencyGraph

# Relationship kinds that point at concrete members of the target, used as call-site evidence.
_CALL_KINDS = {m.METHOD_CALL, m.STATIC_CALL, m.STATIC_REFERENCE, m.INSTANTIATION}


@dataclass
class ImpactReport:
    component: str
    name: str
    kind: str
    file: str
    direct_dependents: list[str]
    indirect_dependents: list[str]
    dependents_by_depth: dict[int, list[str]]
    impact_paths: dict[str, list[str]]
    dependencies: list[str]
    external_references: list[str]
    polymorphic_dependents: list[str]
    relationship_breakdown: dict[str, int]
    call_sites: list[dict]
    used_members: dict[str, int]
    cycle_members: list[str]
    affected_files: list[str]
    affected_packages: list[str]
    total_components: int
    max_depth_limit: int | None = None
    annotations: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    subgraph: dict = field(default_factory=dict)

    @property
    def affected_components(self) -> list[str]:
        return self.direct_dependents + self.indirect_dependents

    @property
    def max_dependency_depth(self) -> int:
        return max(self.dependents_by_depth, default=0)

    def to_dict(self, include_subgraph: bool = True) -> dict:
        data = {
            "component": self.component,
            "name": self.name,
            "kind": self.kind,
            "file": self.file,
            "annotations": self.annotations,
            "direct_dependents": self.direct_dependents,
            "indirect_dependents": self.indirect_dependents,
            "impact_size": len(self.affected_components),
            "max_dependency_depth": self.max_dependency_depth,
            "dependents_by_depth": {str(k): v for k, v in sorted(self.dependents_by_depth.items())},
            "impact_paths": self.impact_paths,
            "dependencies": self.dependencies,
            "external_references": self.external_references,
            "polymorphic_dependents": self.polymorphic_dependents,
            "relationship_breakdown": self.relationship_breakdown,
            "used_members": self.used_members,
            "call_sites": self.call_sites,
            "in_cycle": bool(self.cycle_members),
            "cycle_members": self.cycle_members,
            "affected_files": self.affected_files,
            "affected_packages": self.affected_packages,
            "max_depth_limit": self.max_depth_limit,
            "metrics": self.metrics,
        }
        if include_subgraph:
            data["subgraph"] = self.subgraph
        return data


class ImpactEngine:
    def __init__(self, graph: DependencyGraph) -> None:
        self.graph = graph

    def analyze(self, component: str, max_depth: int | None = None) -> ImpactReport:
        g = self.graph.g
        target = self.graph.resolve(component)

        # Reverse BFS. parent[x] = the next hop from x towards the target.
        depth: dict[str, int] = {target: 0}
        parent: dict[str, str] = {}
        queue = deque([target])
        while queue:
            current = queue.popleft()
            if max_depth is not None and depth[current] >= max_depth:
                continue
            for dependent in sorted(g.predecessors(current)):
                if dependent not in depth:
                    depth[dependent] = depth[current] + 1
                    parent[dependent] = current
                    queue.append(dependent)

        by_depth: dict[int, list[str]] = {}
        for node, d in depth.items():
            if d > 0:
                by_depth.setdefault(d, []).append(node)
        for nodes in by_depth.values():
            nodes.sort()
        affected = [n for n in depth if n != target]

        paths = {}
        for node in sorted(affected):
            chain = [node]
            while chain[-1] != target:
                chain.append(parent[chain[-1]])
            paths[node] = chain

        # Direct evidence: how each direct dependent uses the target.
        breakdown: Counter = Counter()
        call_sites, used_members = [], Counter()
        for dependent in by_depth.get(1, []):
            breakdown.update(self.graph.edge_kinds(dependent, target))
            for rel in self.graph.evidence(dependent, target):
                if rel.kind in _CALL_KINDS:
                    call_sites.append({"caller": dependent, "caller_member": rel.member, "kind": rel.kind,
                                       "target_member": rel.detail or "<init>", "file": rel.file, "line": rel.line})
                    used_members[rel.detail or "<init>"] += 1

        # Components that only know the target through one of its supertypes (e.g. an interface
        # it implements). They don't reference the target directly, but may be wired to it at runtime.
        # Sibling implementations (which only extend/implement the supertype) and types nested
        # inside the supertype are not consumers.
        polymorphic = set()
        for supertype in self.graph.supertypes(target):
            polymorphic.update(d for d in g.predecessors(supertype) if d not in depth and
                               set(self.graph.edge_kinds(d, supertype)) - {m.EXTENDS, m.IMPLEMENTS, m.IMPORT,
                                                                           m.ENCLOSED_BY})

        node = g.nodes[target]
        files = sorted({g.nodes[n]["file"] for n in affected})
        packages = sorted({g.nodes[n]["package"] for n in affected})
        externals = sorted(self.graph.external_references.get(target, ()))
        cycle = self.graph.cycle_containing(target)
        total = len(self.graph)

        report = ImpactReport(
            component=target, name=node["name"], kind=node["kind"], file=node["file"],
            direct_dependents=by_depth.get(1, []),
            indirect_dependents=sorted(n for n in affected if depth[n] > 1),
            dependents_by_depth=by_depth, impact_paths=paths,
            dependencies=self.graph.dependencies(target), external_references=externals,
            polymorphic_dependents=sorted(polymorphic),
            relationship_breakdown=dict(sorted(breakdown.items())),
            call_sites=sorted(call_sites, key=lambda c: (c["caller"], c["line"])),
            used_members=dict(used_members.most_common()),
            cycle_members=cycle, affected_files=files, affected_packages=packages,
            total_components=total, max_depth_limit=max_depth, annotations=list(node["annotations"]),
        )
        report.metrics = {
            # Flat numeric features for the risk model.
            "direct_dependent_count": len(report.direct_dependents),
            "indirect_dependent_count": len(report.indirect_dependents),
            "impact_size": len(affected),
            "max_dependency_depth": report.max_dependency_depth,
            "fan_in": g.in_degree(target),
            "fan_out": g.out_degree(target),
            "external_reference_count": len(externals),
            "polymorphic_dependent_count": len(polymorphic),
            "call_site_count": len(call_sites),
            "affected_file_count": len(files),
            "affected_package_count": len(packages),
            "impact_ratio": round(len(affected) / (total - 1), 4) if total > 1 else 0.0,
            "in_cycle": int(bool(cycle)),
            "inheritance_dependents": sum(1 for d in report.direct_dependents
                                          if {m.EXTENDS, m.IMPLEMENTS} & set(self.graph.edge_kinds(d, target))),
            "loc": node["loc"],
            "method_count": node["methods"],
            "is_deprecated": int("Deprecated" in node["annotations"]),
        }
        report.subgraph = self.graph.to_dict(set(depth))
        return report
