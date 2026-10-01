"""Train, select, calibrate and package the risk model. Uses train + validation only.

Run from seir-risk/:  python -m scripts.train

Outputs:
  models/<name>@<semver>/            packaged model (model.joblib + model_manifest.json)
  models/<name>@<semver>/development.joblib   every candidate, for the final evaluation
  local/reports/<version>/development/   validation results (JSON, Markdown, figures; git-ignored)
"""

import logging
from datetime import datetime, timezone

import joblib
import seir_features

from risk import calibrate
from risk.config import (
    CLASSES,
    DATASET_VERSION,
    DEV_REPORTS_DIR,
    EXPLANATION_TARGET,
    MODEL_SEMVER,
    MODELS_DIR,
    SELECTION_METRIC,
)
from risk.data import load_cases, load_manifest
from risk.evaluate import bootstrap_ci, paired_bootstrap, reliability_curve
from risk.models import VERSION_NAMES
from risk.pipeline import all_predictors, develop, score_split
from risk.plots import confusion_matrix_plot, reliability_plot
from risk.predictor import save_model
from risk.reporting import label_distribution, metrics_table, write_json

DEVELOPMENT_BUNDLE = "development.joblib"
CONTRIBUTION_MEANING = {
    "predicted_class": "SHAP contribution to P(predicted class) of the uncalibrated model; "
                       "positive = pushed towards the class in risk_class",
    "risk_up": "SHAP contribution to log P(HIGH) - log P(LOW) of the uncalibrated model; positive = riskier",
}

log = logging.getLogger("train")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    manifest = load_manifest()
    df = load_cases()
    # Training and serving must use the same feature spec (seir_features).
    dataset_spec = manifest.get("feature_spec_version")
    if dataset_spec != seir_features.FEATURE_SPEC_VERSION:
        raise SystemExit(f"dataset built with feature spec {dataset_spec}, "
                         f"seir_features is {seir_features.FEATURE_SPEC_VERSION}; rebuild the dataset")

    log.info("tuning references, rule baseline and models on train/validation ...")
    run = develop(df, manifest)
    val = run.validation
    selected = run.selected
    log.info("selected %s (validation %s = %.3f)", selected.family, SELECTION_METRIC,
             selected.validation[SELECTION_METRIC])

    # --- validation results, with commit-level uncertainty ---------------------
    results = score_split(run, val)
    predictions = {name: p.predict(val.X) for name, p in all_predictors(run).items()}
    ci = {name: bootstrap_ci(val.y, pred, val.groups) for name, pred in predictions.items()}
    paired = {name: paired_bootstrap(val.y, predictions[selected.family], pred, val.groups)
              for name, pred in predictions.items() if name != selected.family}

    # --- calibration: method chosen on validation with grouped folds ----------------
    method, calibrator, comparison = calibrate.choose_and_fit(selected.estimator, val)
    log.info("calibration method chosen on validation: %s", method)

    # --- package --------------------------------------------------------------------
    model_version = f"{VERSION_NAMES[selected.family]}@{MODEL_SEMVER}"
    model_dir = MODELS_DIR / model_version
    model_manifest = {
        "model_version": model_version,
        "model_family": selected.family,
        "params": selected.params,
        "feature_columns": run.features,
        "feature_spec_version": dataset_spec,
        "classes": list(CLASSES),
        "dataset_version": DATASET_VERSION,
        "label_rule_version": manifest["label_rule_version"],
        "dataset_repositories": manifest["repositories"],
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "selection": {"metric": SELECTION_METRIC, "split": "validation",
                      "scores": {f: m.validation[SELECTION_METRIC] for f, m in run.models.items()}},
        "calibration_method": method,
        "calibration_comparison_validation_oof": comparison,
        # False until the final evaluation verifies calibration on test AND holdout.
        "is_calibrated": False,
        "calibration_verification": "pending final evaluation",
        "risk_class_rule": "argmax of the uncalibrated, class-balanced model",
        "explanation_target": EXPLANATION_TARGET,
        "contribution_meaning": CONTRIBUTION_MEANING[EXPLANATION_TARGET],
        "deprecate_handling": "treated as MODIFY (action_is_delete = 0); no DEPRECATE training cases",
    }
    save_model(model_dir, selected.estimator, calibrator, run.train.X, model_manifest)
    joblib.dump(run, model_dir / DEVELOPMENT_BUNDLE)
    log.info("packaged %s", model_dir)

    # --- reports ----------------------------------------------------------------------
    write_json(DEV_REPORTS_DIR / "validation_results.json", {
        "model_version": model_version,
        "features": run.features,
        "metrics": results,
        "macro_f1_ci": ci,
        "paired_vs_selected": paired,
        "baseline_thresholds": run.baseline.thresholds_,
        "tuning_trials": {f: m.trials for f, m in run.models.items()},
        "calibration_comparison": comparison,
        "calibration_method": method,
    })
    for name, metrics in results.items():
        confusion_matrix_plot(metrics["confusion_matrix"], f"{name} - validation",
                              DEV_REPORTS_DIR / f"confusion_{name}.png")
    curves = {"uncalibrated": selected.predict_proba(val.X)}
    reliability_plot(
        {"uncalibrated": {c: reliability_curve(val.y, curves["uncalibrated"], i) for i, c in enumerate(CLASSES)}},
        f"{model_version} reliability - validation (in-sample for calibration, so uncalibrated only)",
        DEV_REPORTS_DIR / "reliability_validation.png",
    )

    paired_lines = "\n".join(
        f"| {selected.family} − {name} | {p['difference']:+.3f} | {p['ci_low']:+.3f} to {p['ci_high']:+.3f} "
        f"| {p['share_a_better']:.0%} |" for name, p in paired.items())
    calib_lines = "\n".join(f"| {m} | {c['log_loss']:.3f} | {c['brier']:.3f} | {c['ece']:.3f} |"
                            for m, c in comparison.items())
    (DEV_REPORTS_DIR / "VALIDATION.md").write_text(f"""# Development results (validation split only)

Dataset `{DATASET_VERSION}` · labels `{manifest['label_rule_version']}` · selected model **`{model_version}`**

- Train: {len(run.train.y)} cases ({label_distribution(run.train.y)})
- Validation: {len(val.y)} cases ({label_distribution(val.y)})
- Features ({len(run.features)}): {', '.join(f'`{f}`' for f in run.features)}

## Metrics on validation

95% CIs: bootstrap over commits ({len(set(val.groups))} commits).

{metrics_table(results, ci)}

Rule-baseline thresholds (validation-chosen): {run.baseline.thresholds_[0]:.3f}, {run.baseline.thresholds_[1]:.3f}

## Is the selected model really better? (paired bootstrap, validation)

| Comparison | Δ macro-F1 | 95% CI | Resamples where selected wins |
|---|---|---|---|
{paired_lines}

## Calibration choice (out-of-fold on validation, commit-grouped {calibrate.CALIBRATION_FOLDS}-fold)

| Method | Log loss | Brier | ECE |
|---|---|---|---|
{calib_lines}

Chosen: **{method}** (lowest log loss). `is_calibrated` stays false until verified on test and holdout.
""", encoding="utf-8")
    log.info("reports written to %s", DEV_REPORTS_DIR)


if __name__ == "__main__":
    main()
