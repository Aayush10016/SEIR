# seir-analysis — SEIR Software Analysis

Static analysis of a Java repository that answers:
**"If this component changes or is removed, what else could break?"**

It parses the source, extracts dependencies between classes, builds a dependency graph,
and computes the *blast radius* of a change. Its JSON output is the structural evidence
used by SEIR's risk model, AI explanation, backend, and frontend.

```
Repository ─► Repository Parser ─► AST Analyzer ─► Dependency Extractor ─► Graph Builder ─► Impact Engine ─► JSON
              repository.py        ast_analyzer.py  extractor.py           graph.py         impact.py
```

| Module | File | Does |
|---|---|---|
| 1. Repository Parser | `seir_analysis/repository.py` | Finds `.java` files (skips build dirs, tests by default) and parses them with tree-sitter |
| 2. AST Analyzer | `seir_analysis/ast_analyzer.py` | Walks each syntax tree: declarations, methods, fields, imports, and every type reference with its kind, line and enclosing method |
| 3. Dependency Extractor | `seir_analysis/extractor.py` | Resolves names to fully-qualified classes using Java's lookup rules (nested → single import → same package → wildcard → FQN); splits internal vs external (library) references |
| 4. Graph Builder | `seir_analysis/graph.py` | `networkx` graph; edge `A → B` = "A depends on B", with per-kind counts and line-level evidence. Exports JSON / Mermaid / DOT |
| 5. Impact Engine | `seir_analysis/impact.py` | Reverse BFS from the selected component: direct + indirect dependents, depth, propagation paths, call sites, metrics |

## Setup

All commands below are run from this `seir-analysis/` folder.

```bash
cd seir-analysis
pip install -r requirements.txt      # tree-sitter, tree-sitter-java, networkx, pytest
python -m pytest                     # 31 tests (Python 3.11+)
```

## Usage

### CLI

```bash
# Blast radius of a component (FQN, simple name, or .java path)
python -m seir_analysis impact samples/shop LegacyPaymentService
python -m seir_analysis impact samples/shop src/main/java/com/shop/order/OrderService.java --max-depth 2
python -m seir_analysis impact samples/shop PaymentService --format mermaid   # diagram of the affected subgraph

# Repository overview: most depended-on components, unreferenced components, cycles
python -m seir_analysis scan samples/shop

# Every component with fan-in / fan-out / transitive dependents
python -m seir_analysis list samples/shop

# Full graph for the frontend
python -m seir_analysis graph samples/shop --format json -o graph.json
```

Common flags: `--include-tests` (analyse test sources too), `-o FILE` (write to file).

### Python (for the backend)

```python
from seir_analysis import analyze_repository

analysis = analyze_repository("path/to/repo")       # parse + build graph once, reuse for many queries
report = analysis.impact("PaymentService")          # raises ComponentNotFoundError / AmbiguousComponentError
payload = report.to_dict()                          # JSON-serialisable
features = report.metrics                           # flat numeric features for the risk model
graph_json = analysis.graph.to_dict()               # whole graph: {"nodes": [...], "edges": [...]}
```

## Output contract (`impact`)

> **Terminology.** *Dependencies* of X are what X uses. *Dependents* of X are what uses X.
> Change impact flows to **dependents**, so the blast radius is made of dependents.

Example: removing `LegacyPaymentService` in `samples/shop` (trimmed):

```json
{
  "component": "com.shop.payment.LegacyPaymentService",
  "annotations": ["Deprecated"],
  "direct_dependents": ["com.shop.jobs.ReconciliationJob", "com.shop.payment.PaymentService"],
  "indirect_dependents": ["com.shop.api.OrderController", "com.shop.api.PaymentController",
                          "com.shop.notify.NotificationService", "com.shop.order.OrderService"],
  "impact_size": 6,
  "max_dependency_depth": 3,
  "dependents_by_depth": {"1": ["..."], "2": ["..."], "3": ["..."]},
  "impact_paths": {
    "com.shop.api.OrderController": ["com.shop.api.OrderController", "com.shop.order.OrderService",
                                     "com.shop.payment.PaymentService", "com.shop.payment.LegacyPaymentService"]
  },
  "polymorphic_dependents": ["com.shop.jobs.AuditJob"],
  "call_sites": [
    {"caller": "com.shop.jobs.ReconciliationJob", "caller_member": "run", "kind": "static_call",
     "target_member": "reconcileAll", "file": "src/main/java/com/shop/jobs/ReconciliationJob.java", "line": 9}
  ],
  "metrics": {"direct_dependent_count": 2, "indirect_dependent_count": 4, "impact_size": 6,
              "max_dependency_depth": 3, "fan_in": 2, "fan_out": 3, "impact_ratio": 0.3333,
              "in_cycle": 0, "is_deprecated": 1, "...": "..."},
  "subgraph": {"nodes": ["..."], "edges": ["..."]}
}
```

| Field | Meaning |
|---|---|
| `direct_dependents` | Components that reference the target directly (depth 1) |
| `indirect_dependents` | Components reached through a chain of 2+ dependencies |
| `impact_size` | `len(direct) + len(indirect)` |
| `max_dependency_depth` | Longest shortest-path from any affected component to the target |
| `dependents_by_depth` | Affected components grouped by hop count |
| `impact_paths` | For each affected component, one shortest dependency chain to the target (explains *why* it is affected) |
| `dependencies` | What the target itself uses (upstream; not part of the blast radius) |
| `external_references` | Library / JDK types the target uses (`java.util.List`, `org.springframework...`) |
| `polymorphic_dependents` | Components that use an interface/superclass of the target without naming the target itself. They are not in the blast radius but may be wired to it at runtime (e.g. dependency injection) |
| `relationship_breakdown` | How direct dependents use the target: counts per relationship kind |
| `call_sites` / `used_members` | Exact file/line/method where direct dependents call, instantiate, or statically reference the target's members |
| `in_cycle` / `cycle_members` | Whether the target is part of a mutual-dependency cycle |
| `affected_files` / `affected_packages` | Files and packages containing affected components |
| `metrics` | Flat numeric features for the risk model (all ints/floats) |
| `subgraph` | Nodes and edges of the target and its affected components, ready for visualisation |

Relationship kinds: `extends`, `implements`, `field`, `parameter`, `return_type`, `local_variable`,
`instantiation`, `method_call`, `static_call`, `static_reference`, `annotation`, `type_reference`
(generics, casts, `instanceof`, `throws`/`catch`, `X.class`), `import`, `enclosed_by` (nested class → outer class).

## How it feeds the other SEIR modules

| Consumer | Uses |
|---|---|
| AI/ML risk model | `metrics` |
| AI evidence / explanation | `impact_paths`, `call_sites`, `relationship_breakdown`, `annotations` |
| Backend | `analyze_repository()` once per repo/commit, then `impact()` per request; everything is JSON-serialisable |
| Frontend | `subgraph` (impact view) or `graph.to_dict()` (whole repo) |

## Validation

- `samples/shop` is a small Spring-style app built to exercise every feature. It includes an interface with two implementations, records, `var`, static calls, nested types, a dependency cycle, an unreferenced class and a test file.
- Smoke-tested on real projects:
  - **spring-petclinic**: 25 files, 0 parse errors.
  - **apache/commons-lang**: 246 files, 377 types, 2,910 relationships, 0 parse errors, about 0.75 s warm.

## Known limitations

Static analysis without a compiler means:

- **Granularity is class-level.** Method-level calls are kept as *evidence* (`call_sites`), not as graph nodes.
- **Reflection, dependency injection and config wiring are invisible.** Examples: `Class.forName`, Spring beans created from XML or properties. `polymorphic_dependents` partially covers DI through interfaces; the Configuration and Runtime Analysis modules cover the rest.
- **Some receiver types are not inferred.**
  - Covered: fields, `this.field`, parameters, locals, `var x = new T()`, casts, `new T().m()`.
  - Not covered: chained calls (`a.getB().c()`), inherited fields, and lambda parameters without declared types. A class still shows up as a dependent through its field/parameter/import edges, but the specific call site may be missing.
- **Names only resolve against the analysed repository.** Classes in other modules or repositories show up as external references.
- **Java only.**
