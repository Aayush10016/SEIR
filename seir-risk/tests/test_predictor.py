"""The packaged model must produce valid RiskAssessments and refuse inputs it cannot trust.

Needs a model packaged for the current shared feature spec (`python -m scripts.train`);
skipped otherwise.
"""

import json
import math
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import pytest
import seir_features

from app.schema import Availability, ChangeAction, EvidenceItem, Provenance, RiskAssessment, Source
from risk.config import EXPLANATION_TARGETS, MODELS_DIR
from risk.explain import RiskExplainer, risk_up_score
from risk.predictor import MANIFEST_FILE, MODEL_FILE, ModelMismatchError, RiskPredictor

def _spec(model_dir):
    return json.loads((model_dir / MANIFEST_FILE).read_text(encoding="utf-8")).get("feature_spec_version")


ALL_MODEL_DIRS = sorted(p.parent for p in MODELS_DIR.glob(f"*/{MANIFEST_FILE}"))
MODEL_DIRS = [d for d in ALL_MODEL_DIRS if _spec(d) == seir_features.FEATURE_SPEC_VERSION]
OLD_MODEL_DIRS = [d for d in ALL_MODEL_DIRS if _spec(d) != seir_features.FEATURE_SPEC_VERSION]
pytestmark = pytest.mark.skipif(not MODEL_DIRS, reason="no model for the current feature spec; run scripts.train")

REPO, COMPONENT = "apache/commons-lang", "org.apache.commons.lang3.Validate"
# A real test-split case (commons-lang Validate).
ROW_A = {
    "git_recent_commit_count": 1, "git_historical_commit_count": 108, "git_days_since_last_change": 79,
    "git_unique_contributors": 22, "git_lines_added": 5138, "git_lines_deleted": 3858,
    "git_total_churn": 8996, "git_churn_ratio": 0.0001, "git_co_change_count": 45,
    "config_config_reference_count": 0,
}


@pytest.fixture(scope="module")
def predictor() -> RiskPredictor:
    return RiskPredictor.load(MODEL_DIRS[-1])


@pytest.fixture(scope="module")
def background() -> pd.DataFrame:
    return joblib.load(MODEL_DIRS[-1] / MODEL_FILE)["background"]


def test_prediction_is_a_valid_contract(predictor):
    result = predictor.predict(ROW_A, REPO, COMPONENT, "MODIFY")
    RiskAssessment.model_validate(result.model_dump())  # round-trips through the contract
    assert result.model_version == predictor.manifest["model_version"]
    assert result.feature_spec_version == seir_features.FEATURE_SPEC_VERSION
    assert 0 < len(result.top_features) <= 5
    assert all(f.feature in predictor.features for f in result.top_features)


@pytest.mark.parametrize("target", EXPLANATION_TARGETS)
def test_contributions_are_additive(predictor, background, target):
    """SHAP additivity: contributions sum to f(x) minus the average f over the background."""
    explainer = RiskExplainer(predictor.estimator, background, is_xgboost=False, target=target)
    X = predictor._row(ROW_A, ChangeAction.MODIFY)
    sample = pd.DataFrame(explainer._explainer.masker.data, columns=predictor.features)
    proba_x = predictor.estimator.predict_proba(X)
    proba_bg = predictor.estimator.predict_proba(sample)
    if target == "risk_up":
        expected = risk_up_score(proba_x)[0] - risk_up_score(proba_bg).mean()
    else:
        k = proba_x.argmax(axis=1)[0]
        expected = proba_x[0, k] - proba_bg[:, k].mean()
    assert explainer.contributions(X)[0].sum() == pytest.approx(expected, abs=1e-6)


def test_packaged_explainer_is_additive(predictor, background):
    """The explainer actually shipped (whatever the model family) must add up exactly."""
    X = predictor._row(ROW_A, ChangeAction.MODIFY)
    contributions = predictor.explainer.contributions(X)[0]
    proba_x = predictor.estimator.predict_proba(X)
    base = predictor.explainer._explainer(X, silent=True).base_values[0]
    k = proba_x.argmax(axis=1)[0]
    target = proba_x[0, k] if predictor.explainer.target == "predicted_class" else risk_up_score(proba_x)[0]
    base_k = np.asarray(base)[k] if np.ndim(base) else base
    assert contributions.sum() + base_k == pytest.approx(target, abs=1e-4)


def test_explanations_are_deterministic(predictor):
    """Same evidence -> same reasons (main report §7.5, explanation consistency)."""
    first = predictor.predict(ROW_A, REPO, COMPONENT, "MODIFY").top_features
    second = predictor.predict(ROW_A, REPO, COMPONENT, "MODIFY").top_features
    assert first == second


def test_prediction_is_fast_enough_for_the_dashboard(predictor):
    import time
    started = time.perf_counter()
    predictor.predict(ROW_A, REPO, COMPONENT, "MODIFY")
    assert time.perf_counter() - started < 2.0


def test_packaged_model_uses_manifest_target(predictor):
    assert predictor.explainer.target == predictor.manifest["explanation_target"]


def test_targets_differ_for_a_non_high_prediction(predictor, background):
    """For a LOW/MEDIUM prediction, the two targets must explain different quantities."""
    X = predictor._row(ROW_A, ChangeAction.MODIFY)
    by_target = {t: RiskExplainer(predictor.estimator, background, False, t).contributions(X)[0]
                 for t in EXPLANATION_TARGETS}
    assert not np.allclose(*by_target.values())


def test_delete_changes_action_feature(predictor):
    modify = predictor.predict(ROW_A, REPO, COMPONENT, "MODIFY")
    delete = predictor.predict(ROW_A, REPO, COMPONENT, "DELETE")
    assert modify.class_scores != delete.class_scores


def test_deprecate_is_treated_as_modify(predictor):
    modify = predictor.predict(ROW_A, REPO, COMPONENT, "MODIFY")
    deprecate = predictor.predict(ROW_A, REPO, COMPONENT, "DEPRECATE")
    assert deprecate.class_scores == modify.class_scores
    assert deprecate.action.value == "DEPRECATE"


def test_missing_feature_key_is_refused(predictor):
    incomplete = {k: v for k, v in ROW_A.items() if k != "git_co_change_count"}
    with pytest.raises(ModelMismatchError):
        predictor.predict(incomplete, REPO, COMPONENT, "MODIFY")


def test_unknown_value_is_accepted_as_none(predictor):
    result = predictor.predict({**ROW_A, "git_co_change_count": None}, REPO, COMPONENT, "MODIFY")
    unknown = [f for f in result.top_features if f.feature == "git_co_change_count"]
    assert all(f.value is None for f in unknown)


def test_contradicting_action_feature_is_refused(predictor):
    with pytest.raises(ModelMismatchError):
        predictor.predict({**ROW_A, "action_is_delete": 1}, REPO, COMPONENT, "MODIFY")


def test_model_for_an_older_feature_spec_is_refused():
    """The v1 model (9 git features, no spec) must not silently run on features@1.0 inputs."""
    if not OLD_MODEL_DIRS:
        pytest.skip("no older model packaged")
    with pytest.raises(ModelMismatchError):
        RiskPredictor.load(OLD_MODEL_DIRS[0])


def _evidence(column: str, value, available: bool = True) -> EvidenceItem:
    source, evidence_type = column.split("_", 1)
    return EvidenceItem(
        repo_id=REPO, snapshot="a" * 40, component_id=COMPONENT, source=Source(source.upper()),
        evidence_type=evidence_type, value=value if available else None, unit="count",
        availability=Availability.AVAILABLE if available else Availability.UNKNOWN,
        as_of=datetime(2026, 3, 21, tzinfo=timezone.utc),
        provenance=Provenance(note="test") if available else Provenance(),
        extraction_method="test@0.0.0",
    )


def test_predict_from_evidence_matches_feature_path(predictor):
    items = [_evidence(k, v) for k, v in ROW_A.items()]
    from_evidence = predictor.predict_from_evidence(items, REPO, COMPONENT, "MODIFY")
    from_features = predictor.predict(ROW_A, REPO, COMPONENT, "MODIFY")
    assert from_evidence.class_scores == pytest.approx(from_features.class_scores)


def test_json_evidence_matches_object_evidence(predictor):
    """The Evidence Service returns JSON; the shared function must treat it identically."""
    items = [_evidence(k, v) for k, v in ROW_A.items()]
    as_json = [item.model_dump(mode="json") for item in items]
    a = predictor.predict_from_evidence(as_json, REPO, COMPONENT, "DELETE")
    b = predictor.predict_from_evidence(items, REPO, COMPONENT, "DELETE")
    assert a.class_scores == pytest.approx(b.class_scores)


def test_unknown_evidence_becomes_nan_not_zero(predictor):
    items = [_evidence(k, v) for k, v in ROW_A.items() if k != "git_co_change_count"]
    items.append(_evidence("git_co_change_count", None, available=False))
    as_unknown = predictor.predict_from_evidence(items, REPO, COMPONENT, "MODIFY")
    as_none = predictor.predict({**ROW_A, "git_co_change_count": math.nan}, REPO, COMPONENT, "MODIFY")
    assert as_unknown.class_scores == pytest.approx(as_none.class_scores)
