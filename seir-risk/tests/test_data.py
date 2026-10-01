"""The leakage guards must fail loudly. These tests use a tiny synthetic table, not the real dataset."""

import pandas as pd
import pytest

from risk.data import LeakageError, available_families, get_split, select_features

MANIFEST = {
    "feature_columns": ["action_is_delete", "git_recent_commit_count", "static_fan_in"],
    "forbidden_columns": ["label_spread"],
    "label_column": "label",
    "split_column": "split",
}


def make_df() -> pd.DataFrame:
    return pd.DataFrame({
        "repo_id": ["a/a"] * 4,
        "commit_sha": ["a", "b", "c", "d"],
        "as_of": pd.to_datetime(["2020-01-02", "2020-01-01", "2021-01-01", "2022-01-01"], utc=True),
        "action_is_delete": [0, 1, 0, 0],
        "git_recent_commit_count": [1.0, 2.0, 3.0, 4.0],
        "static_fan_in": [5.0, None, 1.0, 2.0],
        "label_spread": [0, 4, 1, 0],
        "label": ["LOW", "HIGH", "MEDIUM", "LOW"],
        "split": ["train", "train", "validation", "test"],
    })


def test_families_filter_by_prefix_and_keep_action():
    assert select_features(MANIFEST, ("git",)) == ["action_is_delete", "git_recent_commit_count"]
    assert select_features(MANIFEST, ("static",)) == ["action_is_delete", "static_fan_in"]
    assert select_features(MANIFEST) == MANIFEST["feature_columns"]


def test_unknown_family_rejected():
    with pytest.raises(ValueError):
        select_features(MANIFEST, ("gitt",))


def test_available_families():
    assert available_families(MANIFEST) == ("static", "git")


def test_forbidden_column_in_manifest_features_is_caught():
    bad = {**MANIFEST, "feature_columns": [*MANIFEST["feature_columns"], "label_spread"]}
    with pytest.raises(LeakageError):
        select_features(bad)


def test_forbidden_column_passed_directly_is_caught():
    with pytest.raises(LeakageError):
        get_split(make_df(), MANIFEST, "train", ["git_recent_commit_count", "label_spread"])


def test_label_as_feature_is_caught():
    with pytest.raises(LeakageError):
        get_split(make_df(), MANIFEST, "train", ["label"])


def test_final_split_locked_by_default():
    features = select_features(MANIFEST)
    with pytest.raises(LeakageError):
        get_split(make_df(), MANIFEST, "test", features)
    assert len(get_split(make_df(), MANIFEST, "test", features, final=True).y) == 1


def test_split_is_time_ordered_and_encoded():
    split = get_split(make_df(), MANIFEST, "train", select_features(MANIFEST))
    assert list(split.groups) == ["b", "a"]  # sorted by as_of
    assert list(split.y) == [2, 0]  # HIGH, LOW
    assert split.X["static_fan_in"].isna().sum() == 1  # unknown stays NaN


def test_sealed_project_is_locked(monkeypatch):
    import risk.data as data

    monkeypatch.setattr(data, "sealed_repositories", lambda: {"secret/repo"})
    df = make_df()
    df["repo_id"] = ["a/a", "a/a", "a/a", "secret/repo"]
    df.loc[3, "split"] = "holdout"
    features = select_features(MANIFEST)
    assert len(get_split(df, MANIFEST, "holdout", features, final=True).y) == 0
    with pytest.raises(LeakageError):
        get_split(df, MANIFEST, "holdout", features, include_sealed=True)
    opened = get_split(df, MANIFEST, "holdout", features, final=True, include_sealed=True)
    assert list(opened.frame["repo_id"]) == ["secret/repo"]


def test_repo_filter():
    df = make_df()
    df["repo_id"] = ["a/a", "b/b", "a/a", "a/a"]
    split = get_split(df, MANIFEST, "train", select_features(MANIFEST), repos={"a/a"})
    assert list(split.groups) == ["a"]
