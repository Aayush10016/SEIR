"""SEIR Software Analysis module: static dependency analysis and change-impact (blast radius)."""

from .graph import AmbiguousComponentError, ComponentNotFoundError, DependencyGraph
from .impact import ImpactEngine, ImpactReport
from .pipeline import SoftwareAnalysis, analyze_repository, analyze_sources

__all__ = [
    "AmbiguousComponentError", "ComponentNotFoundError", "DependencyGraph", "ImpactEngine",
    "ImpactReport", "SoftwareAnalysis", "analyze_repository", "analyze_sources",
]
__version__ = "0.1.0"
