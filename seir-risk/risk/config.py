"""Paths, fixed facts about the dataset, and every tunable number. No magic numbers elsewhere."""

import os
from pathlib import Path

# seir-risk/risk/config.py -> the module folder is one level above the package.
RISK_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = RISK_ROOT.parent
# The evidence module (dataset + contracts). Default: next to seir-risk.
# Override if it lives elsewhere:  SEIR_EVIDENCE_DIR=path/to/seir-evidence
EVIDENCE_DIR = Path(os.environ.get("SEIR_EVIDENCE_DIR", PROJECT_ROOT / "seir-evidence"))

# --- Dataset ------------------------------------------------------------------
# v1:    commons-lang (+ commons-io holdout).
# m3-v2: Member 3's own 7-project experiment (archived in local/); superseded by v4.
# v4:    official dataset (pinned repos): 7 libraries + 2 applications.
# Override to reproduce older results:  SEIR_RISK_DATASET_VERSION=v1
DATASET_VERSION = os.environ.get("SEIR_RISK_DATASET_VERSION", "v4")
DATASET_DIR = EVIDENCE_DIR / "data" / "dataset" / DATASET_VERSION
CASES_FILE = DATASET_DIR / "cases.parquet"
MANIFEST_FILE = DATASET_DIR / "manifest.json"
# Written by the archived m3-v2 builder only: project roles, including "sealed".
ROLES_FILE = DATASET_DIR / "quality_gate.json"
SEALED_ROLE = "sealed"
# Sealed projects per version for datasets without a roles file:
# held out AND never evaluated until the single final run.
SEALED_REPOSITORIES_BY_VERSION = {"v4": frozenset({"jhy/jsoup"})}
# Seen-once holdout: evaluated in the v1 final run, reported but labelled as such.
SEEN_ONCE_HOLDOUT = frozenset({"apache/commons-io"})
# Projects whose runtime configuration can name classes (config clue non-zero).
APPLICATION_REPOSITORIES = frozenset({"apache/syncope", "apache/shiro"})

# Label order is fixed: index 0 < 1 < 2 is the "risk up" direction.
CLASSES = ("LOW", "MEDIUM", "HIGH")

# Expected row counts per dataset version (from each version's quality report).
# A mismatch means the data changed and results are not comparable.
EXPECTED_SPLIT_ROWS_BY_VERSION = {
    "v1": {"train": 3_295, "validation": 706, "test": 707, "holdout": 3_100},
    "m3-v2": {"train": 10_677, "validation": 2_301, "test": 2_297, "holdout": 5_808},
    "v4": {"train": 15_451, "validation": 3_320, "test": 3_334, "holdout": 5_772},
}
EXPECTED_SPLIT_ROWS = EXPECTED_SPLIT_ROWS_BY_VERSION[DATASET_VERSION]
EXPECTED_TOTAL_ROWS = sum(EXPECTED_SPLIT_ROWS.values())

DEVELOPMENT_SPLITS = ("train", "validation")
FINAL_SPLITS = ("test", "holdout")  # looked at once, at the very end
GROUP_COLUMN = "commit_sha"  # cases from one commit are never separated

# --- Feature families (ablation) ------------------------------------------------
# `action_is_delete` is the question being asked, not evidence: always included.
ACTION_FEATURE = "action_is_delete"
# Column naming rule: <source>_<evidence_type>.
FEATURE_FAMILIES = ("static", "git", "config", "runtime")

# --- Outputs ----------------------------------------------------------------------
MODELS_DIR = RISK_ROOT / "models"
# Reports, figures and notes are local only (git-ignored `local/`).
LOCAL_DIR = RISK_ROOT / "local"
REPORTS_DIR = LOCAL_DIR / "reports" / DATASET_VERSION
DEV_REPORTS_DIR = REPORTS_DIR / "development"
FINAL_REPORTS_DIR = REPORTS_DIR / "final"
# Model version per dataset version: a model is only comparable with its own data.
# m3-v2 was an experiment only (no shipped model).
MODEL_SEMVER = {"v1": "0.1.0", "m3-v2": "0.0.0-m3v2", "v4": "0.2.0"}[DATASET_VERSION]

RANDOM_SEED = 42

# --- Rule-based baseline (main report §6.5) ---------------------------------------
# Weights are fixed *before* looking at model results and follow priors from the
# defect/change-prediction literature, not this dataset:
#   * change coupling predicts change propagation (Zimmermann et al. 2005,
#     D'Ambros et al. 2009) -> strongest weight on co-change;
#   * recent / frequent change, churn and many authors predict defects
#     (Nagappan & Ball 2005, Moser et al. 2008, Hassan 2009);
#   * code that has been stable for a long time is less risky;
#   * deleting a class breaks every caller.
#   * a runtime configuration file naming the class is a dependency that code
#     search misses (main report §2.2, §4.4) -> removing/changing it is riskier.
#     (Weight fixed 2026-09-30, before any v4 result was seen.)
# lines_added / lines_deleted get 0: they are already inside total_churn.
# Only the two class thresholds are chosen (on validation).
BASELINE_WEIGHTS = {
    "action_is_delete": 1.0,
    "git_co_change_count": 2.0,
    "git_recent_commit_count": 1.0,
    "git_churn_ratio": 1.0,
    "git_historical_commit_count": 0.5,
    "git_unique_contributors": 0.5,
    "git_total_churn": 0.5,
    "git_days_since_last_change": -0.5,
    "git_lines_added": 0.0,
    "git_lines_deleted": 0.0,
    "config_config_reference_count": 1.0,
}
# Candidate thresholds = these quantiles of the validation scores.
BASELINE_THRESHOLD_QUANTILES = tuple(q / 100 for q in range(5, 96, 5))

# --- Models and tuning budget --------------------------------------------------------
# Same small, fixed grids for every ablation run (a fair comparison needs an
# identical tuning budget). Selection metric: validation macro-F1.
SELECTION_METRIC = "macro_f1"

LOGREG_GRID = {"C": [0.01, 0.1, 1.0, 10.0]}
LOGREG_MAX_ITER = 2_000

RF_GRID = {
    "max_depth": [4, 8, None],
    "min_samples_leaf": [5, 20],
}
RF_N_ESTIMATORS = 500

XGB_GRID = {
    "max_depth": [2, 3, 4, 6],
    "learning_rate": [0.03, 0.1],
    "min_child_weight": [1, 5],
}
XGB_FIXED = {
    "n_estimators": 2_000,  # upper bound; early stopping picks the real number
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "tree_method": "hist",
}
XGB_EARLY_STOPPING_ROUNDS = 50

# --- Evaluation --------------------------------------------------------------------
CALIBRATION_BINS = 10
BOOTSTRAP_ITERATIONS = 1_000
CONFIDENCE_LEVEL = 0.95
# `is_calibrated` may be true only if calibrated top-label ECE is at most this
# on BOTH final splits (verification, not tuning).
MAX_ECE_FOR_CALIBRATED = 0.05
# Calibration method choice is made on validation with commit-grouped folds.
CALIBRATION_METHODS = ("sigmoid", "isotonic")
CALIBRATION_FOLDS = 5

# --- Explanations -------------------------------------------------------------------
TOP_FEATURES = 5
# What `top_features[].contribution` explains (see risk/explain.py):
#   "predicted_class" - P(predicted class); + means "pushed towards the class shown"
#   "risk_up"         - log P(HIGH) - log P(LOW); + always means "riskier"
EXPLANATION_TARGETS = ("predicted_class", "risk_up")
EXPLANATION_TARGET = "predicted_class"
# Reference sample that defines "the average case" for SHAP (drawn from train).
SHAP_BACKGROUND_ROWS = 100
# Exact Shapley values (deterministic: same input -> same reasons) up to this many
# features; beyond it the cost doubles per feature, so the permutation estimate is used.
SHAP_EXACT_MAX_FEATURES = 12
# Rows per final split explained for the global SHAP analysis (fixed random sample).
SHAP_ANALYSIS_ROWS = 500
