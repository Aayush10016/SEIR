"""Per-prediction SHAP explanations (main report §6.10). Two interchangeable targets:

* `predicted_class` — explains P(predicted class | x), the probability of the class
  the model chose (HIGH, MEDIUM or LOW). A contribution of +0.04 means "this
  feature raised the chance of the predicted class by 4 points". Easy to phrase,
  but the meaning of the sign depends on the class: +0.04 towards LOW means safer.

* `risk_up` — explains log P(HIGH | x) - log P(LOW | x). One fixed direction:
  positive always means riskier, whatever the class. For softmax models it equals
  margin_HIGH - margin_LOW, so SHAP values are exact and additive.

In both cases the contributions sum to f(x) minus the average f over a background
sample of training cases.

Explainer choice: TreeSHAP is used only for XGBoost + risk_up (raw margins). SHAP
cannot give per-class *probabilities* for multi-class XGBoost (softmax does not
decompose tree by tree), so predicted_class uses the model-agnostic explainer on
predict_proba for every model family: same units ("probability points"), still additive. Explanations describe the underlying (uncalibrated)
model: calibration rescales scores, it does not change which evidence drove them.
"""

import math

import numpy as np
import pandas as pd
import shap

from risk.config import (
    CLASSES,
    EXPLANATION_TARGETS,
    RANDOM_SEED,
    SHAP_BACKGROUND_ROWS,
    SHAP_EXACT_MAX_FEATURES,
    TOP_FEATURES,
)

LOW, HIGH = CLASSES.index("LOW"), CLASSES.index("HIGH")
PROBA_FLOOR = 1e-12  # avoids log(0) for a hard 0/1 score
PREDICTED_CLASS, RISK_UP = EXPLANATION_TARGETS


def fast_proba(estimator, is_xgboost: bool, columns: list[str]):
    """predict_proba for SHAP's many repeated calls.

    XGBoost's scikit-learn wrapper spends most of its time converting a DataFrame
    on every call (about 0.8 s per call here); the booster on a float32 array gives
    identical probabilities about 200x faster.
    """
    if is_xgboost:
        booster = estimator.get_booster()
        return lambda X: booster.inplace_predict(np.asarray(X, dtype=np.float32))
    return lambda X: estimator.predict_proba(pd.DataFrame(X, columns=columns))


def risk_up_score(proba: np.ndarray) -> np.ndarray:
    proba = np.clip(proba, PROBA_FLOOR, 1.0)
    return np.log(proba[:, HIGH]) - np.log(proba[:, LOW])


class RiskExplainer:
    """SHAP explainer for either target. XGBoost uses TreeSHAP; other models a model-agnostic explainer."""

    def __init__(self, estimator, background: pd.DataFrame, is_xgboost: bool, target: str):
        if target not in EXPLANATION_TARGETS:
            raise ValueError(f"unknown explanation target {target!r}; known: {EXPLANATION_TARGETS}")
        self.estimator = estimator
        self.features = list(background.columns)
        self.is_xgboost = is_xgboost
        self.target = target
        sample = background.sample(min(SHAP_BACKGROUND_ROWS, len(background)), random_state=RANDOM_SEED)

        self._tree = is_xgboost and target == RISK_UP
        if self._tree:
            # Raw class margins; margin_HIGH - margin_LOW == risk_up.
            self._explainer = shap.TreeExplainer(estimator)
        else:
            proba = fast_proba(estimator, is_xgboost, self.features)

            def model_output(X):
                return risk_up_score(proba(X)) if target == RISK_UP else proba(X)

            # Both algorithms are additive; exact is also deterministic.
            algorithm = "exact" if len(self.features) <= SHAP_EXACT_MAX_FEATURES else "permutation"
            masker = shap.maskers.Independent(sample, max_samples=len(sample))
            self._explainer = shap.Explainer(model_output, masker, algorithm=algorithm, seed=RANDOM_SEED)

    def _raw_values(self, X: pd.DataFrame) -> np.ndarray:
        if self._tree:
            return np.asarray(self._explainer.shap_values(X))
        return self._explainer(X, silent=True).values

    def contributions(self, X: pd.DataFrame) -> np.ndarray:
        """SHAP values, shape (rows, features), for this explainer's target."""
        X = X[self.features]
        values = self._raw_values(X)
        if self.target == RISK_UP:
            # TreeSHAP returns per-class margins; the generic explainer already returns risk_up.
            return values[:, :, HIGH] - values[:, :, LOW] if values.ndim == 3 else values
        # predicted_class: values are (rows, features, classes); keep the chosen class per row.
        predicted = self.estimator.predict_proba(X).argmax(axis=1)
        return values[np.arange(len(X)), :, predicted]


def _plain(value):
    """JSON-friendly feature value: NaN -> None (unknown), whole floats -> int."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    value = float(value)
    return int(value) if value.is_integer() else value


def top_features(row: pd.Series, contributions: np.ndarray, k: int = TOP_FEATURES) -> list[dict]:
    """The k largest |contributions| for one row, as `FeatureContribution` dicts."""
    order = np.argsort(-np.abs(contributions))[:k]
    return [
        {"feature": row.index[i], "value": _plain(row.iloc[i]), "contribution": float(contributions[i])}
        for i in order
    ]
