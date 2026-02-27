#!/usr/bin/env python3
"""
Visualize repository and commit timelines from Neo4j.
Generates:
1. Repositories per year based on their first commit.
2. Total commits per year across all repos.
3. Distribution of commits per project (100-commit buckets).
4. Month+year of creation for agents.md & claude.md.
5. Boxplot of per-repository before/after commit ratio for agents.md/claude.md creation.
"""

from neo4j import GraphDatabase
import pandas as pd
import matplotlib.pyplot as plt
from typing import Any, cast

HOST = "100.65.19.90"
URI = f"neo4j://{HOST}:7687"
USER = "neo4j"
PASSWORD = "neo4j123"

date_format = "yyyy-MM-dd HH:mm:ss"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def load_df(query: str) -> pd.DataFrame:
    with driver.session() as session:
        data = session.run(cast(Any, query)).data()
    return pd.DataFrame(data)

def chart_repositories_per_year():
    Q_REPOS_PER_YEAR = """
        MATCH (r:Repository)<-[:PART_OF]-(:Branch)<-[:IN_BRANCH]-(c:Commit)
        WHERE c.date IS NOT NULL
        WITH r, min(datetime(replace(c.date, ' ', 'T'))) AS first_commit_date
        RETURN date(first_commit_date).year AS year, count(DISTINCT r) AS repo_count
        ORDER BY year
    """

    repos_per_year = load_df(Q_REPOS_PER_YEAR)


    plt.figure(figsize=(7, 4))
    plt.bar(repos_per_year["year"], repos_per_year["repo_count"])
    plt.title("Repositories Created Per Year (First Commit Year)")
    plt.xlabel("Year")
    plt.ylabel("Number of Repositories")
    plt.tight_layout()
    plt.savefig("repos_per_year.png")

def chart_commits_per_year():
    query = """
        MATCH (c:Commit)
        WHERE c.date IS NOT NULL
        WITH date(datetime(replace(c.date, ' ', 'T'))).year AS year, count(c) AS commit_count
        RETURN year, commit_count
        ORDER BY year
    """

    commits_per_year_df = load_df(query)

    plt.figure(figsize=(7, 4))
    plt.bar(commits_per_year_df["year"], commits_per_year_df["commit_count"], color="#55A868")
    plt.title("Total Commits Per Year")
    plt.xlabel("Year")
    plt.ylabel("Number of Commits")
    plt.tight_layout()
    plt.savefig("commits_per_year.png")

def chart_commits_per_project():
    query = """
    MATCH (r:Repository)<-[:PART_OF]-(:Branch)<-[:IN_BRANCH]-(c:Commit)
    WHERE c.date IS NOT NULL
    WITH r, count(c) AS commit_count
    WHERE commit_count < 5000
    RETURN r.name AS repository, commit_count
    ORDER BY commit_count DESC
    """

    commits_per_project_df = load_df(query)

    commits_per_project_df ["commit_count"] = pd.to_numeric(
        commits_per_project_df ["commit_count"], errors="coerce"
    )
    commits_per_project_df = commits_per_project_df .dropna(subset=["commit_count"])

    # Use 100-commit buckets for the histogram
    commit_counts = commits_per_project_df ["commit_count"].astype(int)
    avg_commits = float(commit_counts.mean())
    bin_width = 100
    max_count = int(commit_counts.max())
    upper_edge = ((max_count // bin_width) + 1) * bin_width
    bins = list(range(0, upper_edge + bin_width, bin_width))

    plt.figure(figsize=(9, 5))
    plt.hist(commit_counts, bins=bins, color="#64B5CD", edgecolor="white")
    plt.axvline(avg_commits, color="#C44E52", linestyle="--", linewidth=2, label=f"Average: {avg_commits:.1f}")
    plt.title("Commit Count Distribution per Project")
    plt.xlabel(f"Commits per Project (bucket size = {bin_width})")
    plt.ylabel("Number of Projects")
    plt.legend()
    plt.tight_layout()
    plt.savefig("commits_per_project.png")

    print(f"Average commits per project: {avg_commits:.2f}")

def chart_artifact_creation():
    query = """
    MATCH (r:Repository)<-[:PART_OF]-(:Branch)<-[:IN_BRANCH]-(c:Commit)-[m:MODIFIED]->(f:File)
    WHERE toLower(f.name) IN ["agents.md", "claude.md"]
    AND m.change_type = "ADD"
    AND c.date IS NOT NULL
    WITH datetime(replace(c.date, ' ', 'T')) AS created_at, f.name AS file_name
    RETURN date(created_at).year AS year, date(created_at).month AS month, file_name
    ORDER BY year, month
    """

    artifact_creation = load_df(query)


    artifact_creation["month_year"] = (
        artifact_creation["year"].astype(str) + "-" + artifact_creation["month"].astype(str).str.zfill(2)
    )

    counts = (
        artifact_creation.groupby("month_year")["file_name"]
        .count()
        .reset_index(name="file_count")
    )

    plt.figure(figsize=(9, 4))
    plt.bar(counts["month_year"], counts["file_count"], color="#C44E52")
    plt.title("Creation of agents.md / claude.md Over Time")
    plt.xlabel("Month-Year")
    plt.ylabel("Files Created")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig("special_files_timeline.png")

def chart_before_after_commits():
    Q_COMMITS_BEFORE_AFTER_SPECIAL = """
    MATCH (r:Repository)<-[:PART_OF]-(:Branch)<-[:IN_BRANCH]-(c_special:Commit)-[m:MODIFIED]->(f:File)
    WHERE toLower(f.name) IN ["agents.md", "claude.md"]
        AND m.change_type = "ADD"
        AND c_special.date IS NOT NULL
    WITH r, min(datetime(replace(c_special.date, ' ', 'T'))) AS special_created_at
    MATCH (r)<-[:PART_OF]-(:Branch)<-[:IN_BRANCH]-(c:Commit)
    WHERE c.date IS NOT NULL
    WITH r, special_created_at, datetime(replace(c.date, ' ', 'T')) AS commit_dt
    WITH
        r,
        count(*) AS total_commits,
        sum(CASE WHEN commit_dt < special_created_at THEN 1 ELSE 0 END) AS commits_before,
        sum(CASE WHEN commit_dt >= special_created_at THEN 1 ELSE 0 END) AS commits_after
    WHERE total_commits >= 500
    AND commits_before > 0
    RETURN
        r.name AS repository,
        commits_before,
        commits_after,
        total_commits
    """
    before_after_commits = load_df(Q_COMMITS_BEFORE_AFTER_SPECIAL)

    print(f"Repositories after filters: {len(before_after_commits)}")

    before_after_commits["commits_before"] = pd.to_numeric(
        before_after_commits["commits_before"], errors="coerce"
    )
    before_after_commits["commits_after"] = pd.to_numeric(
        before_after_commits["commits_after"], errors="coerce"
    )

    # Ratio is before/after per repository.
    ratio_series = (
        before_after_commits.loc[
            before_after_commits["commits_after"] > 0,
            "commits_before",
        ]
        / before_after_commits.loc[
            before_after_commits["commits_after"] > 0,
            "commits_after",
        ]
    ).dropna()

    q1 = float(cast(Any, ratio_series.quantile(0.25)))
    q3 = float(cast(Any, ratio_series.quantile(0.75)))
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    trimmed_ratio_series = ratio_series[
        (ratio_series >= lower_bound) & (ratio_series <= upper_bound)
    ]

    # ratio_mean = float(trimmed_ratio_series.mean())
    # ratio_variance = (
    #     float(cast(Any, trimmed_ratio_series.var(ddof=1)))
    #     if len(trimmed_ratio_series) > 1
    #     else 0.0
    # )

    plt.figure(figsize=(7, 5))
    box = plt.boxplot([trimmed_ratio_series], tick_labels=["Before/After"], patch_artist=True)
    box["boxes"][0].set_facecolor("#8172B2")
    plt.title("Per-Repository Commit Ratio (Before/After, Outliers Trimmed)")
    plt.ylabel("Ratio")
    plt.tight_layout()
    plt.savefig("commits_before_after_ratio.png")

if __name__ == "__main__":
    chart_repositories_per_year()
    chart_commits_per_year()
    chart_commits_per_project()
    chart_artifact_creation()
    chart_before_after_commits()