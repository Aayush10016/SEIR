# seir-risk — SEIR Risk Model (Member 3)

Predicts how risky it is to **modify or delete a Java class**: **LOW**, **MEDIUM** or **HIGH**,
with the clues that drove the answer. The output is the team's shared `RiskAssessment` contract,
consumed by the explanation layer, the backend and the dashboard.

This file is the single starting point for the module: what it does, how to run it, how it was
built, and what is still open.

---

## 1. Where it fits

```
Code structure ────────────┐
                           ├─► evidence ─► seir_features (shared) ─► seir-risk ─► RiskAssessment ─► explainer / backend / dashboard
Git, configuration ────────┘
```

- **Input:** evidence about one class from the Evidence Service, plus the proposed action
  (`MODIFY`, `DELETE`, `DEPRECATE`).
- **Conversion:** evidence is turned into model inputs by the shared
  `seir_features.evidence_to_features` (in `seir-evidence`). This is the same function used to build the training
  data, so training and live use can never compute inputs differently.
- **Output:** `RiskAssessment` with `risk_class`, `class_scores`, `top_features`, `is_calibrated`,
  `model_version` and `feature_spec_version`.

## 2. What the model sees and predicts

**Inputs** (`features@1.0`, 11 columns, in this order):

| Column | Meaning |
|---|---|
| `action_is_delete` | 1 if the class is deleted (DEPRECATE is treated as MODIFY) |
| `git_churn_ratio` | Share of lifetime edits made in the last 90 days |
| `git_co_change_count` | Other classes that usually change together with it |
| `git_days_since_last_change` | Days since it was last changed |
| `git_historical_commit_count` | Commits that touched it before the change |
| `git_lines_added` / `git_lines_deleted` / `git_total_churn` | Lifetime size of edits |
| `git_recent_commit_count` | Commits in the last 90 days |
| `git_unique_contributors` | Different authors |
| `config_config_reference_count` | Runtime configuration files that name the class |

Every input describes the class **before** the change. Unknown values are `NaN`, never 0.

**Labels** (`labels@1.0`, fixed before any training):

| Label | Meaning |
|---|---|
| LOW | No other class had to change, and no later bug was traced back to the change |
| MEDIUM | 1–3 other classes changed with it |
| HIGH | 4 or more other classes changed with it, **or** a later bug fix was traced back to it |

**Reasons (`top_features`):** each `contribution` is the SHAP value for the **predicted class**
(team decision, 2026-09-30). Positive means the clue pushed the prediction **towards**
`risk_class`; negative means it pushed away. The values are in probability points and add up
exactly. The same input always gives the same reasons.

## 3. Setup

Python 3.11+.

```bash
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest
```

`requirements.txt` pins the exact library versions and installs `seir-evidence` from this repository. The predictor refuses to load a model if
scikit-learn, xgboost or numpy differ from the training versions.

**Data:** the training dataset is not in Git. Build it with the `seir-evidence` dataset builder (about 10 minutes;
pinned repositories, so the output is identical every time):

```bash
cd ../seir-evidence && python -m scripts.build_dataset --version v4
```

If `seir-evidence` is somewhere else, set `SEIR_EVIDENCE_DIR=path/to/seir-evidence`.

## 4. Run

```bash
.venv/Scripts/python -m scripts.check_dataset      # dataset matches the expected v4 counts
.venv/Scripts/python -m scripts.train              # train, select, calibrate -> models/xgb-risk@0.2.0/
.venv/Scripts/python -m scripts.ablation           # value of each evidence family (validation)
.venv/Scripts/python -m scripts.final_evaluation   # ONE-TIME final test (refuses to run twice)
```

Trained models (`models/`) and reports (`local/`) are outputs and are git-ignored.

## 5. Use the model

```python
from risk.predictor import RiskPredictor

predictor = RiskPredictor.load("models/xgb-risk@0.2.0")
assessment = predictor.predict_from_evidence(evidence, repo_id, component_id, action="DELETE")
assessment.model_dump_json()   # validated RiskAssessment
```

`evidence` is the Evidence Service output for **one** class (JSON dicts or `EvidenceItem`s).
A prediction with its explanation takes about 0.06 s. Loading fails loudly if:
- the model's feature spec differs from `seir_features`;
- the class order differs;
- the library versions differ.

## 6. How it was built

| Step | Choice | Why |
|---|---|---|
| Data | Dataset v4: 27,877 real changes from 9 Java projects | Real outcomes, not invented labels |
| Splits | Oldest 70 % / next 15 % / newest 15 % per project. Two whole projects held out: `commons-io` (results seen once in v1) and `jsoup` (**sealed**, never evaluated) | Tests on the future and on unseen projects |
| Leakage guards | Features only from the manifest. Post-change columns raise an error. Test, holdout and sealed sets are locked in code (`risk/data.py`). The final evaluation refuses to run twice | Leakage makes scores look good and mean nothing |
| Reference points | Majority class, random guessing, and a hand-written rule with weights fixed from literature before training | A learned model must beat these |
| Models | Logistic Regression, Random Forest, XGBoost; same fixed tuning budget; balanced class weights | From interpretable to flexible; no neural network at this data size |
| Selection | Best validation macro-F1 (average F1 over the 3 labels), rule fixed in advance | Prevents picking the model we hoped would win |
| Uncertainty | 95 % intervals by resampling whole commits | Changes from one commit are not independent |
| Calibration | Chosen on validation; `is_calibrated` is true only if verified on the final sets | Scores are "model scores" unless proven to be probabilities |

## 7. Current results (validation, 3,320 changes; final test not run yet)

| Predictor | Macro-F1 |
|---|---|
| Random guessing | 0.320 |
| Hand-written rule | 0.289 |
| **XGBoost `xgb-risk@0.2.0` (selected)** | **0.428** (95 % CI 0.40–0.45) |
| Logistic Regression / Random Forest | 0.418 / 0.418 (statistically tied with XGBoost) |

It catches about **55 % of HIGH-risk changes**. Treat it as a **"look here first" hint, not a
gatekeeper**, and show scores as "model score", not "probability".

## 8. Findings that matter

- **The clues, not the data size, set the ceiling.** Tripling the data, combining clues and
  switching models moved the score by at most ±0.02.
- **More history means safer, not riskier.** Heavily maintained classes get many small,
  self-contained changes. Many co-change partners mean riskier.
- **The model does not know what the change is.** A typo fix and a public API change to the
  same class look identical to it. This is the biggest limit.
- **Bug-tracing labels are noisy.** A 30-link review (AI-assisted, not a human review) found
  44 % precision (95 % CI 27–63 %). It affects about 2 % of labels.

## 9. Open items

- [ ] Code-structure clues (`static_*`) from the software-analysis module. This is the biggest expected improvement
      and the project's main research question; `scripts.ablation` picks them up automatically.
- [ ] Run the Git vs Git + config comparison (`scripts.ablation`), including the Syncope and
      Shiro application projects.
- [ ] One-time final evaluation, including the sealed `jsoup` project, once the team agrees
      the model is final.
- [ ] Team decision: should SEIR also accept the *planned change* (draft diff) as input? This is
      the most promising route to a large score increase.

## 10. Layout

```
risk/
  config.py      every path, version and tunable number
  data.py        dataset loading + leakage guards (locked final and sealed sets)
  baseline.py    hand-written rule (non-ML reference)
  models.py      Logistic Regression / Random Forest / XGBoost + fixed tuning budget
  pipeline.py    develop(): train on train, select on validation
  calibrate.py   calibration method choice and fitting
  evaluate.py    macro-F1, Brier, ECE, reliability, commit-level bootstrap
  explain.py     SHAP reasons (predicted class; risk-up kept as an option)
  predictor.py   load a packaged model -> RiskAssessment
  ablation.py    same model on every evidence-family combination
  plots.py, reporting.py   figures and tables for local reports
scripts/         check_dataset, train, ablation, final_evaluation, experiment_more_data
tests/           leakage guards, contract validity, explanation maths, input safety, speed
requirements.txt pinned dependencies
pyproject.toml   package definition
```
