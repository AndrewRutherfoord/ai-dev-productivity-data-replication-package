from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ARIMAX_CSV = Path("churn_arimax_summary.csv")
TTEST_CSV = Path("churn_paired_ttest_summary.csv")
OUTPUT_DIR = Path("arimax_result_plots")

# keep weird characters away from file names (for saving plots)
def sanitize_filename(text: str) -> str:
    return (text.lower().replace("/", "_").replace(" ", "_").replace("-", "_").replace("(", "").replace(")", ""))


# sort the groups alphabetically and add "All" at the end
def sort_groups(groups: Iterable[str]) -> list[str]:
    # set gets rid of duplicates
    groups = sorted(set(groups))
    if "All" in groups:
        groups = [g for g in groups if g != "All"] + ["All"]
    return groups


# define order for metrics shown in plots
# other metrics can be added at the end and they will be sorted alphabetically
def default_metric_order(metrics: Iterable[str]) -> list[str]:
    preferred = [
        "gross_churn",
        "net_added",
        "net_removed",
        "net_negative_commits",
        "add_delete_ratio",
        "total_commits",
        "files_touched_per_commit",
        "files_touched",
        "churn",
        "net_modified",
        "is_net_negative",
    ]

    metrics_set = set(metrics)
    ordered = [m for m in preferred if m in metrics_set]
    remaining = sorted(metrics_set - set(ordered))
    return ordered + remaining


# compute figure size based on number of groups and metrics, with some minimum size
def compute_figsize(num_cols: int, num_rows: int, base_w: float = 1.4, base_h: float = 0.5, min_w: float = 8, min_h: float = 4) -> tuple[float, float]:
    return max(min_w, num_cols * base_w), max(min_h, num_rows * base_h)


# create a heatmap with values shown in cells
def make_heatmap(df: pd.DataFrame, title: str, cbar_label: str, output_path: Path, cmap: str = "viridis", value_fmt: str = ".2f") -> None:
    if df.empty:
        print(f"Warning: No data to plot for {title}")
        return
    
    data = df.to_numpy(dtype=float)
    fig_w, fig_h = compute_figsize(df.shape[1], df.shape[0], base_w=1.6, base_h=0.7)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(data, aspect="auto", interpolation="nearest", cmap=cmap)

    ax.set_xticks(np.arange(df.shape[1]))
    ax.set_yticks(np.arange(df.shape[0]))
    ax.set_xticklabels(df.columns, rotation=45, ha="right")
    ax.set_yticklabels(df.index)
    ax.set_title(title)

    finite_vals = data[np.isfinite(data)]
    threshold = (finite_vals.max() + finite_vals.min()) / 2 if finite_vals.size else 0.5

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            label = "NA" if np.isnan(val) else format(val, value_fmt)
            text_color = "white" if (not np.isnan(val) and val > threshold) else "black"
            ax.text(j, i, label, ha="center", va="center", color=text_color, fontsize=9)
    
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


# save heatmaps
def save_arimax_heatmaps(arimax_df: pd.DataFrame, outdir: Path, suffix: str = "") -> None:
    metric_order = default_metric_order(arimax_df["metric"].unique())
    group_order = sort_groups(arimax_df["group"].unique())

    for value_col, title_stub in [
        ("post_sig_pct", "ARIMAX post-significance percentage"),
        ("trend_sig_pct", "ARIMAX trend-significance percentage"),
    ]:
        pivot_df = arimax_df.pivot(index="metric", columns="group", values=value_col)
        pivot_df = pivot_df.reindex(index=metric_order, columns=group_order)

        make_heatmap(
            pivot_df,
            title=f"{title_stub}{suffix}",
            cbar_label=value_col,
            output_path=outdir / f"heatmap_{sanitize_filename(value_col)}{sanitize_filename(suffix)}.png",
        )


def main() -> None:

    arimax_df = pd.read_csv(ARIMAX_CSV)
    ttest_df = pd.read_csv(TTEST_CSV)

    required_arimax_cols = {
        "group",
        "metric",
        "post_sig_pct",
        "trend_sig_pct",
        "median_coef_post",
        "median_coef_trend",
    }
    required_ttest_cols = {
        "group",
        "metric",
        "delay",
        "mean_diff",
        "p_value",
        "significant",
        "period",
    }

    missing_arimax = required_arimax_cols - set(arimax_df.columns)
    missing_ttest = required_ttest_cols - set(ttest_df.columns)

    if missing_arimax:
        raise ValueError(f"Missing ARIMAX columns: {sorted(missing_arimax)}")
    if missing_ttest:
        raise ValueError(f"Missing t-test columns: {sorted(missing_ttest)}")

    save_arimax_heatmaps(arimax_df, OUTPUT_DIR)

    arimax_all = arimax_df[arimax_df["group"] == "All"].copy()

    if not arimax_all.empty:
        save_arimax_heatmaps(arimax_all, OUTPUT_DIR, suffix=" (All group)")
    else:
        print("No 'All' rows found in ARIMAX summary; skipping All-group ARIMAX plots.")

    print("Done.")

if __name__ == "__main__":
    main()