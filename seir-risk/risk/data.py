"""Loading the dataset with the leakage rules enforced in code, not just in documentation.

Rules (main report §6.8, §9.3):
  1. features come only from the manifest's `feature_columns`;
  2. forbidden (post-change) columns can never become features;
  3. test / holdout are unreachable unless the caller explicitly asks for the final evaluation;
  4. "sealed" projects (a fresh unseen-project test) are excluded even from the final
     splits unless the caller asks for them explicitly as well.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from risk.config import (
    ACTION_FEATURE,
    CASES_FILE,
    CLASSES,
    DEVELOPMENT_SPLITS,
    FEATURE_FAMILIES,
    FINAL_SPLITS,
    GROUP_COLUMN,
    MANIFEST_FILE,
    DATASET_VERSION,
    ROLES_FILE,
    SEALED_REPOSITORIES_BY_VERSION,
    SEALED_ROLE,
)


class LeakageError(AssertionError):
    """A rule that keeps post-change information away from the model was broken."""


@dataclass(frozen=True)
class Split:
    """One split, ready for modelling. `y` holds class indices into CLASSES."""

    name: str
    X: pd.DataFrame
    y: np.ndarray
    groups: np.ndarray  # commit SHA per row, for grouped bootstrap / folds
    frame: pd.DataFrame  # full rows (ids, forbidden columns) for error analysis only


def load_manifest(path: Path = MANIFEST_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_cases(path: Path = CASES_FILE) -> pd.DataFrame:
    return pd.read_parquet(path)


def sealed_repositories(path: Path = ROLES_FILE) -> set[str]:
    """Projects locked until the single final evaluation.

    From the dataset's roles file (m3-v2) if present, else from config (v4: jsoup).
    """
    if not path.exists():
        return set(SEALED_REPOSITORIES_BY_VERSION.get(DATASET_VERSION, ()))
    roles = json.loads(path.read_text(encoding="utf-8"))["roles"]
    return {repo for repo, role in roles.items() if role == SEALED_ROLE}


def select_features(manifest: dict, families: tuple[str, ...] | None = None) -> list[str]:
    """Feature columns from the manifest, optionally restricted to evidence families.

    `families=("git",)` keeps `git_*` columns. The action column is always kept:
    it is the question being asked, not evidence. `None` keeps every feature.
    """
    features = list(manifest["feature_columns"])
    assert_no_forbidden(features, manifest)
    if families is None:
        return features

    unknown = set(families) - set(FEATURE_FAMILIES)
    if unknown:
        raise ValueError(f"unknown feature families {sorted(unknown)}; known: {FEATURE_FAMILIES}")
    prefixes = tuple(f"{family}_" for family in families)
    return [f for f in features if f == ACTION_FEATURE or f.startswith(prefixes)]


def available_families(manifest: dict) -> tuple[str, ...]:
    """Evidence families that actually have columns in this dataset version."""
    features = manifest["feature_columns"]
    return tuple(fam for fam in FEATURE_FAMILIES if any(f.startswith(f"{fam}_") for f in features))


def assert_no_forbidden(features: list[str], manifest: dict) -> None:
    leaked = set(features) & (set(manifest["forbidden_columns"]) | {manifest["label_column"]})
    if leaked:
        raise LeakageError(f"post-change columns used as features: {sorted(leaked)}")


def encode_labels(labels: pd.Series) -> np.ndarray:
    unknown = set(labels.unique()) - set(CLASSES)
    if unknown:
        raise ValueError(f"unknown labels {sorted(unknown)}")
    return labels.map({name: i for i, name in enumerate(CLASSES)}).to_numpy()


def get_split(df: pd.DataFrame, manifest: dict, name: str, features: list[str],
              final: bool = False, include_sealed: bool = False,
              repos: set[str] | None = None) -> Split:
    """Rows of one split, optionally restricted to some projects.

    Test/holdout require `final=True` (look once). Sealed projects
    additionally require `include_sealed=True`, which itself requires `final=True`.
    """
    if name in FINAL_SPLITS and not final:
        raise LeakageError(f"'{name}' is a final evaluation split; pass final=True only in the final run")
    if include_sealed and not final:
        raise LeakageError("sealed projects can only be opened in the final run")
    if name not in (*DEVELOPMENT_SPLITS, *FINAL_SPLITS):
        raise ValueError(f"unknown split {name!r}")
    assert_no_forbidden(features, manifest)

    rows = df[df[manifest["split_column"]] == name]
    if not include_sealed:
        rows = rows[~rows["repo_id"].isin(sealed_repositories())]
    if repos is not None:
        rows = rows[rows["repo_id"].isin(repos)]
    rows = rows.sort_values("as_of", kind="stable")
    return Split(
        name=name,
        X=rows[features].astype(float),
        y=encode_labels(rows[manifest["label_column"]]),
        groups=rows[GROUP_COLUMN].to_numpy(),
        frame=rows,
    )


def final_evaluation_sets() -> dict[str, dict]:
    """Named final evaluation sets -> `get_split` arguments.

    "test" and "holdout" as before (holdout excludes sealed projects); a dataset
    with sealed projects adds "sealed", opened only here, in the single final run.
    """
    sets = {"test": {"name": "test"}, "holdout": {"name": "holdout"}}
    sealed = sealed_repositories()
    if sealed:
        sets["sealed"] = {"name": "holdout", "include_sealed": True, "repos": sealed}
    return sets


def get_final_set(df: pd.DataFrame, manifest: dict, set_name: str, features: list[str]) -> Split:
    split = get_split(df, manifest, features=features, final=True, **final_evaluation_sets()[set_name])
    return Split(set_name, split.X, split.y, split.groups, split.frame)
