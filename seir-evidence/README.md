# seir-evidence — SEIR Evidence & Evolution (Member 5)

Collects the evidence that source-code analysis alone cannot see — **Git history** and
**configuration files** (runtime usage is next) — and turns repository history into the
**labelled dataset** the risk model is trained on. It also owns the team's **shared contracts**
and the **shared feature function** used by the risk model.

```
Repository ─► History reader ─► Git evidence ────────┐
  (git)       git_log.py         git_history.py      ├─► EvidenceItem (shared contract) ─► backend / risk model / explainer
          └─► Config scanner ─────────────────────────┘
              config_files.py
                                         │
                      history + labels   ▼
                 dataset/ ─► cases.parquet ─► seir_features ─► risk model (seir-risk)
```

| Part | Where | Does |
|---|---|---|
| Shared contracts | `app/schema/` → exported to `../contracts/` | `Component`, `DependencyEdge`, `EvidenceItem`, `ChangeCase`, `RiskAssessment`, `Explanation` (Pydantic + JSON Schema) |
| Git evidence | `app/collectors/git_log.py`, `git_history.py` | One-pass `git log`, rename-aware; 9 history features per class **as of any moment**, plus co-change edges |
| Configuration evidence | `app/collectors/config_files.py` | Finds classes named in runtime / test / build configuration at any commit; flags stale references |
| Pipeline | `app/pipeline.py` | `analyze_repository()`: all evidence for one repository snapshot |
| Dataset | `app/dataset/` | Change cases, SZZ bug tracing, `labels@1.0`, leakage-safe features, splits, quality report |
| Shared features | `seir_features/` | `evidence_to_features()` — the ONE evidence → model-input conversion, used by the dataset **and** the risk model |

## Setup

All commands below are run from this `seir-evidence/` folder. Python 3.11+, Git on the PATH.

```bash
python -m venv .venv
.venv/Scripts/activate                  # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
python -m pytest                        # 140 tests
```

## Usage

```bash
# Evidence for a repository (clones into workspace/, writes JSON into data/<repo>/<snapshot>/)
python -m scripts.run_analysis https://github.com/spring-projects/spring-petclinic
python -m scripts.run_analysis https://github.com/spring-projects/spring-petclinic --ref <commit>

# Training dataset for the risk model (repositories listed and pinned in corpus.yaml; ~10 min)
python -m scripts.build_dataset --version v4

# Regenerate ../contracts/schemas after changing app/schema
python -m scripts.export_schemas
```

Verification and manual review (Data & Evolution report §5, §6, §10):

| Command | Purpose |
|---|---|
| `python -m scripts.verify_git_history <url> --sample 20` | Git features vs independent `git log` queries, repeatability, lower-bound check |
| `python -m scripts.sample_szz_links --version v4` | 30 "this change caused that bug" links to review by hand |
| `python -m scripts.evaluate_szz_review <csv>` | SZZ precision with a 95 % interval |
| `python -m scripts.review_config_references <url> [--ref …]` | Configuration references + candidate misses to review by hand |
| `python -m scripts.evaluate_config_review <csv> …` | Configuration precision, recall, unresolved rate |

Tunable numbers live in `app/config.py` and can be overridden with `SEIR_*` environment variables
(e.g. `SEIR_RECENT_WINDOW_DAYS=180`).

### For the risk model (`seir-risk`)

```python
from seir_features import FEATURE_COLUMNS, evidence_to_features, to_vector

x = to_vector(evidence_to_features(evidence_json_list, action="DELETE"))   # same as training
```

`seir-risk` installs this module with `pip install -e ../seir-evidence`.

## Outputs

| Output | Where | Contract |
|---|---|---|
| Evidence for one snapshot | `data/<repo>/<snapshot>/evidence.json`, `components.json`, `edges.json`, `config_references.json` | `EvidenceItem`, `Component`, `DependencyEdge` |
| Training dataset | `data/dataset/<version>/cases.parquet` + `manifest.json`, `quality_report.md`, `change_cases.jsonl`, `static_feature_requests.csv` | `ChangeCase`; columns per `manifest.json` |

`data/` and `workspace/` are generated and git-ignored; every build is reproducible (pinned
repositories, deterministic IDs).

## Layout

```
app/
  schema/            shared contracts (source of truth for ../contracts)
  collectors/        git_log.py, git_history.py, config_files.py
  dataset/           cases, commit_filters, szz, labels, features, config_history, splits, quality, build
  pipeline.py        analyze_repository(): all evidence for one snapshot
  inventory.py       class list for a snapshot (until Member 4's parser feeds Component records)
  repo_fetcher.py    clone / update / check out a pinned commit
  git_cli.py         thin wrapper around the git command line
  ids.py             deterministic IDs, path -> class name
  config.py          every tunable number
seir_features/       shared evidence -> model-input conversion (no dependencies)
scripts/             command-line entry points (above)
tests/               pytest suite (real throw-away git repositories, no mocks of git)
docs/                DATASET.md (short guide), member3-handover.md (full hand-over to the risk model)
corpus.yaml          repositories used for the dataset, pinned to exact commits
```

Team-wide naming rules and contracts: [../contracts/CONVENTIONS.md](../contracts/CONVENTIONS.md).

## Known limitations

- **Java only**; a "component" is a top-level class (nested classes roll up into their outer class).
- **Labels are approximations**: "changed in the same commit" ≠ "had to change", and SZZ bug tracing
  is heuristic (manual precision review pending).
- **Configuration**: files are scanned line by line (robust to templating, but no YAML key paths);
  only class names and Spring bean references are recognised.
- **Runtime evidence** is not implemented yet (Phase 5); it can never exist for historical cases.
- **Structural features** (dependents, size) for the dataset are pending from the software-analysis module.
