"""Transparent, non-ML rule-based risk score (main report §6.5).

score = sum_i weight_i * z_i, where z_i is the train-standardised log feature.
Weights are fixed in config from literature priors; nothing is fitted to labels
except two thresholds, chosen on validation:
    score < t_low -> LOW,   t_low <= score < t_high -> MEDIUM,   otherwise HIGH.

The question it lets us answer: does a *learned* model beat a reasonable,
hand-written scoring rule built from the same features?
"""

from itertools import combinations

import numpy as np
import pandas as pd

from risk.config import BASELINE_THRESHOLD_QUANTILES, BASELINE_WEIGHTS
from risk.evaluate import macro_f1
from risk.preprocess import signed_log1p


class RuleBasedBaseline:
    def __init__(self, weights: dict[str, float] = BASELINE_WEIGHTS):
        self.weights = dict(weights)
        self.features_: list[str] = []
        self.mean_: pd.Series | None = None
        self.std_: pd.Series | None = None
        self.thresholds_: tuple[float, float] | None = None

    def fit(self, X_train: pd.DataFrame) -> "RuleBasedBaseline":
        """Learn only the standardisation (unsupervised; labels are not used)."""
        # Features without a weight (e.g. a new evidence family) are ignored,
        # so the rule stays exactly as written down.
        self.features_ = [f for f in X_train.columns if f in self.weights]
        logged = signed_log1p(X_train[self.features_])
        self.mean_ = pd.Series(np.nanmean(logged, axis=0), index=self.features_)
        std = np.nanstd(logged, axis=0)
        self.std_ = pd.Series(np.where(std > 0, std, 1.0), index=self.features_)
        return self

    def score(self, X: pd.DataFrame) -> np.ndarray:
        z = (pd.DataFrame(signed_log1p(X[self.features_]), columns=self.features_, index=X.index)
             - self.mean_) / self.std_
        # Unknown evidence contributes nothing (z = 0 is the average case).
        z = z.fillna(0.0)
        weights = np.array([self.weights[f] for f in self.features_])
        return z.to_numpy() @ weights

    def fit_thresholds(self, X_val: pd.DataFrame, y_val: np.ndarray) -> "RuleBasedBaseline":
        """Pick (t_low, t_high) among validation-score quantiles that maximise macro-F1."""
        scores = self.score(X_val)
        candidates = np.quantile(scores, BASELINE_THRESHOLD_QUANTILES)
        best = max(
            combinations(candidates, 2),  # t_low < t_high, since quantiles are sorted
            key=lambda t: macro_f1(y_val, self._classify(scores, t)),
        )
        self.thresholds_ = (float(best[0]), float(best[1]))
        return self

    @staticmethod
    def _classify(scores: np.ndarray, thresholds: tuple[float, float]) -> np.ndarray:
        return np.digitize(scores, thresholds)  # 0 = LOW, 1 = MEDIUM, 2 = HIGH

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.thresholds_ is None:
            raise RuntimeError("call fit_thresholds() on validation first")
        return self._classify(self.score(X), self.thresholds_)
