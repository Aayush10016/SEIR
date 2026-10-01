"""The one-time final evaluation on test (temporal) and holdout (unseen project).

Run from seir-risk/:  python -m scripts.final_evaluation

Nothing here may change the model: every choice (features, model, hyperparameters,
thresholds, calibration method) was fixed by scripts.train on train + validation.
This script only measures, and verifies the calibration claim (`is_calibrated`).

It refuses to run twice: looking at test results, changing something and looking
again is how test sets silently turn into validation sets. `--rerun` exists for
a genuine pipeline bug; document the reason if you ever use it.
"""

import argparse
import json
import logging
import sys

import joblib
import numpy as np

from risk.ablation import run_ablation
from risk.config import (
    CLASSES,
    FINAL_REPORTS_DIR,
    MAX_ECE_FOR_CALIBRATED,
    MODELS_DIR,
    RANDOM_SEED,
    SHAP_ANALYSIS_ROWS,
)
from risk.data import Split, final_evaluation_sets, get_final_set, load_cases, load_manifest
from risk.evaluate import (
    bootstrap_ci,
    classification_metrics,
    paired_bootstrap,
    probability_metrics,
    reliability_curve,
)
from risk.explain import RISK_UP, RiskExplainer
from risk.pipeline import DevelopmentRun, all_predictors, score_split
from risk.plots import (
    confusion_matrix_plot,
    interval_plot,
    reliability_plot,
    shap_dependence_plot,
    shap_importance_plot,
)
from risk.predictor import MANIFEST_FILE, MODEL_FILE
from risk.reporting import label_distribution, metrics_table, write_json
from scripts.ablation import ablation_markdown
from scripts.train import DEVELOPMENT_BUNDLE

RESULTS_FILE = FINAL_REPORTS_DIR / "final_results.json"
SET_DESCRIPTIONS = {
    "test": "test — newest period of each training project",
    "holdout": "holdout — unseen project(s), results seen before (v1 final)",
    "sealed": "sealed — unseen project(s), never evaluated before this run",
}
FINAL_SETS = tuple(final_evaluation_sets())

log = logging.getLogger("final")


def latest_model_dir():
    manifests = sorted(MODELS_DIR.glob(f"*/{MANIFEST_FILE}"))
    if not manifests:
        raise SystemExit("no packaged model; run `python -m scripts.train` first")
    return manifests[-1].parent


def high_recall_by_cause(split: Split, y_pred: np.ndarray) -> dict:
    """Error analysis with post-change columns (allowed here: they are not model inputs).

    HIGH has two causes: a later bug fix traced by SZZ, or spread >= 4. Which one
    does the model detect? Git history might see coupling but not future bugs.
    """
    frame = split.frame
    high = split.y == CLASSES.index("HIGH")
    by_spread = high & (frame["label_spread"].to_numpy() >= 4)
    bug_only = high & ~by_spread
    out = {}
    for name, mask in (("spread_ge_4", by_spread), ("szz_bug_only", bug_only)):
        n = int(mask.sum())
        out[name] = {"n": n, "recall_high": float((y_pred[mask] == CLASSES.index("HIGH")).mean()) if n else None}
    return out


def per_action(split: Split, y_pred: np.ndarray) -> dict:
    out = {}
    for action in ("MODIFY", "DELETE"):
        mask = (split.frame["action"] == action).to_numpy()
        if mask.any():
            m = classification_metrics(split.y[mask], y_pred[mask])
            out[action] = {"n": m["n"], "macro_f1": m["macro_f1"], "accuracy": m["accuracy"],
                           "recall": {c: m["per_class"][c]["recall"] for c in CLASSES}}
    return out


def shap_summary(explainer: RiskExplainer, split: Split, features: list[str]) -> tuple[dict, np.ndarray, np.ndarray]:
    n = min(SHAP_ANALYSIS_ROWS, len(split.y))
    sample = split.X.sample(n, random_state=RANDOM_SEED)
    values = explainer.contributions(sample)
    summary = {}
    for i, feature in enumerate(features):
        x, c = sample[feature].to_numpy(), values[:, i]
        varies = np.nanstd(x) > 0 and np.std(c) > 0
        summary[feature] = {
            "mean_abs_contribution": float(np.abs(c).mean()),
            # Spearman-like direction: does a larger value push risk up (+) or down (-)?
            "direction": float(np.corrcoef(np.argsort(np.argsort(x)), np.argsort(np.argsort(c)))[0, 1])
            if varies else 0.0,
        }
    return summary, sample.to_numpy(), values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rerun", action="store_true", help="overwrite existing final results (document why)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    sys.stdout.reconfigure(encoding="utf-8")

    if RESULTS_FILE.exists() and not args.rerun:
        raise SystemExit(f"final results already exist ({RESULTS_FILE}); test/holdout are evaluated once")

    model_dir = latest_model_dir()
    manifest_path = model_dir / MANIFEST_FILE
    model_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bundle = joblib.load(model_dir / MODEL_FILE)
    run: DevelopmentRun = joblib.load(model_dir / DEVELOPMENT_BUNDLE)
    selected_name = model_manifest["model_family"]
    calibrator = bundle["calibrator"]
    features = model_manifest["feature_columns"]
    if features != run.features:
        raise SystemExit("development bundle and packaged model disagree on features")

    manifest, df = load_manifest(), load_cases()
    # Global analysis always uses the fixed risk-up axis: "larger value -> riskier"
    # is only meaningful on one direction (per-prediction output may differ).
    explainer = RiskExplainer(bundle["estimator"], bundle["background"],
                              is_xgboost=selected_name == "xgb", target=RISK_UP)
    results: dict = {"model_version": model_manifest["model_version"], "splits": {}}

    for split_name in FINAL_SETS:
        log.info("evaluating %s ...", split_name)
        split = get_final_set(df, manifest, split_name, features)
        predictions = {name: p.predict(split.X) for name, p in all_predictors(run).items()}
        metrics = score_split(run, split)
        ci = {name: bootstrap_ci(split.y, pred, split.groups) for name, pred in predictions.items()}
        paired = {name: paired_bootstrap(split.y, predictions[selected_name], pred, split.groups)
                  for name, pred in predictions.items() if name != selected_name}

        raw = bundle["estimator"].predict_proba(split.X)
        calibrated = calibrator.predict_proba(split.X) if calibrator is not None else raw
        calibration = {"uncalibrated": probability_metrics(split.y, raw),
                       "calibrated": probability_metrics(split.y, calibrated)}
        curves = {name: {c: reliability_curve(split.y, p, i) for i, c in enumerate(CLASSES)}
                  for name, p in (("uncalibrated", raw), ("calibrated", calibrated))}

        selected_pred = predictions[selected_name]
        shap_stats, shap_x, shap_values = shap_summary(explainer, split, features)

        results["splits"][split_name] = {
            "n": int(len(split.y)),
            "repositories": sorted(set(split.frame["repo_id"])),
            "commits": int(len(set(split.groups))),
            "label_distribution": label_distribution(split.y),
            "metrics": metrics,
            "macro_f1_ci": ci,
            "paired_vs_selected": paired,
            "calibration": calibration,
            "reliability": curves,
            "per_action": per_action(split, selected_pred),
            "high_recall_by_cause": high_recall_by_cause(split, selected_pred),
            "shap": shap_stats,
        }

        out = FINAL_REPORTS_DIR / split_name
        for name in (selected_name, "rule_baseline"):
            confusion_matrix_plot(metrics[name]["confusion_matrix"], f"{name} - {split_name}",
                                  out / f"confusion_{name}.png")
        reliability_plot(curves, f"{model_manifest['model_version']} reliability - {split_name}",
                         out / "reliability.png")
        interval_plot([{"label": n, **ci[n]} for n in predictions], f"Macro-F1 with 95% CI - {split_name}",
                      "Macro-F1 (bootstrap over commits)", out / "macro_f1.png")
        shap_importance_plot(features, shap_values, f"What drives risk-up - {split_name}",
                             out / "shap_importance.png")
        top = sorted(shap_stats, key=lambda f: -shap_stats[f]["mean_abs_contribution"])[:2]
        for feature in top:
            i = features.index(feature)
            shap_dependence_plot(shap_x[:, i], shap_values[:, i], feature, f"{feature} - {split_name}",
                                 out / f"shap_dependence_{feature}.png")

    # --- verify the calibration claim -----------------------------------------------
    verified = calibrator is not None and all(
        results["splits"][s]["calibration"]["calibrated"]["ece"] <= MAX_ECE_FOR_CALIBRATED
        and results["splits"][s]["calibration"]["calibrated"]["brier"]
        <= results["splits"][s]["calibration"]["uncalibrated"]["brier"]
        for s in FINAL_SETS)
    model_manifest["is_calibrated"] = bool(verified)
    model_manifest["calibration_verification"] = {
        "rule": f"calibrated ECE <= {MAX_ECE_FOR_CALIBRATED} and Brier not worse than uncalibrated, "
                f"on every final split",
        "passed": bool(verified),
        "by_split": {s: results["splits"][s]["calibration"] for s in FINAL_SETS},
    }
    manifest_path.write_text(json.dumps(model_manifest, indent=2), encoding="utf-8")
    results["is_calibrated"] = bool(verified)
    log.info("calibration verified: %s", verified)

    # --- ablation on the final splits, same model family and grid ---------------------------
    log.info("ablation on final splits ...")
    ablation = run_ablation(df, manifest, selected_name, eval_splits=("validation", *FINAL_SETS), final=True)
    results["ablation"] = ablation

    write_json(RESULTS_FILE, results)
    write_markdown(results, model_manifest, ablation)
    log.info("final results written to %s", FINAL_REPORTS_DIR)


def write_markdown(results: dict, model_manifest: dict, ablation: list[dict]) -> None:
    selected = model_manifest["model_family"]
    sections = []
    for split_name, r in results["splits"].items():
        paired = "\n".join(
            f"| {selected} − {n} | {p['difference']:+.3f} | {p['ci_low']:+.3f} to {p['ci_high']:+.3f} "
            f"| {p['share_a_better']:.0%} |" for n, p in r["paired_vs_selected"].items())
        cal = "\n".join(f"| {n} | {m['log_loss']:.3f} | {m['brier']:.3f} | {m['ece']:.3f} |"
                        for n, m in r["calibration"].items())
        actions = "\n".join(f"| {a} | {m['n']} | {m['macro_f1']:.3f} | "
                            + " | ".join(f"{m['recall'][c]:.2f}" for c in CLASSES) + " |"
                            for a, m in r["per_action"].items())
        causes = "\n".join(f"| {k} | {v['n']} | {v['recall_high']:.2f} |" if v["recall_high"] is not None
                           else f"| {k} | 0 | — |" for k, v in r["high_recall_by_cause"].items())
        shap_rows = "\n".join(
            f"| `{f}` | {s['mean_abs_contribution']:.3f} | {s['direction']:+.2f} |"
            for f, s in sorted(r["shap"].items(), key=lambda kv: -kv[1]["mean_abs_contribution"]))
        repos = ", ".join(r["repositories"])
        sections.append(f"""## {SET_DESCRIPTIONS[split_name]}

Projects: {repos}

{r['n']} cases from {r['commits']} commits · {r['label_distribution']}

{metrics_table(r['metrics'], r['macro_f1_ci'])}

**Paired bootstrap (same resampled commits):**

| Comparison | Δ macro-F1 | 95% CI | Resamples where {selected} wins |
|---|---|---|---|
{paired}

**Calibration of `{selected}` scores:**

| Scores | Log loss | Brier | ECE |
|---|---|---|---|
{cal}

**Per action (`{selected}`):**

| Action | n | Macro-F1 | Recall LOW | Recall MEDIUM | Recall HIGH |
|---|---|---|---|---|---|
{actions}

**Which HIGH cases are detected? (`{selected}`)**

| HIGH because of | n | Recall HIGH |
|---|---|---|
{causes}

**SHAP on the risk-up axis** ({SHAP_ANALYSIS_ROWS}-row sample; direction = rank correlation of value with
contribution, + means "larger value → riskier"):

| Feature | Mean \\|contribution\\| | Direction |
|---|---|---|
{shap_rows}

Figures: `{split_name}/`
""")
    FINAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (FINAL_REPORTS_DIR / "FINAL.md").write_text(f"""# Final evaluation — `{results['model_version']}`

Evaluated once. All choices were fixed on train + validation beforehand.

**`is_calibrated` = {str(results['is_calibrated']).lower()}** (rule: calibrated ECE ≤ {MAX_ECE_FOR_CALIBRATED} and Brier not worse than
uncalibrated, on test and holdout).

{''.join(sections)}
## Ablation (same model family `{selected}`, same grid, same splits)

{ablation_markdown(ablation, ('validation', *FINAL_SETS))}
""", encoding="utf-8")


if __name__ == "__main__":
    main()
