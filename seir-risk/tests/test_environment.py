"""Phase 0 smoke tests: the environment can import and validate the shared output contract."""

import json

import pytest

from app.schema import RiskAssessment
from risk.config import CLASSES, PROJECT_ROOT

EXAMPLE = PROJECT_ROOT / "contracts" / "examples" / "risk_assessment.json"
needs_contracts = pytest.mark.skipif(not EXAMPLE.exists(), reason="shared contracts/ folder not checked out")


@needs_contracts
def test_contract_example_is_valid():
    RiskAssessment.model_validate(json.loads(EXAMPLE.read_text(encoding="utf-8")))


@needs_contracts
def test_contract_rejects_scores_not_summing_to_one():
    bad = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    bad["class_scores"] = {"LOW": 0.5, "MEDIUM": 0.5, "HIGH": 0.5}
    with pytest.raises(ValueError):
        RiskAssessment.model_validate(bad)


def test_class_order_matches_contract_enum():
    from app.schema import RiskClass

    assert set(CLASSES) == {member.value for member in RiskClass}


def test_ml_libraries_import():
    import shap  # noqa: F401
    import sklearn  # noqa: F401
    import xgboost  # noqa: F401
