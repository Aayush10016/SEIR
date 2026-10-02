"""Module 1 - Repository Parser: find Java source files and parse them into syntax trees."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import tree_sitter_java
from tree_sitter import Language, Parser, Tree

JAVA_LANGUAGE = Language(tree_sitter_java.language())

# Directories that never contain first-party source worth analysing (dot-directories are skipped too).
EXCLUDED_DIRS = {"node_modules", "__pycache__"}
# Build-tool output directories. Only skipped next to a build file or at the repository root, so
# that Java packages with the same names (e.g. `com.acme.build`) are still analysed.
BUILD_OUTPUT_DIRS = {"target", "build", "out", "bin"}
BUILD_FILES = {"pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "build.xml"}
TEST_DIR_NAMES = {"test", "tests", "androidTest", "testFixtures", "integrationTest"}


@dataclass
class ParsedFile:
    path: Path               # absolute path
    rel_path: str            # repository-relative, forward slashes
    source: bytes
    tree: Tree
    is_test: bool

    @property
    def has_syntax_errors(self) -> bool:
        return self.tree.root_node.has_error


def is_test_path(rel_path: str) -> bool:
    parts = rel_path.split("/")
    return any(p in TEST_DIR_NAMES for p in parts[:-1]) or parts[-1].endswith(("Test.java", "Tests.java", "IT.java"))


def find_java_files(root: Path, include_tests: bool = False) -> list[Path]:
    root = Path(root)
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        is_project_dir = Path(dirpath) == root or not BUILD_FILES.isdisjoint(filenames)
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")
                             and not (is_project_dir and d in BUILD_OUTPUT_DIRS))
        for name in sorted(filenames):
            if not name.endswith(".java") or name in ("package-info.java", "module-info.java"):
                continue
            path = Path(dirpath) / name
            if include_tests or not is_test_path(path.relative_to(root).as_posix()):
                found.append(path)
    return found


class RepositoryParser:
    def __init__(self) -> None:
        self._parser = Parser(JAVA_LANGUAGE)

    def parse_source(self, source: bytes, rel_path: str = "<memory>.java") -> ParsedFile:
        return ParsedFile(
            path=Path(rel_path),
            rel_path=rel_path,
            source=source,
            tree=self._parser.parse(source),
            is_test=is_test_path(rel_path),
        )

    def parse_file(self, path: Path, root: Path) -> ParsedFile:
        parsed = self.parse_source(path.read_bytes(), path.relative_to(root).as_posix())
        parsed.path = path
        return parsed

    def parse_repository(self, root: str | os.PathLike, include_tests: bool = False) -> list[ParsedFile]:
        root = Path(root).resolve()
        if not root.is_dir():
            raise NotADirectoryError(f"Repository path does not exist or is not a directory: {root}")
        return [self.parse_file(p, root) for p in find_java_files(root, include_tests)]
