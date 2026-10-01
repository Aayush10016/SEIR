"""Metrics shared by every model, so all comparisons use identical definitions.

* Class metrics: macro precision/recall/F1 (classes are imbalanced), per-class recall.
* Probability metrics: multi-class Brier score, log loss, expected calibration error.
* Uncertainty: bootstrap over *commits*, not rows. Cases from one commit are
  correlated; resampling rows would pretend we have more independent evidence
  than we do and give confidence intervals that are too narrow.
"""

from collections.abc import Callable

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)

from risk.config import BOOTSTRAP_ITERATIONS, CALIBRATION_BINS, CLASSES, CONFIDENCE_LEVEL, RANDOM_SEED

LABELS = list(range(len(CLASSES)))


def macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0))


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, zero_division=0
    )
    return {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(precision.mean()),
        "macro_recall": float(recall.mean()),
        "macro_f1": float(f1.mean()),
        "per_class": {
            name: {"precision": float(p), "recall": float(r), "f1": float(f), "support": int(s)}
            for name, p, r, f, s in zip(CLASSES, precision, recall, f1, support)
        },
        # rows = true class, columns = predicted class, in CLASSES order
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
    }


def brier_score(y_true: np.ndarray, proba: np.ndarray) -> float:
    """Mean squared distance between the score vector and the one-hot truth (0 = perfect, 2 = worst)."""
    one_hot = np.eye(len(CLASSES))[y_true]
    return float(np.mean(np.sum((proba - one_hot) ** 2, axis=1)))


def expected_calibration_error(y_true: np.ndarray, proba: np.ndarray, bins: int = CALIBRATION_BINS) -> float:
    """Top-label ECE: when the model says 70 % for its chosen class, is it right ~70 % of the time?"""
    confidence = proba.max(axis=1)
    correct = (proba.argmax(axis=1) == y_true).astype(float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    bin_ids = np.clip(np.digitize(confidence, edges[1:-1]), 0, bins - 1)
    ece = 0.0
    for b in range(bins):
        mask = bin_ids == b
        if mask.any():
            ece += mask.mean() * abs(correct[mask].mean() - confidence[mask].mean())
    return float(ece)


def reliability_curve(y_true: np.ndarray, proba: np.ndarray, class_index: int,
                      bins: int = CALIBRATION_BINS) -> dict:
    """Per-class reliability data: mean predicted score vs observed frequency per bin."""
    scores = proba[:, class_index]
    observed = (y_true == class_index).astype(float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    bin_ids = np.clip(np.digitize(scores, edges[1:-1]), 0, bins - 1)
    mean_score, frequency, count = [], [], []
    for b in range(bins):
        mask = bin_ids == b
        if mask.any():
            mean_score.append(float(scores[mask].mean()))
            frequency.append(float(observed[mask].mean()))
            count.append(int(mask.sum()))
    return {"mean_score": mean_score, "observed_frequency": frequency, "count": count}


def probability_metrics(y_true: np.ndarray, proba: np.ndarray) -> dict:
    return {
        "brier": brier_score(y_true, proba),
        "log_loss": float(log_loss(y_true, proba, labels=LABELS)),
        "ece": expected_calibration_error(y_true, proba),
    }


def _group_bootstrap_indices(groups: np.ndarray, iterations: int, seed: int):
    """Yield row indices of bootstrap samples drawn over whole groups (commits)."""
    rng = np.random.default_rng(seed)
    unique, inverse = np.unique(groups, return_inverse=True)
    rows_by_group = [np.flatnonzero(inverse == g) for g in range(len(unique))]
    for _ in range(iterations):
        picked = rng.integers(0, len(unique), size=len(unique))
        yield np.concatenate([rows_by_group[g] for g in picked])


def _interval(values: list[float], level: float) -> tuple[float, float]:
    tail = (1.0 - level) / 2 * 100
    low, high = np.percentile(values, [tail, 100 - tail])
    return float(low), float(high)


def bootstrap_ci(y_true: np.ndarray, y_pred: np.ndarray, groups: np.ndarray,
                 metric: Callable[[np.ndarray, np.ndarray], float] = macro_f1,
                 iterations: int = BOOTSTRAP_ITERATIONS, level: float = CONFIDENCE_LEVEL,
                 seed: int = RANDOM_SEED) -> dict:
    values = [metric(y_true[idx], y_pred[idx]) for idx in _group_bootstrap_indices(groups, iterations, seed)]
    low, high = _interval(values, level)
    return {"estimate": metric(y_true, y_pred), "ci_low": low, "ci_high": high, "level": level}


def paired_bootstrap(y_true: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray, groups: np.ndarray,
                     metric: Callable[[np.ndarray, np.ndarray], float] = macro_f1,
                     iterations: int = BOOTSTRAP_ITERATIONS, level: float = CONFIDENCE_LEVEL,
                     seed: int = RANDOM_SEED) -> dict:
    """Difference metric(A) - metric(B) on the *same* resampled cases.

    Pairing removes the shared "this sample was easy / hard" noise, so it can
    detect a real difference that two separate intervals would hide.
    """
    diffs = [metric(y_true[idx], pred_a[idx]) - metric(y_true[idx], pred_b[idx])
             for idx in _group_bootstrap_indices(groups, iterations, seed)]
    low, high = _interval(diffs, level)
    return {
        "difference": metric(y_true, pred_a) - metric(y_true, pred_b),
        "ci_low": low,
        "ci_high": high,
        "level": level,
        "share_a_better": float(np.mean(np.array(diffs) > 0)),
    }
