"""Preprocessing for models that need it. Tree models use raw features (they are scale-invariant)."""

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler


def signed_log1p(values):
    """log(1 + |x|) with the sign kept.

    Counts here span 4-5 orders of magnitude (churn from 24 to 82,765). A linear
    model on raw values would be dominated by a few huge classes. The log turns
    "10x more" into "+2.3", a constant step. Keeping the sign makes it safe for
    future features that can be negative.
    """
    values = np.asarray(values, dtype=float)
    return np.sign(values) * np.log1p(np.abs(values))


def linear_preprocessor() -> Pipeline:
    """Impute -> log -> standardise. Fitted on train only, as part of the model pipeline.

    `add_indicator=True` adds a `<feature>_missing` column for every feature that
    had NaN during fitting: "unknown" is information, not the median value.
    """
    return Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
        ("log", FunctionTransformer(signed_log1p, feature_names_out="one-to-one")),
        ("scale", StandardScaler()),
    ])
