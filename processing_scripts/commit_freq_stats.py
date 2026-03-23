from neo4j import GraphDatabase
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from scipy.stats import wilcoxon, kruskal
from statsmodels.stats.multitest import multipletests

from typing import Any, cast, Optional

HOST = "100.65.19.91"
URI = f"neo4j://{HOST}:7687"
USER = "neo4j"
PASSWORD = "neo4j123"
ARTIFACT_CSV = "agents_claude_artifact_creations.csv"

# change time window if deemed necessary
WEEKS_BEFORE = 30
WEEKS_AFTER = 30
# min number of repos for a language group to be included in the programming language analysis
MIN_REPOS_PER_GROUP = 10

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# get data from running cypher queries in  the neo4j db
def load_df(query:str) -> pd.DataFrame:
    with driver.session() as session:
        data = session.run(cast(Any, query)).data()
    return pd.DataFrame(data)


# load the AI artifact creation dates from CSV and build a lookup table
def artifact_date_lookup(csv_path: str = ARTIFACT_CSV) -> dict[tuple[str, str], str]:
    df = pd.read_csv(csv_path)
    # remove rows with missing repo url, branch or artifact creation date
    df = df.dropna(subset=["url", "branch", "artifact_creation_date"]).copy()
    # convert dates to pandas datetime format and remove any invalid ones
    df["artifact_creation_date"] = pd.to_datetime(df["artifact_creation_date"], errors="coerce")
    df = df.dropna(subset=["artifact_creation_date"])

    # if the same repo or ranch appears multiple times, take the earliest artifact creation date
    df = df.groupby(["url", "branch"], as_index=False)["artifact_creation_date"].min()
    # format the datetime as a string that can be parsed by neo4j
    df["iso"] = df["artifact_creation_date"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    return {(row["url"], row["branch"]): row["iso"] for _, row in df.iterrows()}


# given a repo and the lookup table, return the artifact creation date for the specific repo
def get_artifact_creation_date(repo, lookup: dict[tuple[str, str], str]) -> Optional[str]:
    key = (repo.url, repo.branch)
    if key in lookup:
        return lookup[key]
    return None


# map programming language label into broader groups for analysis
# we're taking the most dominant languages, then group everything else as "other"
def map_language_to_group(language: str) -> str:
    language = str(language).lower()

    if language in {"python", "py"}:
        return "Python"
    if language in {"javascript", "js", "typescript", "ts", "tsx"}:
        return "JavaScript/TypeScript"
    if language == "java":
        return "Java"
    if language in {"c", "cpp", "h"}:
        return "C/C++"
    if language == "go":
        return "Go"
    if language in {"html", "css"}:
        return "Web"
    return "Other"


# for a given repo, determine the dominant programmig language of that repo
def get_repo_dominant_language(repo_url: str, repo_branch: str) -> Optional[str]:
    # look at all modified files in the repo and determine the most common programming language based on file extensions
    query = f"""
    MATCH (r:Repository {{url: "{repo_url}"}})<-[:PART_OF]-(b:Branch {{name: "{repo_branch}"}})
    MATCH (b)<-[:IN_BRANCH]-(:Commit)-[:MODIFIED]->(f:File)
    WHERE f.name IS NOT NULL
    WITH
        CASE
            WHEN toLower(f.name) ENDS WITH ".py" THEN "python"
            WHEN toLower(f.name) ENDS WITH ".js" THEN "javascript"
            WHEN toLower(f.name) ENDS WITH ".ts" THEN "typescript"
            WHEN toLower(f.name) ENDS WITH ".java" THEN "java"
            WHEN toLower(f.name) ENDS WITH ".go" THEN "go"
            WHEN toLower(f.name) ENDS WITH ".c" THEN "c"
            WHEN toLower(f.name) ENDS WITH ".cpp" THEN "cpp"
            WHEN toLower(f.name) ENDS WITH ".h" THEN "h"
            WHEN toLower(f.name) ENDS WITH ".html" THEN "html"
            WHEN toLower(f.name) ENDS WITH ".css" THEN "css"
            ELSE NULL
        END AS language,
        f
    WHERE language IS NOT NULL
    RETURN language, count(DISTINCT f) AS file_count
    ORDER BY file_count DESC
    LIMIT 1
    """

    df = load_df(query)
    if df.empty:
        return None
    
    dominant_language = str(df.loc[0, "language"])
    return map_language_to_group(dominant_language)


# build analysis data, including AI artifact creation date, dominant language group, commits before/after artifact,
# commits per week before/after, change in commits per week, ratio after/before
def build_commit_frequency_repo_dataset(weeks_before: int = WEEKS_BEFORE, weeks_after: int = WEEKS_AFTER, csv_path: str = ARTIFACT_CSV) -> pd.DataFrame:
    from interact_with_neo4j import iter_repos

    # lookup table for artifact creation dates
    lookup = artifact_date_lookup(csv_path)
    rows = []

    # for all repos
    for repo in iter_repos():
        # get artifat creation date
        created_at = get_artifact_creation_date(repo, lookup)
        if not created_at:
            continue

        # define t0 as the artifact creation date, convert commit timestamps into neo4j parsable datetime,
        # compute day distance between the commit and t0 and filter commits within the time window (30 weeks in this case)
        # also week 0 (week of artifat creation) is included in the "after"
        query = f"""
        MATCH (r:Repository {{url: "{repo.url}"}})<-[:PART_OF]-(b:Branch {{name: "{repo.branch}"}})
        MATCH (b)<-[:IN_BRANCH]-(c:Commit)
        WHERE c.date IS NOT NULL
        WITH datetime("{created_at}") AS t0, datetime(replace(c.date, ' ', 'T')) AS dt
        WITH duration.inDays(t0, dt).days AS day_offset
        WHERE day_offset >= -{weeks_before}*7 AND day_offset <= {weeks_after}*7
        RETURN sum(CASE WHEN day_offset <0 THEN 1 ELSE 0 END) AS commits_before, sum(CASE WHEN day_offset >= 0 THEN 1 ELSE 0 END) AS commits_after
        """

        df = load_df(query)
        if df.empty:
            continue

        commits_before = int(df.loc[0, "commits_before"] or 0)
        commits_after = int(df.loc[0, "commits_after"] or 0)

        # calculate commits per week before/after
        commits_per_week_before = commits_before / weeks_before if weeks_before > 0 else np.nan
        commits_per_week_after = commits_after / weeks_after if weeks_after > 0 else np.nan

        # get repo dominant programming language group
        language_group = get_repo_dominant_language(repo.url, repo.branch)
        if language_group is None:
            language_group = "Other"
        
        # save data for specific repo in a row
        rows.append({
            "repo_key": f"{repo.url}::{repo.branch}",
            "repo_url": repo.url,
            "repo_branch": repo.branch,
            "artifact_creation_date": created_at,
            "language_group": language_group,
            "commits_before": commits_before,
            "commits_after": commits_after,
            "commits_per_week_before": commits_per_week_before,
            "commits_per_week_after": commits_per_week_after,
            "delta_commit_per_week": commits_per_week_after - commits_per_week_before,
            "ratio_after_before": (commits_per_week_after / commits_per_week_before if commits_per_week_before > 0 else np.nan),
        })

    repo_df = pd.DataFrame(rows)

    if repo_df.empty:
        print("No repo level commit frequency data collected")
        return repo_df
    
    # drop rows with missing commit freq data, just to be safe
    repo_df = repo_df.dropna(subset=["commits_per_week_before", "commits_per_week_after"])
    repo_df.to_csv("repo_commit_frequency_30w_before_after.csv", index=False)

    # 179 repos in this dataset as of now
    print(f"Saved repo level dataset: {len(repo_df)} repos")
    return repo_df
    

# run paired wilcoxon signed-rank test to compare commit freq before/after (pre/post data, probably not normally distributed)
def run_overall_commit_freq_wilcoxon(repo_df: pd.DataFrame) -> pd.DataFrame:
    df = repo_df.copy().dropna(subset=["commits_per_week_before", "commits_per_week_after"])

    if df.empty:
        print("No data for Wilcoxon test")
        return pd.DataFrame()
    
    # extract before, after data and calculate delta
    before = df["commits_per_week_before"]
    after = df["commits_per_week_after"]
    delta = after - before

    # only keep repos that have a change in commit frequency, since the ones with no difference
    # bring no meaning to the wilcoxon test
    nonzero_delta = delta[delta != 0]

    # in case all repos have 0 change in commit freq (highly unlikely)
    # we don't run the test and return default statistical values
    if len(nonzero_delta) == 0:
        result_df = pd.DataFrame([{
            "group": "Overall",
            "num_repos": len(df),
            "median_before": float(before.median()),
            "median_after": float(after.median()),
            "median_delta": float(delta.median()),
            "wilcoxon_statistic": np.nan,
            "wilcoxon_pvalue": np.nan,
            "effect_size_rbc": np.nan,
        }])
        result_df.to_csv("commit_frequency_overall_wilcoxon.csv", index=False)
        return result_df

    # we have data, we run the test and test whether the median paired difference is 0
    test = wilcoxon(before, after, zero_method="wilcox", alternative="two-sided")

    # calculate effect size,
    # pos means more repos increased than decreased in their commit freq, neg is the opposite
    n_pos = int((delta > 0).sum())
    n_neg = int((delta < 0).sum())
    effect_size_rbc = (n_pos - n_neg) / (n_pos + n_neg) if (n_pos + n_neg) > 0 else np.nan

    # save results
    result_df = pd.DataFrame([{
        "group": "Overall",
        "num_repos": len(df),
        "median_before": float(before.median()),
        "median_after": float(after.median()),
        "median_delta": float(delta.median()),
        "wilcoxon_statistic": float(test.statistic),
        "wilcoxon_pvalue": float(test.pvalue),
        "effect_size_rbc": float(effect_size_rbc) if not pd.isna(effect_size_rbc) else np.nan,
    }])

    result_df.to_csv("commit_frequency_overall_wilcoxon.csv", index=False)
    return result_df


# run the same paired wilcoxon test, but within each programming language group
def run_language_group_commit_freq_tests(repo_df: pd.DataFrame, min_repos_per_group: int = MIN_REPOS_PER_GROUP) -> pd.DataFrame:
    df = repo_df.copy().dropna(subset=["language_group"])
    # count repos in each group and keep the ones with at least MIN_REPOS_PER_GROUP
    group_counts = df["language_group"].value_counts()
    valid_groups = group_counts[group_counts >= min_repos_per_group].index.tolist()

    results = []

    # for each language group
    for group in valid_groups:
        # subset repos
        sub = df[df["language_group"] == group].copy()

        # extract before, after data and calculate delta
        before = sub["commits_per_week_before"]
        after = sub["commits_per_week_after"]
        delta = after - before
        # in case all repos have 0 change in commit freq (highly unlikely)
         # we don't run the test and return default statistical values
        nonzero_delta = delta[delta != 0]

        if len(nonzero_delta) == 0:
            results.append({
                "language_group": group,
                "num_repos": len(sub),
                "median_before": float(before.median()),
                "median_after": float(after.median()),
                "median_delta": float(delta.median()),
                "wilcoxon_statistic": np.nan,
                "wilcoxon_pvalue": np.nan,
                "effect_size_rbc": np.nan,
            })
            continue

        # we have data, we run the test and test whether the commit freq changed differently across language groups
        # here we ask if within {specific language group}, did the before and after freq change?
        test = wilcoxon(before, after, zero_method="wilcox", alternative="two-sided")

        # calculate effect size
        n_pos = int((delta > 0).sum())
        n_neg = int((delta < 0).sum())
        effect_size_rbc = (n_pos - n_neg) / (n_pos + n_neg) if (n_pos + n_neg) > 0 else np.nan

        results.append({
            "language_group": group,
            "num_repos": len(sub),
            "median_before": float(before.median()),
            "median_after": float(after.median()),
            "median_delta": float(delta.median()),
            "wilcoxon_statistic": float(test.statistic),
            "wilcoxon_pvalue": float(test.pvalue),
            "effect_size_rbc": float(effect_size_rbc) if not pd.isna(effect_size_rbc) else np.nan,
        })

    result_df = pd.DataFrame(results)

    if result_df.empty:
        print("No valid language groups for Wilcoxon tests")
        return result_df
    
    valid_mask = result_df["wilcoxon_pvalue"].notna()
    result_df["p_value_fdr_bh"] = np.nan
    result_df["reject_fdr_0_05"] = pd.Series([pd.NA]*len(result_df), dtype="boolean")

    # because we run several language tests, we correct for multile comparisons using benjamini-hochberg false discovery rate correction
    if valid_mask.any():
        reject, pvals_adj, _, _ = multipletests(result_df.loc[valid_mask, "wilcoxon_pvalue"], method="fdr_bh")
        result_df.loc[valid_mask, "p_value_fdr_bh"] = pvals_adj
        result_df.loc[valid_mask, "reject_fdr_0_05"] = reject
    
    # store results
    result_df = result_df.sort_values(["p_value_fdr_bh", "wilcoxon_pvalue"], na_position="last")
    result_df.to_csv("commit_frequency_language_group_wilcoxon_fdr.csv", index=False)

    return result_df


# test whether the size of the change in commit freq differs across language groups (is the delta between groups different?)
def run_commit_frequency_kruskal_by_language(repo_df: pd.DataFrame, min_repos_per_group: int = MIN_REPOS_PER_GROUP) -> pd.DataFrame:
    df = repo_df.copy().dropna(subset=["language_group", "delta_commit_per_week"])
    
    # count repos in each group and keep the ones with at least MIN_REPOS_PER_GROUP
    group_counts = df["language_group"].value_counts()
    valid_groups = group_counts[group_counts >= min_repos_per_group].index.tolist()

    if len(valid_groups) < 2:
        print("Not enough valid language groups for Kruskal-Wallis test")
        return pd.DataFrame()
    
    # create delta array per group
    grouped_deltas = [df.loc[df["language_group"] == group, "delta_commit_per_week"].values for group in valid_groups]
    
    # run kruskal wallis
    test = kruskal(*grouped_deltas)

    summary_rows = []
    # for each language group
    for group in valid_groups:
        # subset repos
        sub = df[df["language_group"] == group]
        # compute number of repos, the median delta and mean delta
        summary_rows.append({
            "language_group": group,
            "num_repos": len(sub),
            "median_delta": float(sub["delta_commit_per_week"].median()),
            "mean_delta": float(sub["delta_commit_per_week"].mean()),
        })
    
    # sort values by language group
    summary_df = pd.DataFrame(summary_rows).sort_values("language_group")
    # test results
    test_df = pd.DataFrame([{
        "test": "Kruskal-Wallis on delta_commit_per_week across language groups",
        "num_groups": len(valid_groups),
        "group_names": ", ".join(valid_groups),
        "statistic": float(test.statistic),
        "pvalue": float(test.pvalue),
    }])

    # save results
    summary_df.to_csv("commit_frequency_language_group_delta_summary.csv", index=False)
    test_df.to_csv("commit_frequency_kruskal_wallis_language_groups.csv", index=False)

    return test_df


# boxplot for delta (after - before) commits per week grouped by programming language
def plot_commit_freq_delta_by_language(repo_df: pd.DataFrame, min_repos_per_group: int = MIN_REPOS_PER_GROUP) -> None:
    df = repo_df.copy().dropna(subset=["language_group", "delta_commit_per_week"])

    group_counts = df["language_group"].value_counts()
    valid_groups = group_counts[group_counts >= min_repos_per_group].index.tolist()

    if len(valid_groups) == 0:
        print("No valid language groups for plotting")
        return
    
    plot_data = [df.loc[df["language_group"] == group, "delta_commit_per_week"].values for group in valid_groups]

    plt.figure(figsize=(10, 5))
    box = plt.boxplot(plot_data, tick_labels=valid_groups, patch_artist=True)

    for b in box["boxes"]:
        b.set_facecolor("#64B5CD")
    
    # horizontal line, groups above 0 have commit freq increased, below 0 have commit freq decreased after artifact creation
    plt.axhline(0, linestyle="--", linewidth=1)
    plt.title("Change in commit frequency by language group")
    plt.xlabel("Language Group")
    plt.ylabel("Delta commits per week (after - before)")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig("commit_frequency_delta_by_language_group.png")


def main() -> None:
    repo_df = build_commit_frequency_repo_dataset(weeks_before=WEEKS_BEFORE, weeks_after=WEEKS_AFTER, csv_path=ARTIFACT_CSV)

    if repo_df.empty:
        print("No data collected for commit frequency analysis")
        return
    
    run_overall_commit_freq_wilcoxon(repo_df)
    run_language_group_commit_freq_tests(repo_df, min_repos_per_group=MIN_REPOS_PER_GROUP)
    run_commit_frequency_kruskal_by_language(repo_df, min_repos_per_group=MIN_REPOS_PER_GROUP)
    plot_commit_freq_delta_by_language(repo_df, min_repos_per_group=MIN_REPOS_PER_GROUP)

if __name__ == "__main__":
    try:
        main()
    finally:
        driver.close()