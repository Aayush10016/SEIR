"""Ablation study (main report §6.13, §9.4): the value of each evidence family.

Rules for a valid ablation, all enforced here:
  * identical splits (the dataset's own split column);
  * identical model family and tuning grid for every feature set;
  * identical metrics;
  * every feature set is reported, including the ones that do not help.

Feature sets are every combination of the evidence families present in the
dataset, plus "action only" (no evidence at all) as the floor. With v1 only the
`git` family exists; when `static_*` columns arrive the loop grows by itself.
"""

from itertools import combinations

import numpy as np
import pandas as pd

from risk.config import APPLICATION_REPOSITORIES
from risk.data import Split, available_families, get_final_set, get_split, select_features
from risk.evaluate import bootstrap_ci, macro_f1, paired_bootstrap
from risk.models import evaluate_on, tune

ACTION_ONLY = "action_only"


def feature_sets(manifest: dict) -> dict[str, tuple[str, ...]]:
    families = available_families(manifest)
    sets = {ACTION_ONLY: ()}
    for size in range(1, len(families) + 1):
        for combo in combinations(families, size):
            sets["+".join(combo)] = combo
    return sets


def _subsets(split: Split) -> dict[str, np.ndarray]:
    """Row masks for per-project scores, plus the pooled application projects.

    The config clue can only be non-zero in applications, so its value must be
    judged there too, not only in the library-dominated overall score.
    """
    repos = split.frame["repo_id"].to_numpy()
    masks = {repo: repos == repo for repo in sorted(set(repos))}
    apps = np.isin(repos, list(APPLICATION_REPOSITORIES))
    if apps.any():
        masks["applications"] = apps
    return masks


def run_ablation(df: pd.DataFrame, manifest: dict, model_family: str,
                 eval_splits: tuple[str, ...] = ("validation",), final: bool = False) -> list[dict]:
    rows, predictions = [], {}
    for name, families in feature_sets(manifest).items():
        features = select_features(manifest, families)
        train = get_split(df, manifest, "train", features)
        validation = get_split(df, manifest, "validation", features)
        model = tune(model_family, train, validation)
        row = {"feature_set": name, "features": features, "model_family": model_family,
               "params": model.params, "splits": {}}
        for split_name in eval_splits:
            if split_name == "validation":
                split = validation
            elif final:
                split = get_final_set(df, manifest, split_name, features)
            else:
                raise ValueError(f"'{split_name}' is a final evaluation set; pass final=True")
            metrics = evaluate_on(model.estimator, split)
            pred = model.predict(split.X)
            metrics["macro_f1_ci"] = bootstrap_ci(split.y, pred, split.groups)
            metrics["subsets"] = {
                name: {"n": int(mask.sum()), "macro_f1": macro_f1(split.y[mask], pred[mask])}
                for name, mask in _subsets(split).items()
            }
            row["splits"][split_name] = metrics
            predictions[(name, split_name)] = (split, pred)
        rows.append(row)
    _add_paired_comparisons(rows, predictions)
    return rows


def _add_paired_comparisons(rows: list[dict], predictions: dict) -> None:
    """Each feature set vs the same set without one family (e.g. git+config vs git), paired."""
    names = {row["feature_set"] for row in rows}
    for row in rows:
        parts = row["feature_set"].split("+")
        if len(parts) < 2:
            continue
        for dropped in parts:
            reference = "+".join(p for p in parts if p != dropped)
            if reference not in names:
                continue
            for split_name, metrics in row["splits"].items():
                split, pred = predictions[(row["feature_set"], split_name)]
                _, ref_pred = predictions[(reference, split_name)]
                comparisons = {}
                for subset, mask in _subsets(split).items():
                    if subset == "applications" or len(set(split.frame["repo_id"])) == 1:
                        comparisons[subset] = paired_bootstrap(
                            split.y[mask], pred[mask], ref_pred[mask], split.groups[mask])
                comparisons["all"] = paired_bootstrap(split.y, pred, ref_pred, split.groups)
                metrics.setdefault("vs", {})[f"minus_{dropped}"] = comparisons
