"""Does more training data help? Same models, same tuning budget, same validation set; only
the training projects differ (commons-lang only, as in v1, versus every v2 training project).

Run from seir-risk/:  python -m scripts.experiment_more_data
"""

import sys

import numpy as np

from risk.config import DEV_REPORTS_DIR
from risk.data import load_cases, load_manifest
from risk.evaluate import bootstrap_ci, macro_f1, paired_bootstrap
from risk.models import MODEL_FAMILIES
from risk.pipeline import develop
from risk.reporting import write_json

V1_TRAINING = {"apache/commons-lang"}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    manifest, df = load_manifest(), load_cases()
    runs = {"commons-lang only": develop(df, manifest, train_repos=V1_TRAINING, with_baseline=False),
            "all v2 projects": develop(df, manifest, with_baseline=False)}
    val = runs["all v2 projects"].validation
    repos = sorted(set(val.frame["repo_id"]))

    results, lines = {}, []
    for family in MODEL_FAMILIES:
        preds = {name: run.models[family].predict(val.X) for name, run in runs.items()}
        paired = paired_bootstrap(val.y, preds["all v2 projects"], preds["commons-lang only"], val.groups)
        per_repo = {}
        for repo in repos:
            mask = (val.frame["repo_id"] == repo).to_numpy()
            per_repo[repo] = {name: macro_f1(val.y[mask], p[mask]) for name, p in preds.items()}
        results[family] = {
            name: {"train_rows": len(runs[name].train.y), "macro_f1": bootstrap_ci(val.y, p, val.groups)}
            for name, p in preds.items()
        } | {"paired_all_minus_lang": paired, "per_repo": per_repo}
        r = results[family]
        lines.append(f"| {family} | {r['commons-lang only']['macro_f1']['estimate']:.3f} "
                     f"| {r['all v2 projects']['macro_f1']['estimate']:.3f} "
                     f"| {paired['difference']:+.3f} ({paired['ci_low']:+.3f} to {paired['ci_high']:+.3f}) |")

    repo_lines = "\n".join(
        f"| {repo} | " + " | ".join(
            f"{results[f]['per_repo'][repo]['commons-lang only']:.3f} → {results[f]['per_repo'][repo]['all v2 projects']:.3f}"
            for f in MODEL_FAMILIES) + " |" for repo in repos)
    table = f"""# More training data (v2 validation, {len(val.y)} cases)

| Model | Trained on commons-lang only ({len(runs['commons-lang only'].train.y)} rows) | Trained on all v2 projects ({len(runs['all v2 projects'].train.y)} rows) | Δ macro-F1 (95% CI, paired) |
|---|---|---|---|
{chr(10).join(lines)}

Per project (macro-F1, lang-only → all):

| Project | {' | '.join(MODEL_FAMILIES)} |
|---|{'---|' * len(MODEL_FAMILIES)}
{repo_lines}
"""
    DEV_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (DEV_REPORTS_DIR / "MORE_DATA.md").write_text(table, encoding="utf-8")
    write_json(DEV_REPORTS_DIR / "more_data.json", results)
    print(table)


if __name__ == "__main__":
    main()
