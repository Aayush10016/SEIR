from pathlib import Path

import pytest

from seir_analysis import analyze_repository, analyze_sources

SAMPLE_REPO = Path(__file__).resolve().parent.parent / "samples" / "shop"


@pytest.fixture(scope="session")
def shop():
    return analyze_repository(SAMPLE_REPO)


@pytest.fixture
def edges():
    """Analyse in-memory sources and return {(source, target): {kinds}} with short names."""
    def _run(sources: dict[str, str]):
        analysis = analyze_sources(sources)
        result: dict[tuple[str, str], set[str]] = {}
        for rel in analysis.extraction.relationships:
            result.setdefault((rel.source, rel.target), set()).add(rel.kind)
        return result, analysis
    return _run
