"""Static report figures (PNG). One style for all figures: thin marks, recessive axes.

Colours come from a validated reference palette (categorical slots 1-2 pass the
colour-blind separation checks); text always uses ink colours, never series colours.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # file output only; no display needed
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from risk.config import CLASSES  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES = ("#2a78d6", "#eb6834")  # categorical slots 1, 2 (fixed order)
SEQUENTIAL = LinearSegmentedColormap.from_list("blue", ["#f0f5fc", "#9ec5f4", "#2a78d6", "#104281"])
DPI = 160


def _style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BASELINE)
    ax.tick_params(colors=MUTED, labelcolor=INK_SECONDARY, labelsize=8)
    ax.grid(color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def _save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.patch.set_facecolor(SURFACE)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)


def confusion_matrix_plot(matrix: list[list[int]], title: str, path: Path) -> None:
    """Counts with row percentages (share of each true class). Colour = row share."""
    counts = np.array(matrix)
    shares = counts / np.maximum(counts.sum(axis=1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(3.8, 3.4))
    ax.imshow(shares, cmap=SEQUENTIAL, vmin=0, vmax=1)
    for i in range(len(CLASSES)):
        for j in range(len(CLASSES)):
            dark_cell = shares[i, j] > 0.55
            ax.text(j, i, f"{counts[i, j]}\n{shares[i, j]:.0%}", ha="center", va="center", fontsize=8,
                    color=SURFACE if dark_cell else INK)
    ax.set_xticks(range(len(CLASSES)), CLASSES)
    ax.set_yticks(range(len(CLASSES)), CLASSES)
    ax.set_xlabel("Predicted", color=INK_SECONDARY, fontsize=9)
    ax.set_ylabel("True", color=INK_SECONDARY, fontsize=9)
    ax.tick_params(colors=MUTED, labelcolor=INK_SECONDARY, labelsize=8, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(title, color=INK, fontsize=10, loc="left")
    _save(fig, path)


def reliability_plot(curves: dict[str, dict[str, dict]], title: str, path: Path) -> None:
    """Small multiples, one per class. `curves[series_name][class_name]` = reliability_curve() output."""
    fig, axes = plt.subplots(1, len(CLASSES), figsize=(9, 3.2), sharey=True)
    for ax, class_name in zip(axes, CLASSES):
        _style(ax)
        ax.plot([0, 1], [0, 1], color=MUTED, linewidth=1, linestyle=(0, (3, 3)))
        for color, (series_name, per_class) in zip(SERIES, curves.items()):
            c = per_class[class_name]
            ax.plot(c["mean_score"], c["observed_frequency"], color=color, linewidth=2,
                    marker="o", markersize=4, label=series_name)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(class_name, color=INK, fontsize=9, loc="left")
        ax.set_xlabel("Mean predicted score", color=INK_SECONDARY, fontsize=8)
    axes[0].set_ylabel("Observed frequency", color=INK_SECONDARY, fontsize=8)
    if len(curves) > 1:
        axes[0].legend(frameon=False, fontsize=8, labelcolor=INK_SECONDARY, loc="upper left")
    fig.suptitle(title, color=INK, fontsize=10, x=0.02, ha="left")
    _save(fig, path)


def interval_plot(rows: list[dict], title: str, xlabel: str, path: Path,
                  reference: float | None = None, reference_label: str = "") -> None:
    """Point estimate with confidence interval per row: {'label', 'estimate', 'ci_low', 'ci_high'}."""
    fig, ax = plt.subplots(figsize=(6, 0.45 * len(rows) + 1.0))
    _style(ax)
    ax.grid(axis="y", visible=False)
    y = np.arange(len(rows))[::-1]
    for yi, row in zip(y, rows):
        ax.plot([row["ci_low"], row["ci_high"]], [yi, yi], color=SERIES[0], linewidth=2,
                solid_capstyle="round")
        ax.plot(row["estimate"], yi, "o", color=SERIES[0], markersize=7,
                markeredgecolor=SURFACE, markeredgewidth=1.5)
        ax.text(row["ci_high"] + 0.005, yi, f"{row['estimate']:.3f}", va="center", fontsize=8, color=INK_SECONDARY)
    if reference is not None:
        ax.axvline(reference, color=MUTED, linewidth=1, linestyle=(0, (3, 3)))
        ax.text(reference, y.max() + 0.6, reference_label, fontsize=7, color=MUTED, ha="center")
    ax.set_yticks(y, [r["label"] for r in rows])
    ax.set_xlabel(xlabel, color=INK_SECONDARY, fontsize=8)
    ax.set_ylim(-0.7, len(rows) - 0.1)
    ax.set_title(title, color=INK, fontsize=10, loc="left")
    _save(fig, path)


def shap_importance_plot(features: list[str], contributions: np.ndarray, title: str, path: Path) -> None:
    """Mean |SHAP| per feature (bars), with the mean signed effect as a text annotation."""
    mean_abs = np.abs(contributions).mean(axis=0)
    order = np.argsort(mean_abs)
    fig, ax = plt.subplots(figsize=(6, 0.35 * len(features) + 1.0))
    _style(ax)
    ax.grid(axis="y", visible=False)
    ax.barh(np.arange(len(order)), mean_abs[order], color=SERIES[0], height=0.6)
    for yi, idx in enumerate(order):
        ax.text(mean_abs[idx], yi, f"  {mean_abs[idx]:.3f}", va="center", fontsize=7, color=INK_SECONDARY)
    ax.set_yticks(np.arange(len(order)), [features[i] for i in order])
    ax.set_xlabel("Mean |contribution| to risk-up log-odds (HIGH vs LOW)", color=INK_SECONDARY, fontsize=8)
    ax.set_title(title, color=INK, fontsize=10, loc="left")
    _save(fig, path)


def shap_dependence_plot(feature_values: np.ndarray, contributions: np.ndarray, feature: str,
                         title: str, path: Path) -> None:
    """How one feature's value moves the risk-up score (log x-axis: counts are skewed)."""
    fig, ax = plt.subplots(figsize=(5, 3.2))
    _style(ax)
    ax.axhline(0, color=BASELINE, linewidth=1)
    ax.scatter(np.log1p(feature_values), contributions, s=10, color=SERIES[0], alpha=0.35, linewidths=0)
    ax.set_xlabel(f"log(1 + {feature})", color=INK_SECONDARY, fontsize=8)
    ax.set_ylabel("Contribution to risk-up", color=INK_SECONDARY, fontsize=8)
    ax.set_title(title, color=INK, fontsize=10, loc="left")
    _save(fig, path)
