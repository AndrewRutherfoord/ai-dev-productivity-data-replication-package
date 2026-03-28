# %% Setup
# NOTE: Apparely changes in imported modules are not reloaded when you re-run this cell. You need to restart the jupyter kernet and run all cells again to see changes in interact_with_neo4j.py or arimax.py. Very irritating...
import logging
import pandas as pd
import numpy as np
from interact_with_neo4j import (
    RepoInfo,
    get_file_extension_mappings,
    iter_repos,
    load_df,
)
from arimax import fit_best_arimax, extract_results
from collections import defaultdict

from multithread import execute_tasks_in_parallel

RESULT_FILE = "./productivity/arimax_results.csv"
SIGNIFICANCE_LEVEL = 0.1

logging.getLogger("statsmodels").setLevel(logging.ERROR)
logging.getLogger("pmdarima").setLevel(logging.ERROR)


FILE_EXTENSIONS_MAP = get_file_extension_mappings()


FILE_EXTENSION_GROUPINGS = defaultdict(list)
for k, v in FILE_EXTENSIONS_MAP.items():
    FILE_EXTENSION_GROUPINGS[v].append(k)
FILE_EXTENSION_GROUPINGS["All"].extend(FILE_EXTENSIONS_MAP.keys())

EXTENSIONS = list(FILE_EXTENSIONS_MAP.keys())
print(FILE_EXTENSION_GROUPINGS)


# %% Setup functions for processing data fetched from Neo4j + adding fields for stat testing.

QUERY = """
MATCH (r:Repository)--(b:Branch)--(commit:Commit)-[m:MODIFIED]-(f:File)
WHERE any(ext IN $extensions WHERE f.name ENDS WITH ext) AND r.url = $repoUrl
WITH r, commit, m, f,
     datetime(replace(commit.date, ' ', 'T')) AS dt
WITH r, commit, m, f,
     date.truncate('week', dt) AS week
RETURN commit.hash AS hash,
    sum(coalesce(m.added_lines, 0)) AS total_added,
    sum(coalesce(m.deleted_lines, 0)) AS total_removed,
    sum(coalesce(m.added_lines, 0) + coalesce(m.deleted_lines, 0)) AS total_churn,
    sum(CASE WHEN m.added_lines > 0 AND m.deleted_lines > 0 THEN 1 ELSE 0 END) AS files_modified,
    sum(CASE WHEN m.added_lines > 0 AND m.deleted_lines = 0 THEN 1 ELSE 0 END) AS files_only_added,
    sum(CASE WHEN m.added_lines = 0 AND m.deleted_lines > 0 THEN 1 ELSE 0 END) AS files_only_deleted,
    count(m) AS files_touched,
    datetime(replace(commit.date, ' ', 'T')) AS date,
    commit.message AS message,
    commit.author AS author,
    week
ORDER BY date
"""

MIN_WEEKS = 4
MIN_COMMITS = 10


def _to_utc_naive(value):
    # The joy of date time conversions...

    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if isinstance(ts, pd.Series):
        return ts.dt.tz_convert(None)
    if isinstance(ts, pd.DatetimeIndex):
        return ts.tz_convert(None)
    if isinstance(ts, pd.Timestamp):
        return ts.tz_convert(None)
    return ts

def enrich_df(repo : RepoInfo, df : pd.DataFrame, week_col = "week", is_weekly = False) -> pd.DataFrame | None:
    """Adds the week offsets which are used for the ARIMAX model and applies a limit of 1.5x more weeks before than after artifact creation to avoid skew."""

    df = df.reset_index()
    df["week"] = _to_utc_naive(df[week_col].apply(lambda d: d.isoformat()))

    artifact_dt = _to_utc_naive(repo.artifact_creation_date)
    artifact_week = artifact_dt.to_period("W").start_time

    df = df.sort_values("week").set_index("week")

    if is_weekly:
        df = df.asfreq("W-MON").fillna(0)
        artifact_week = artifact_dt.to_period("W-MON").start_time

    # group into before/after artifact creation
    df["week_offset"] = (df.index - artifact_week).days // 7 # type: ignore

    post_weeks = df[df["week_offset"] >= 0].shape[0]
    pre_weeks = df[df["week_offset"] < 0].shape[0]

    if post_weeks < MIN_WEEKS or pre_weeks < MIN_WEEKS:
        return None

    # Trim to only have 1.5x more weeks before than after. 
    max_pre_weeks = int(1.5 * post_weeks)

    df = df[
        (df["week_offset"] >= -max_pre_weeks) &
        (df["week_offset"] < post_weeks)
    ]

    df["time"] = range(len(df))

    post_pos = np.flatnonzero(df["week_offset"].to_numpy() >= 0)
    if len(post_pos) == 0:
        return None
    t0 = int(post_pos[0])

    df["post"] = (df["time"] >= t0).astype(int)
    df["time_after"] = (df["time"] - t0).clip(lower=0)

    return df

def enrich_commit_df(repo: RepoInfo, df: pd.DataFrame) -> pd.DataFrame | None:
    # Adds commit_offset: negative = before artifact, 0+ = after artifact.
    df["dt"] = _to_utc_naive(df["date"].apply(lambda d: d.isoformat()))
    df = df.sort_values("dt").reset_index(drop=True)

    # Find the artifact commit position
    artifact_idx = df.index[df["hash"] == repo.artifact_creation_commit]

    if len(artifact_idx) == 0:
        # Artifact commit not in this filtered set (as a result of the file extension filtering)
        artifact_dt = _to_utc_naive(repo.artifact_creation_date)
        artifact_pos = df[df["dt"] <= artifact_dt].shape[0]
    else:
        artifact_pos = artifact_idx[0]

    df["commit_offset"] = df.index - artifact_pos

    post_commits = df[df["commit_offset"] >= 0].shape[0]
    pre_commits = df[df["commit_offset"] < 0].shape[0]

    if post_commits < MIN_COMMITS or pre_commits < MIN_COMMITS:
        return None

    df["post"] = (df["commit_offset"] >= 0).astype(int)

    return df

def get_repo_churn_data(repo : RepoInfo, extensions : list[str]) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    result = load_df(QUERY, {"extensions": extensions, "repoUrl": repo.url})
    if result.empty:
        return (None, None)

    # Per-commit churn metrics
    result["churn"] = result[["total_added", "total_removed"]].sum(axis=1)  # added + removed

    result["net_modified"] = result[["total_added", "total_removed"]].min(axis=1)  # paired edits
    result["net_added"] = result["total_added"] - result["net_modified"]
    result["net_removed"] = result["total_removed"] - result["net_modified"]

    result["is_net_negative"] = result["net_removed"] > result["net_added"]

    # Group by week
    weekly = result.groupby("week").agg(
        gross_churn=("churn", "sum"),
        total_added=("total_added", "sum"),
        total_removed=("total_removed", "sum"),
        net_added=("net_added", "sum"),
        net_removed=("net_removed", "sum"),
        net_negative_commits=("is_net_negative", "sum"),
        total_commits=("hash", "count"),
        files_touched=("files_touched", "sum"),
    )


    # Derived ratios
    weekly["net_negative_commits"] = weekly["net_removed"] - weekly["net_added"] # How many of the commits remove more than they add
    weekly["add_delete_ratio"] = weekly["total_added"] / (weekly["total_removed"]).replace(0, 1)
    weekly["files_touched_per_commit"] = weekly["files_touched"] / weekly["total_commits"].replace(0, 1)

    weekly = enrich_df(repo, weekly, is_weekly=True)

    result = enrich_df(repo, result, is_weekly=False)
    if result is not None:
        result = enrich_commit_df(repo, result)

    return result, weekly

# This block is just for testing.
for es in FILE_EXTENSION_GROUPINGS.values():
    commit_df, weekly_df = get_repo_churn_data(next(iter_repos()), es)
    print(f"Processing extensions: {es}")
    if weekly_df is not None and not weekly_df.empty:
        print(f"Weekly")
        print(weekly_df.iloc[-1])
    if commit_df is not None and not commit_df.empty:
        print(f"Commits")
        print(commit_df.iloc[-1])
    break


# %% ! Run the Neo4j Queries and store it. Makes processing faster in Jupyter by not having to hit the DB again

commit_results : dict[tuple[str, str], pd.DataFrame]= {}
weekly_results : dict[tuple[str, str], pd.DataFrame]= {}

i = 0
total = len(list(iter_repos()))
for repo in iter_repos():
    for group, es in FILE_EXTENSION_GROUPINGS.items():
        commit_df, weekly_df = get_repo_churn_data(repo, es)
        if commit_df is not None and not commit_df.empty:
            commit_results[(repo.url, group)] = commit_df

        if weekly_df is not None and not weekly_df.empty:
            weekly_results[(repo.url, group)] = weekly_df
    i += 1
    logging.info(f"Processed {repo.url} ({i}/{total})")


# %% Run the SARMIMA on weekly data

results = {group: [] for group in FILE_EXTENSION_GROUPINGS.keys()}
weekly_metrics = [
    "gross_churn",              # total lines added + removed
    "net_added",                # lines added that are not removed in the same commit
    "net_removed",              # lines removed that are not added in the same commit
    "net_negative_commits",     # number of commits where net_removed > net_added
    "add_delete_ratio",         # ratio of total added to total removed lines 
    "total_commits",            # number of commits in the week, as a measure of activity
    "files_touched_per_commit"  # average number of files touched per commit, as a measure of edit intensity
]

def process_repo_weekly_metrics(repo : RepoInfo, group : str) -> list[dict]:
    try:
        results : list[dict] = []
        weekly_df = weekly_results.get((repo.url, group))

        if weekly_df is None or weekly_df.empty:
            # print(f"No data for {repo.url} with extensions {extensions}")
            return results

        for metric in weekly_metrics:
            # X = weekly_df[["post", "time_after"]]
            X = weekly_df[["time", "post", "time_after"]]

            result, order = fit_best_arimax(weekly_df[metric], X)

            if result is None or not result.mle_retvals["converged"]: # type: ignore
                logging.warning(f"ARIMAX model did not converge for {repo.url} with group {group} on {metric}. Skipping.")
                continue

            results.append({**extract_results(repo, result, order), "metric": metric})
        
        return results

    except Exception as e:
        logging.error(f"Failed for {repo.url}: {e}")
        return []

def handle_arimax(args, result):
    repo, group = args
    results[group].extend(result)
    logging.info(f"Processed {repo.url} ({group})")

tasks = [(repo, group) for repo in iter_repos() for group in FILE_EXTENSION_GROUPINGS]

# A little multithreading to speed things up a little
execute_tasks_in_parallel(tasks, process_repo_weekly_metrics, handle_arimax)

# %% Summary of ARIMA results

def compile_weekly_sarima_summary(results: dict[str, list[dict]], weekly_metrics: list[str]) -> pd.DataFrame:
    all_summaries = []

    for metric in weekly_metrics:
        for group, rows in results.items():
            if len(rows) == 0:
                continue

            results_df = pd.DataFrame(rows)
            results_df = results_df[results_df["metric"] == metric]

            if results_df.empty:
                continue

            post_sig = results_df["p_post"] < SIGNIFICANCE_LEVEL
            trend_sig = results_df["p_time_after"] < SIGNIFICANCE_LEVEL

            # Direction among significant repos
            post_pos_sig = post_sig & (results_df["coef_post"] > 0)
            post_neg_sig = post_sig & (results_df["coef_post"] < 0)

            trend_pos_sig = trend_sig & (results_df["coef_time_after"] > 0)
            trend_neg_sig = trend_sig & (results_df["coef_time_after"] < 0)

            all_summaries.append( {
                    "group": group,
                    "metric": metric,
                    "n": len(results_df),
                    "period": "weeks",
                    "post_sig_count": int(post_sig.sum()),
                    "post_sig_pct": float(post_sig.mean()),
                    "trend_sig_count": int(trend_sig.sum()),
                    "trend_sig_pct": float(trend_sig.mean()),

                    # Directional % of repos. 
                    "post_pos_sig_pct": float(post_pos_sig.mean()),
                    "post_neg_sig_pct": float(post_neg_sig.mean()),
                    "trend_pos_sig_pct": float(trend_pos_sig.mean()),
                    "trend_neg_sig_pct": float(trend_neg_sig.mean()),

                    # Direction among significant only
                    "post_pos_share_among_sig": float(
                        post_pos_sig.sum() / post_sig.sum()
                    )
                    if post_sig.sum() > 0
                    else np.nan,
                    "trend_pos_share_among_sig": float(
                        trend_pos_sig.sum() / trend_sig.sum()
                    )
                    if trend_sig.sum() > 0
                    else np.nan,

                    # Coefs
                    "mean_coef_post": float(results_df["coef_post"].mean()),
                    "median_coef_post": float(results_df["coef_post"].median()),
                    "mean_coef_trend": float(
                        results_df["coef_time_after"].mean()
                    ),
                    "median_coef_trend": float(
                        results_df["coef_time_after"].median()
                    ),

                })

    summary_df = pd.DataFrame(all_summaries)
    return summary_df

summary_df = compile_weekly_sarima_summary(results, weekly_metrics)
summary_df.to_csv("churn_arimax_summary.csv", index=False)

print(f"Saved {len(summary_df)} groups to churn_arimax_summary.csv")


# %% Run paired ttest on weekly data

from scipy import stats

def prepare_paired_ttest(df: pd.DataFrame, metric: str, delay: int = 0, offset_field: str = "week_offset") -> dict | None:
    pre = df[(df[offset_field] < -delay)][metric]
    post = df[(df[offset_field] >= delay)][metric]

    return {
        "pre_mean": pre.mean(),
        "post_mean": post.mean(),
        "diff": post.mean() - pre.mean(),
    }


def execute_paired_ttest(results : dict, metrics : list[str], delays : list[int], offset_field : str, extra_cols : dict = {}) -> list[dict]:

    ttest_results = []

    # When delay is 0 we are comparing all before artifact vs all after artifact. The delays are to allow for some time to settle in after the adoption of AI. In some visual plots we saw a spike in code output immediately after the artifact creation, so this allows us to account for this.
    for delay in delays:
        for group in FILE_EXTENSION_GROUPINGS:
            pairs = {metric: [] for metric in metrics}

            for repo in iter_repos():
                df = results.get((repo.url, group))
                if df is None or df.empty:
                    continue

                for metric in metrics:
                    result = prepare_paired_ttest(df, metric, delay=delay, offset_field=offset_field)
                    if result is not None:
                        pairs[metric].append({"repo": repo.url, **result})

            for metric in metrics:
                if len(pairs[metric]) < 5:
                    logging.warning(f"Not enough data for paired t-test for group {group} on metric {metric} with delay {delay}. Skipping.")
                    continue

                mdf = pd.DataFrame(pairs[metric])
                t_stat, p_value = stats.ttest_rel(mdf["post_mean"], mdf["pre_mean"])

                ttest_results.append({
                    "group": group,
                    "metric": metric,
                    "delay": delay,
                    "n_repos": len(mdf),
                    "mean_pre": mdf["pre_mean"].mean(),
                    "mean_post": mdf["post_mean"].mean(),
                    "mean_diff": mdf["diff"].mean(),
                    "median_diff": mdf["diff"].median(),
                    "t_stat": t_stat,
                    "p_value": p_value,
                    "significant": p_value < SIGNIFICANCE_LEVEL,
                    **extra_cols,
                })
    return ttest_results

weekly_ttest_results = execute_paired_ttest(weekly_results, weekly_metrics, [0, 2, 4], offset_field="week_offset", extra_cols={"period": "weeks"})

commit_metrics = ["files_touched", "churn", "net_added", "net_removed", "net_modified", "is_net_negative"]
commit_ttest_results = execute_paired_ttest(commit_results, commit_metrics, [0, 2, 4], offset_field="commit_offset", extra_cols={"period": "commits"})

ttest_df = pd.DataFrame(weekly_ttest_results + commit_ttest_results)
ttest_df.to_csv("churn_paired_ttest_summary.csv", index=False)
print(f"Saved {len(ttest_df)} rows")

# %% Plot the SARIMA results

import matplotlib.pyplot as plt
import numpy as np

def plot_sarima_significance(summary_df: pd.DataFrame, group: str = "All", output_path: str = "images/churn_sarima_significance.png"):
    df = summary_df[summary_df["group"] == group].copy()
    df = df.set_index("metric").reindex(weekly_metrics).dropna()

    x = np.arange(len(df))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))

    bars1 = ax.bar(x - width / 2, df["post_sig_pct"] * 100, width, label="Level change (post)", color="#4C72B0")
    bars2 = ax.bar(x + width / 2, df["trend_sig_pct"] * 100, width, label="Trend change (time_after)", color="#DD8452")

    ax.axhline(y=SIGNIFICANCE_LEVEL * 100, color="red", linestyle="--", linewidth=1, label=f"Significance threshold ({int(SIGNIFICANCE_LEVEL * 100)}%)")

    ax.set_xlabel("Metric")
    ax.set_ylabel("% of repos with significant effect")
    ax.set_title(f"SARIMA: Proportion of Repos with Significant Churn Effects — {group} files")
    ax.set_xticks(x)
    ax.set_xticklabels(df.index, rotation=30, ha="right")
    ax.set_ylim(0, 100)
    ax.legend()

    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 1, f"{h:.0f}%", ha="center", va="bottom", fontsize=8)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 1, f"{h:.0f}%", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.show()
    print(f"Saved chart to {output_path}")

plot_sarima_significance(summary_df)


# %%

def plot_trend_direction(
    summary_df: pd.DataFrame,
    group: str = "All",
    output_path: str = "images/churn_sarima_trend_direction.png",
):
    df = summary_df[summary_df["group"] == group].copy()
    df = df.set_index("metric").reindex(weekly_metrics).dropna()

    x = np.arange(len(df))
    width = 0.6

    pos = df["trend_pos_sig_pct"] * 100
    neg = df["trend_neg_sig_pct"] * 100

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x, pos, width, label="Significant positive trend change", color="#55A868")
    ax.bar(
        x,
        neg,
        width,
        bottom=pos,
        label="Significant negative trend change",
        color="#C44E52",
    )

    ax.set_xlabel("Metric")
    ax.set_ylabel("% of repos")
    ax.set_title(f"SARIMA: Direction of Trend Change — {group} files")
    ax.set_xticks(x)
    ax.set_xticklabels(df.index, rotation=30, ha="right")
    ax.set_ylim(0, 100)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.show()

plot_trend_direction(summary_df)

# %%
plot_trend_direction(summary_df, group="Bash", output_path="images/churn_sarima_trend_direction_bash.png")