"""Small helpers to write results as JSON (for machines) and Markdown tables (for the report)."""

import json
from pathlib import Path

import numpy as np

from risk.config import CLASSES


def _jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(obj), indent=2), encoding="utf-8")


def fmt(value, digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def metrics_table(results: dict[str, dict], ci: dict[str, dict] | None = None) -> str:
    """One row per predictor: macro-F1 (with CI), per-class recall, accuracy, log loss, ECE."""
    header = ("| Predictor | Macro-F1 | 95% CI | Recall LOW | Recall MEDIUM | Recall HIGH "
              "| Accuracy | Log loss | Brier | ECE |")
    lines = [header, "|" + "---|" * (header.count("|") - 1)]
    for name, m in results.items():
        interval = ci.get(name) if ci else None
        ci_text = f"{interval['ci_low']:.3f}–{interval['ci_high']:.3f}" if interval else "—"
        recalls = [fmt(m["per_class"][c]["recall"], 2) for c in CLASSES]
        lines.append(f"| {name} | {fmt(m['macro_f1'])} | {ci_text} | " + " | ".join(recalls)
                     + f" | {fmt(m['accuracy'])} | {fmt(m.get('log_loss'))} | {fmt(m.get('brier'))}"
                     + f" | {fmt(m.get('ece'))} |")
    return "\n".join(lines)


def label_distribution(y: np.ndarray) -> str:
    counts = np.bincount(y, minlength=len(CLASSES))
    return ", ".join(f"{c} {n} ({n / counts.sum():.0%})" for c, n in zip(CLASSES, counts))
