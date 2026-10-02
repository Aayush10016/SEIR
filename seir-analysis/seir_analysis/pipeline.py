"""Public entry point: run all five stages over a repository."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .ast_analyzer import analyze_file
from .extractor import ExtractionResult, extract_dependencies
from .graph import DependencyGraph
from .impact import ImpactEngine, ImpactReport
from .models import FileFacts
from .repository import RepositoryParser


@dataclass
class SoftwareAnalysis:
    root: Path
    files: list[FileFacts]
    extraction: ExtractionResult
    graph: DependencyGraph

    @property
    def files_with_syntax_errors(self) -> list[str]:
        return [f.path for f in self.files if f.has_syntax_errors]

    def impact(self, component: str, max_depth: int | None = None) -> ImpactReport:
        return ImpactEngine(self.graph).analyze(component, max_depth=max_depth)

    def summary(self, top: int = 10) -> dict:
        metrics = self.graph.component_metrics()
        return {
            "repository": str(self.root),
            "files_analyzed": len(self.files),
            "files_with_syntax_errors": self.files_with_syntax_errors,
            "components": len(self.graph),
            "relationships": len(self.extraction.relationships),
            "dependency_edges": self.graph.g.number_of_edges(),
            "packages": len({t.package for t in self.extraction.types.values()}),
            "most_depended_on": [
                {"component": r["component"], "fan_in": r["fan_in"], "transitive_dependents": r["transitive_dependents"]}
                for r in sorted(metrics, key=lambda r: (-r["transitive_dependents"], -r["fan_in"], r["component"]))[:top]
            ],
            "unreferenced_components": [r["component"] for r in metrics if r["fan_in"] == 0],
            "dependency_cycles": self.graph.cycles(),
        }


def analyze_repository(root: str | os.PathLike, include_tests: bool = False) -> SoftwareAnalysis:
    parsed = RepositoryParser().parse_repository(root, include_tests=include_tests)
    files = [analyze_file(p) for p in parsed]
    extraction = extract_dependencies(files)
    return SoftwareAnalysis(root=Path(root).resolve(), files=files, extraction=extraction,
                            graph=DependencyGraph(extraction))


def analyze_sources(sources: dict[str, str]) -> SoftwareAnalysis:
    """Analyse in-memory sources ({relative path: Java code}); handy for tests and APIs."""
    parser = RepositoryParser()
    files = [analyze_file(parser.parse_source(code.encode("utf-8"), path)) for path, code in sources.items()]
    extraction = extract_dependencies(files)
    return SoftwareAnalysis(root=Path("<memory>"), files=files, extraction=extraction,
                            graph=DependencyGraph(extraction))
