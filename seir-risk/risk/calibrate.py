"""Probability calibration (main report §6.9, §14.5).

Why it is needed here: balanced class weights deliberately inflate the scores of
rare classes, so raw scores are *decision* scores, not probabilities.

Procedure:
  1. choose between none / sigmoid / isotonic on validation with commit-grouped
     folds (fit the calibrator on k-1 folds, score log loss on the held-out fold),
     so the choice is never judged on the data it was fitted on;
  2. fit the chosen calibrator on all of validation;
  3. the final evaluation verifies it on test and holdout; only then may
     `is_calibrated` be true.
"""

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import log_loss
from sklearn.model_selection import GroupKFold

from risk.config import CALIBRATION_FOLDS, CALIBRATION_METHODS
from risk.data import Split
from risk.evaluate import LABELS, brier_score, expected_calibration_error

NO_CALIBRATION = "none"


def fit_calibrator(estimator, X, y, method: str) -> CalibratedClassifierCV:
    # FrozenEstimator: the model is not retrained; all given rows fit the calibrator.
    return CalibratedClassifierCV(FrozenEstimator(estimator), method=method).fit(X, y)


def compare_calibration(estimator, validation: Split) -> dict[str, dict]:
    """Out-of-fold scores on validation for each method (and for no calibration)."""
    raw = estimator.predict_proba(validation.X)
    oof = {NO_CALIBRATION: raw, **{m: np.zeros_like(raw) for m in CALIBRATION_METHODS}}
    folds = GroupKFold(n_splits=CALIBRATION_FOLDS)
    for fit_idx, eval_idx in folds.split(validation.X, validation.y, groups=validation.groups):
        for method in CALIBRATION_METHODS:
            calibrator = fit_calibrator(estimator, validation.X.iloc[fit_idx], validation.y[fit_idx], method)
            oof[method][eval_idx] = calibrator.predict_proba(validation.X.iloc[eval_idx])
    return {
        method: {
            "log_loss": float(log_loss(validation.y, proba, labels=LABELS)),
            "brier": brier_score(validation.y, proba),
            "ece": expected_calibration_error(validation.y, proba),
        }
        for method, proba in oof.items()
    }


def choose_and_fit(estimator, validation: Split) -> tuple[str, CalibratedClassifierCV | None, dict]:
    comparison = compare_calibration(estimator, validation)
    method = min(comparison, key=lambda m: comparison[m]["log_loss"])
    calibrator = None if method == NO_CALIBRATION else fit_calibrator(
        estimator, validation.X, validation.y, method)
    return method, calibrator, comparison
