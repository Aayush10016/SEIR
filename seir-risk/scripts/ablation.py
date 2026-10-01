"""Ablation study on the validation split (development). Final-split ablation runs in final_evaluation.

Run from seir-risk/:  python -m scripts.ablation [--model-family logreg|rf|xgb]
The model family defaults to the one selected by scripts.train (same model for every feature set).
"""

import argparse
import json
import sys

from risk.ablation import run_ablation
from risk.config import DEV_REPORTS_DIR, MODELS_DIR
from risk.data import load_cases, load_manifest
from risk.predictor import MANIFEST_FILE
from risk.reporting import write_json


def selected_family() -> str:
    manifests = sorted(MODELS_DIR.glob(f"*/{MANIFEST_FILE}"))
    if not manifests:
        raise SystemExit("no packaged model; run `python -m scripts.train` first")
    return json.loads(manifests[-1].read_text(encoding="utf-8"))["model_family"]


def ablation_markdown(rows: list[dict], split_names: tuple[str, ...]) -> str:
    """Overall + application-project macro-F1 per feature set, then paired differences."""
    head = " | ".join(f"{s} macro-F1 (95% CI) | {s} applications" for s in split_names)
    lines = [f"| Feature set | # features | {head} |",
             "|---|---|" + "---|---|" * len(split_names)]
    for row in rows:
        cells = []
        for s in split_names:
            m = row["splits"][s]
            ci = m["macro_f1_ci"]
            apps = m.get("subsets", {}).get("applications")
            cells.append(f"{m['macro_f1']:.3f} ({ci['ci_low']:.3f}–{ci['ci_high']:.3f})")
            cells.append(f"{apps['macro_f1']:.3f} (n={apps['n']})" if apps else "—")
        lines.append(f"| {row['feature_set']} | {len(row['features'])} | " + " | ".join(cells) + " |")

    paired = ["", "Paired differences (same resampled commits; + = the larger set is better):", "",
              "| Comparison | Split | Rows | Δ macro-F1 | 95% CI |", "|---|---|---|---|---|"]
    for row in rows:
        for s in split_names:
            for dropped, subsets in row["splits"][s].get("vs", {}).items():
                family = dropped.removeprefix("minus_")
                reference = "+".join(p for p in row["feature_set"].split("+") if p != family)
                for subset, d in subsets.items():
                    paired.append(f"| {row['feature_set']} − {reference} | {s} | {subset} "
                                  f"| {d['difference']:+.3f} | {d['ci_low']:+.3f} to {d['ci_high']:+.3f} |")
    return "\n".join(lines + (paired if len(paired) > 5 else []))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model-family", default=None)
    args = parser.parse_args()
    family = args.model_family or selected_family()

    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    rows = run_ablation(load_cases(), load_manifest(), family)
    write_json(DEV_REPORTS_DIR / "ablation_validation.json", rows)
    table = ablation_markdown(rows, ("validation",))
    (DEV_REPORTS_DIR / "ABLATION.md").write_text(
        f"# Ablation (validation, model family `{family}`)\n\n{table}\n", encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
