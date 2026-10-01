"""Packaging and live inference: features for one component -> a validated RiskAssessment.

A packaged model is a folder:
    model.joblib         the fitted estimator (+ optional calibrator, + SHAP background)
    model_manifest.json  feature list and order, class order, versions, calibration status

Loading fails loudly if the manifest and the estimator disagree, if the model was
trained with a different feature spec than the shared `seir_features` one, or if
the installed ML libraries differ from the ones used for training (a pickled
model can silently change behaviour across library versions).

Evidence is turned into model inputs by `seir_features.evidence_to_features`,
the SAME function the dataset builder uses, so training and live prediction
cannot compute features differently.

Only load model files you produced yourself: joblib files are pickles and can run code.
"""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import seir_features
from app.schema import ChangeAction, RiskAssessment
from risk.config import ACTION_FEATURE, CLASSES, EXPLANATION_TARGET
from risk.explain import RiskExplainer, top_features

MODEL_FILE = "model.joblib"
MANIFEST_FILE = "model_manifest.json"
PINNED_LIBRARIES = ("scikit-learn", "xgboost", "numpy")


class ModelMismatchError(RuntimeError):
    """The packaged model cannot be trusted with the current inputs or environment."""


def library_versions() -> dict[str, str]:
    return {lib: version(lib) for lib in PINNED_LIBRARIES}


def _minor(v: str) -> str:
    return ".".join(v.split(".")[:2])


def save_model(model_dir: Path, estimator, calibrator, background: pd.DataFrame, manifest: dict) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"estimator": estimator, "calibrator": calibrator, "background": background},
                model_dir / MODEL_FILE)
    manifest = {**manifest, "libraries": library_versions()}
    (model_dir / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


@dataclass
class RiskPredictor:
    estimator: object
    calibrator: object | None
    manifest: dict
    explainer: RiskExplainer

    @property
    def features(self) -> list[str]:
        return self.manifest["feature_columns"]

    @classmethod
    def load(cls, model_dir: Path) -> "RiskPredictor":
        manifest = json.loads((Path(model_dir) / MANIFEST_FILE).read_text(encoding="utf-8"))
        bundle = joblib.load(Path(model_dir) / MODEL_FILE)

        if tuple(manifest["classes"]) != CLASSES:
            raise ModelMismatchError(f"class order {manifest['classes']} != {CLASSES}")
        if list(bundle["background"].columns) != manifest["feature_columns"]:
            raise ModelMismatchError("model features differ from manifest feature_columns")
        trained_spec = manifest.get("feature_spec_version")
        if trained_spec != seir_features.FEATURE_SPEC_VERSION:
            raise ModelMismatchError(f"model trained with feature spec {trained_spec}, "
                                     f"seir_features is {seir_features.FEATURE_SPEC_VERSION}; retrain")
        if tuple(manifest["feature_columns"]) != seir_features.FEATURE_COLUMNS:
            raise ModelMismatchError("model feature order differs from seir_features.FEATURE_COLUMNS")
        for lib, trained in manifest["libraries"].items():
            installed = version(lib)
            if _minor(installed) != _minor(trained):
                raise ModelMismatchError(f"{lib} {installed} installed, model trained with {trained}")

        calibrator = bundle["calibrator"] if manifest["is_calibrated"] else None
        # The manifest records what contributions mean; older manifests fall back to config.
        explainer = RiskExplainer(bundle["estimator"], bundle["background"],
                                  is_xgboost=manifest["model_family"] == "xgb",
                                  target=manifest.get("explanation_target", EXPLANATION_TARGET))
        return cls(bundle["estimator"], calibrator, manifest, explainer)

    def _row(self, features: Mapping[str, float | None], action: ChangeAction) -> pd.DataFrame:
        # DEPRECATE has no training examples; it is treated as MODIFY.
        is_delete = int(action is ChangeAction.DELETE)
        if ACTION_FEATURE in features and int(features[ACTION_FEATURE]) != is_delete:
            raise ModelMismatchError(f"{ACTION_FEATURE}={features[ACTION_FEATURE]} contradicts action {action}")
        values = {**features, ACTION_FEATURE: is_delete}
        # A key that is absent is a pipeline bug (training/serving skew); an
        # unknown value must be passed explicitly as None / NaN.
        missing = [f for f in self.features if f not in values]
        if missing:
            raise ModelMismatchError(f"features not supplied (pass None if unknown): {missing}")
        row = {f: (np.nan if values[f] is None else float(values[f])) for f in self.features}
        return pd.DataFrame([row], columns=self.features)

    def predict(self, features: Mapping[str, float | None], repo_id: str, component_id: str,
                action: ChangeAction | str) -> RiskAssessment:
        action = ChangeAction(action)
        X = self._row(features, action)

        raw = self.estimator.predict_proba(X)[0]
        # The class is the tuned (class-balanced) decision; scores are probabilities
        # only if calibration was verified on the final splits.
        scores = self.calibrator.predict_proba(X)[0] if self.calibrator is not None else raw
        scores = scores / scores.sum()  # exact distribution for the contract's sum check
        contributions = self.explainer.contributions(X)[0]

        return RiskAssessment(
            repo_id=repo_id,
            component_id=component_id,
            action=action,
            risk_class=CLASSES[int(raw.argmax())],
            class_scores={name: float(s) for name, s in zip(CLASSES, scores)},
            is_calibrated=self.calibrator is not None,
            top_features=top_features(X.iloc[0], contributions),
            model_version=self.manifest["model_version"],
            feature_spec_version=self.manifest["feature_spec_version"],
        )

    def predict_from_evidence(self, evidence: Iterable, repo_id: str, component_id: str,
                              action: ChangeAction | str) -> RiskAssessment:
        """Evidence for ONE component (JSON dicts or EvidenceItems) -> RiskAssessment.

        Uses the shared `seir_features` conversion: missing or unknown evidence is NaN.
        """
        row = seir_features.evidence_to_features(evidence, action=ChangeAction(action).value)
        return self.predict(row, repo_id, component_id, action)
