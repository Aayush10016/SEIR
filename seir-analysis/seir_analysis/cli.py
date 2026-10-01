"""Command-line interface: `python -m seir_analysis <command> ...`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .graph import AmbiguousComponentError, ComponentNotFoundError
from .pipeline import analyze_repository


def _emit(text: str, out: str | None) -> None:
    if out:
        Path(out).write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {out}", file=sys.stderr)
    else:
        print(text)


def _cmd_scan(args) -> int:
    analysis = analyze_repository(args.repo, include_tests=args.include_tests)
    data = analysis.summary(top=args.top)
    if args.graph:
        data["graph"] = analysis.graph.to_dict()
    _emit(json.dumps(data, indent=2), args.out)
    return 0


def _cmd_impact(args) -> int:
    analysis = analyze_repository(args.repo, include_tests=args.include_tests)
    try:
        report = analysis.impact(args.component, max_depth=args.max_depth)
    except (ComponentNotFoundError, AmbiguousComponentError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "mermaid":
        nodes = {report.component, *report.affected_components}
        _emit(analysis.graph.to_mermaid(nodes, highlight=report.component), args.out)
    else:
        _emit(json.dumps(report.to_dict(include_subgraph=not args.no_subgraph), indent=2), args.out)
    return 0


def _cmd_list(args) -> int:
    analysis = analyze_repository(args.repo, include_tests=args.include_tests)
    rows = sorted(analysis.graph.component_metrics(), key=lambda r: (-r["transitive_dependents"], r["component"]))
    if args.format == "json":
        _emit(json.dumps(rows, indent=2), args.out)
        return 0
    width = max((len(r["component"]) for r in rows), default=9)
    lines = [f"{'COMPONENT':<{width}}  KIND        FAN-IN  FAN-OUT  BLAST  EXT", "-" * (width + 42)]
    for r in rows:
        lines.append(f"{r['component']:<{width}}  {r['kind']:<10}  {r['fan_in']:>6}  {r['fan_out']:>7}  "
                     f"{r['transitive_dependents']:>5}  {r['external_references']:>3}")
    _emit("\n".join(lines), args.out)
    return 0


def _cmd_graph(args) -> int:
    analysis = analyze_repository(args.repo, include_tests=args.include_tests)
    graph = analysis.graph
    text = {"json": lambda: json.dumps(graph.to_dict(), indent=2),
            "mermaid": graph.to_mermaid, "dot": graph.to_dot}[args.format]()
    _emit(text, args.out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seir-analysis",
                                     description="SEIR Software Analysis: dependency graph and change-impact analysis for Java.")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("repo", help="path to the repository root")
        p.add_argument("--include-tests", action="store_true", help="also analyse test sources")
        p.add_argument("-o", "--out", help="write output to a file instead of stdout")

    p = sub.add_parser("scan", help="summarise the repository's structure")
    common(p)
    p.add_argument("--top", type=int, default=10, help="how many most-depended-on components to list")
    p.add_argument("--graph", action="store_true", help="include the full dependency graph")
    p.set_defaults(func=_cmd_scan)

    p = sub.add_parser("impact", help="blast radius of changing/removing a component")
    common(p)
    p.add_argument("component", help="FQN, simple class name, or .java file path")
    p.add_argument("--max-depth", type=int, help="stop propagating after this many hops")
    p.add_argument("--format", choices=["json", "mermaid"], default="json")
    p.add_argument("--no-subgraph", action="store_true", help="omit the subgraph from JSON output")
    p.set_defaults(func=_cmd_impact)

    p = sub.add_parser("list", help="list components with coupling metrics")
    common(p)
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.set_defaults(func=_cmd_list)

    p = sub.add_parser("graph", help="export the dependency graph")
    common(p)
    p.add_argument("--format", choices=["json", "mermaid", "dot"], default="json")
    p.set_defaults(func=_cmd_graph)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except NotADirectoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
