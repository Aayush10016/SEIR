"""Candidate models and a fixed-budget tuning loop (fit on train, select on validation).

Three families, from most interpretable to most flexible (main report §6.6):
  * logreg - multinomial logistic regression on log-scaled, standardised features;
  * rf     - random forest (non-linear, robust, few knobs);
  * xgb    - gradient-boosted trees (usually strongest on tabular data, native NaN support).

Every family gets `balanced` class weights: MEDIUM is ~20 % of cases, and without
weights the model can score well on accuracy while almost never predicting it.
"""

from dataclasses import dataclass, field
from itertools import product
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from risk.config import (
    CLASSES,
    LOGREG_GRID,
    LOGREG_MAX_ITER,
    RANDOM_SEED,
    RF_GRID,
    RF_N_ESTIMATORS,
    SELECTION_METRIC,
    XGB_EARLY_STOPPING_ROUNDS,
    XGB_FIXED,
    XGB_GRID,
)
from risk.data import Split
from risk.evaluate import classification_metrics, probability_metrics
from risk.preprocess import linear_preprocessor

MODEL_FAMILIES = ("logreg", "rf", "xgb")
GRIDS = {"logreg": LOGREG_GRID, "rf": RF_GRID, "xgb": XGB_GRID}
# Used in `model_version`, e.g. "xgb-risk@0.1.0".
VERSION_NAMES = {"logreg": "logreg-risk", "rf": "rf-risk", "xgb": "xgb-risk"}
TREE_FAMILIES = ("rf", "xgb")


@dataclass
class TunedModel:
    family: str
    params: dict[str, Any]
    estimator: Any  # fitted; exposes predict_proba(X) with columns in CLASSES order
    validation: dict  # metrics of the selected configuration
    trials: list[dict] = field(default_factory=list)  # every configuration tried

    def predict_proba(self, X) -> np.ndarray:
        return self.estimator.predict_proba(X)

    def predict(self, X) -> np.ndarray:
        return self.predict_proba(X).argmax(axis=1)


def _expand_grid(grid: dict[str, list]) -> list[dict]:
    keys = list(grid)
    return [dict(zip(keys, values)) for values in product(*(grid[k] for k in keys))]


def _fit_logreg(params: dict, train: Split, validation: Split) -> Pipeline:
    model = Pipeline([
        ("pre", linear_preprocessor()),
        ("clf", LogisticRegression(C=params["C"], class_weight="balanced",
                                   max_iter=LOGREG_MAX_ITER, random_state=RANDOM_SEED)),
    ])
    return model.fit(train.X, train.y)


def _fit_rf(params: dict, train: Split, validation: Split) -> RandomForestClassifier:
    model = RandomForestClassifier(
        n_estimators=RF_N_ESTIMATORS,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=RANDOM_SEED,
        **params,
    )
    return model.fit(train.X, train.y)


def _xgb(params: dict, **overrides) -> XGBClassifier:
    return XGBClassifier(
        objective="multi:softprob",
        num_class=len(CLASSES),
        eval_metric="mlogloss",
        random_state=RANDOM_SEED,
        n_jobs=-1,
        **{**XGB_FIXED, **params, **overrides},
    )


def _fit_xgb(params: dict, train: Split, validation: Split) -> XGBClassifier:
    """Early-stop on validation to find the number of trees, then refit with exactly that many.

    The refit makes the saved model self-contained (no hidden `best_iteration`
    that SHAP or a future loader might ignore). Trees are built sequentially with
    a fixed seed, so the refit's trees equal the first N trees of the first fit.
    """
    train_w = compute_sample_weight("balanced", train.y)
    val_w = compute_sample_weight("balanced", validation.y)
    probe = _xgb(params, early_stopping_rounds=XGB_EARLY_STOPPING_ROUNDS)
    probe.fit(train.X, train.y, sample_weight=train_w,
              eval_set=[(validation.X, validation.y)], sample_weight_eval_set=[val_w], verbose=False)
    n_trees = probe.best_iteration + 1
    return _xgb({**params, "n_estimators": n_trees}).fit(train.X, train.y, sample_weight=train_w)


FITTERS = {"logreg": _fit_logreg, "rf": _fit_rf, "xgb": _fit_xgb}


def evaluate_on(estimator, split: Split) -> dict:
    proba = estimator.predict_proba(split.X)
    return {**classification_metrics(split.y, proba.argmax(axis=1)), **probability_metrics(split.y, proba)}


def tune(family: str, train: Split, validation: Split) -> TunedModel:
    """Try every grid configuration; keep the best validation macro-F1 (ties: lower log loss)."""
    if family not in FITTERS:
        raise ValueError(f"unknown model family {family!r}; known: {MODEL_FAMILIES}")
    trials, best = [], None
    for params in _expand_grid(GRIDS[family]):
        estimator = FITTERS[family](params, train, validation)
        metrics = evaluate_on(estimator, validation)
        if family == "xgb":
            params = {**params, "n_estimators": int(estimator.n_estimators)}
        trials.append({"params": params, SELECTION_METRIC: metrics[SELECTION_METRIC],
                       "log_loss": metrics["log_loss"]})
        key = (metrics[SELECTION_METRIC], -metrics["log_loss"])
        if best is None or key > best[0]:
            best = (key, params, estimator, metrics)
    _, params, estimator, metrics = best
    return TunedModel(family=family, params=params, estimator=estimator, validation=metrics, trials=trials)
