"""Phase 0 check: does the dataset match the expected version (row counts, columns, labels)?

Run from seir-risk/:  python -m scripts.check_dataset
Exits non-zero on the first mismatch, so it can gate later scripts.
"""

import json
import sys

import pandas as pd

from risk.config import (
    CASES_FILE,
    CLASSES,
    EXPECTED_SPLIT_ROWS,
    EXPECTED_TOTAL_ROWS,
    MANIFEST_FILE,
)


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    for path in (CASES_FILE, MANIFEST_FILE):
        if not path.exists():
            fail(f"missing {path} - build it with the seir-evidence dataset builder")

    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    df = pd.read_parquet(CASES_FILE)

    features = manifest["feature_columns"]
    forbidden = manifest["forbidden_columns"]
    label_col = manifest["label_column"]
    split_col = manifest["split_column"]

    # 1. Row counts, total and per split.
    if len(df) != EXPECTED_TOTAL_ROWS:
        fail(f"{len(df)} rows, expected {EXPECTED_TOTAL_ROWS}")
    split_counts = df[split_col].value_counts().to_dict()
    if split_counts != EXPECTED_SPLIT_ROWS:
        fail(f"split sizes {split_counts}, expected {EXPECTED_SPLIT_ROWS}")

    # 2. Every column the manifest names actually exists.
    missing = [c for c in [*features, *forbidden, label_col, split_col] if c not in df.columns]
    if missing:
        fail(f"manifest columns absent from the table: {missing}")

    # 3. The most important leakage guard: features and forbidden columns never overlap.
    overlap = set(features) & set(forbidden)
    if overlap:
        fail(f"forbidden columns listed as features: {sorted(overlap)}")

    # 4. Labels are exactly the three risk classes.
    unexpected = set(df[label_col].unique()) - set(CLASSES)
    if unexpected:
        fail(f"unexpected label values: {sorted(unexpected)}")

    # 5. One row per case.
    if df["case_id"].duplicated().any():
        fail("duplicate case_id values")

    print(f"OK: {len(df):,} rows, {len(features)} features, splits {split_counts}")
    print(f"features: {features}")
    print("label distribution per split:")
    print(pd.crosstab(df[split_col], df[label_col])[list(CLASSES)])
    print(f"missing values in features: {int(df[features].isna().sum().sum())}")


if __name__ == "__main__":
    main()
