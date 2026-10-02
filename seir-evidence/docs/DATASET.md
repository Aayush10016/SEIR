# SEIR Risk Dataset — short guide

**Current version:** `v4` · **Label rules:** `labels@1.0` · **Features:** `features@1.0` (`seir_features`)
**Build:** `python -m scripts.build_dataset --version v4` (from `seir-evidence/`, ~10 min, identical output every time)

Exact numbers (case counts, exclusions, class balance, leakage checks) are in
`data/dataset/v4/quality_report.md`, written by every build. The full hand-over to the risk
model, with statistics and modelling advice, is [member3-handover.md](member3-handover.md).

## 1. What one row is

One **change case**: a production Java class that existed before a real historical commit and was
modified or deleted by it.

- **Features** describe the class *just before* the commit (`as_of` = commit time, exclusive).
- The **label** describes what *actually happened* at and after the commit.

## 2. Projects (all pinned to a fixed commit in `corpus.yaml`)

| Projects | Role |
|---|---|
| commons-lang, commons-collections, commons-compress, commons-codec, commons-text | training (libraries) |
| apache/syncope (capped at 5,000 cases, whole commits sampled), apache/shiro | training (applications — the only rows with runtime configuration references) |
| apache/commons-io | holdout — unseen project, already evaluated once |
| jhy/jsoup | holdout — **sealed**, evaluated exactly once |

## 3. Columns

| Group | Columns | Use for training? |
|---|---|---|
| IDs | `case_id`, `repo_id`, `commit_sha`, `parent_sha`, `as_of`, `target_component_id`, `target_parent_path`, `action` | ❌ identifiers only |
| Features | `manifest.json → feature_columns` = `seir_features.FEATURE_COLUMNS` | ✅ |
| **Forbidden** | `label_spread`, `label_impacted_test_count`, `label_caused_bug_fix`, `label_fix_commit_count` | ⛔ never — post-change facts the label is built from |
| Label | `label` ∈ {LOW, MEDIUM, HIGH} | 🎯 target |
| Split | `split` ∈ {train, validation, test, holdout} | how to evaluate |

- Feature names follow `<source>_<evidence_type>` (`git_…`, `config_…`, later `static_…`), so an
  ablation run is a filter on the column prefix.
- `config_config_reference_count` counts places in **runtime** configuration (Spring XML,
  `application*.yml/properties`, MyBatis mappers, ServiceLoader, `spring.factories`…) that name the
  class. Build-tool and test configuration are not counted; libraries are always 0.
- `NaN` means **unknown**, never zero.
- For live predictions build features with `seir_features.evidence_to_features` — the same function
  the dataset builder uses.

## 4. Labels (`labels@1.0`, fixed before any training)

| Label | Rule |
|---|---|
| **HIGH** | the change later needed a bug fix (SZZ), **or** ≥ 4 other production classes changed with it |
| **MEDIUM** | 1–3 other production classes changed with it |
| **LOW** | no other production class changed and no bug was caused |

**Excluded** (each counted in the quality report): root commits, cherry-picked duplicates, bulk
commits (> 30 Java files), cosmetic commits, newly created classes, changes in the last 180 days
(right-censoring), and Syncope cases above its cap.

## 5. How to evaluate

| Split | Meaning | Use |
|---|---|---|
| `train` | oldest 70 % of each training project | fit |
| `validation` | next 15 % | model selection, calibration |
| `test` | newest 15 % | report once |
| `holdout` | commons-io and jsoup (whole projects) | report once; jsoup is sealed |

Never shuffle across splits or use random K-fold on the whole table; use time-ordered folds grouped
by `commit_sha` inside `train`. Classes are imbalanced: report macro-F1 and per-class recall.

## 6. Structural (STATIC) features — pending Member 4

`static_feature_requests.csv` lists, per case, the commit to analyse (`parent_sha`), the class
(`target_component_id`) and its file at that commit (`target_parent_path`). Structural evidence must
come back as `EvidenceItem`s (`source: STATIC`, `snapshot: parent_sha`, `as_of: as_of`; see
`../../contracts/CONVENTIONS.md`); a future dataset version then adds them as `static_*` columns.

## 7. Known limitations

1. "Changed in the same commit" ≠ "had to change" (tangled commits).
2. SZZ is heuristic: fixes without fix words are missed; add-only fixes cannot be traced.
3. Label thresholds (≥ 4 / ≥ 1) are operational definitions, not ground truth.
4. A training label may use a fix from the test period; features never do.
