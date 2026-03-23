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
from typing import Any, cast, Optional

HOST = "100.65.19.91"
URI = f"neo4j://{HOST}:7687"
USER = "neo4j"
PASSWORD = "neo4j123"
ARTIFACT_CSV = "agents_claude_artifact_creations.csv"

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


# create a lookup from the csv (url, branch)
def artifact_date_lookup(csv_path: str = ARTIFACT_CSV) -> dict[tuple[str, str], str]:

    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["url", "branch", "artifact_creation_date"]).copy()
    df["artifact_creation_date"] = pd.to_datetime(df["artifact_creation_date"], errors="coerce")
    df = df.dropna(subset=["artifact_creation_date"])

    df = (df.groupby(["url", "branch"], as_index=False)["artifact_creation_date"].min())

    df["iso"] = df["artifact_creation_date"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    return {(row["url"], row["branch"]): row["iso"] for _, row in df.iterrows()}


# get artifact creation date from specific repo
def get_artifact_creation_date(repo, lookup: dict[tuple[str, str], str]) -> Optional[str]:

    key = (repo.url, repo.branch)
    if key in lookup:
        return lookup[key]
    
    return None


# get commit tied to artifact creation date per repo and aggregate it in weeks before and after artifact creation
# plot median and iqr across repos per week and plot coverage of repos with data in the respective weeks
def chart_event_aligned_commit_frequency_week(weeks_before, weeks_after, csv_path: str = ARTIFACT_CSV):
    
    from interact_with_neo4j import iter_repos

    lookup = artifact_date_lookup(csv_path)

    rows = []

    # get artifact creation date for each repo
    for repo in iter_repos():
        created_at = get_artifact_creation_date(repo, lookup)
        if not created_at:
            continue

        # get commits in respective time window around artifact creation date
        query = f"""
        MATCH (r:Repository {{url: "{repo.url}"}})<-[:PART_OF]-(b:Branch {{name: "{repo.branch}"}})
        MATCH (b)<-[:IN_BRANCH]-(c:Commit)
        WHERE c.date IS NOT NULL
        WITH datetime("{created_at}") AS special_created_at, datetime(replace(c.date, ' ', 'T')) AS commit_dt
        WITH duration.inDays(special_created_at, commit_dt).days AS day_offset
        WHERE day_offset >= -{weeks_before}*7 AND day_offset <= {weeks_after}*7
        RETURN toInteger(floor(day_offset/7.0)) AS week_offset, count(*) AS commits_in_week
        ORDER BY week_offset
        """

        df = load_df(query)
        if df.empty:
            print("No data returned for artifact aligned commit frequency.")
            return
        # only include repos with at least 1 commit in a week
        df["commits_in_week"] = pd.to_numeric(df["commits_in_week"], errors="coerce").fillna(0)
        df["week_offset"] = pd.to_numeric(df["week_offset"], errors="coerce").astype(int)
        df["repo_key"] = f"{repo.url}::{repo.branch}"
        rows.append(df)
    
    if not rows:
        print("No data collected for artifact aligned commit frequency")
        return

    all_df = pd.concat(rows, ignore_index=True)

    # aggregate across repos per week (iqr and median)
    grouped = all_df.groupby("week_offset")["commits_in_week"]
    stats = grouped.agg(
        median="median",
        q1=lambda x: x.quantile(0.25),
        q3=lambda x: x.quantile(0.75),
        repos="count"   # number of repo per week observations
    ).reset_index()

    # add missing weeks with 0 commits
    total_weeks = pd.DataFrame({"week_offset": list(range(-weeks_before, weeks_after+1))})
    stats = total_weeks.merge(stats, on="week_offset", how="left").fillna({"median": 0, "q1": 0, "q3": 0, "repos": 0})

    # plot median with iqr band
    plt.figure(figsize=(10, 4))
    plt.plot(stats["week_offset"], stats["median"], marker="o", linewidth=1)
    plt.fill_between(stats["week_offset"], stats["q1"], stats["q3"], alpha=0.2)
    plt.axvline(0, linestyle="--")
    plt.title("Artifact creation-aligned commit frequency (median +- iqr across repos)")
    plt.xlabel("Weeks relative to artifact creation (week 0 is creation week)")
    plt.ylabel("Commits per repo per week")
    plt.tight_layout()
    plt.savefig("artifact_aligned_commit_frequency_median_iqr_week.png")

    # plot coverage, so how many repos contribute with data per week
    plt.figure(figsize=(10, 3.2))
    plt.plot(stats["week_offset"], stats["repos"], marker="o", linewidth=1)
    plt.axvline(0, linestyle="--")
    plt.title("Repo coverage per relative week (repos with data in respective week)")
    plt.xlabel("Weeks relative to artifact creation")
    plt.ylabel("Week repo observations")
    plt.tight_layout()
    plt.savefig("artifact_aligned_commit_frequency_coverage_week.png")


# get commit tied to artifact creation date per repo and aggregate it in months before and after artifact creation
# plot median and iqr across repos per month and plot coverage of repos with data in the respective months
def chart_event_aligned_commit_frequency_month(months_before, months_after, csv_path: str = ARTIFACT_CSV):
    
    from interact_with_neo4j import iter_repos

    lookup = artifact_date_lookup(csv_path)

    rows = []

    # get artifact creation date for each repo
    for repo in iter_repos():
        created_at = get_artifact_creation_date(repo, lookup)
        if not created_at:
            continue

        # get commits in respective time window around artifact creation date
        query = f"""
        MATCH (r:Repository {{url: "{repo.url}"}})<-[:PART_OF]-(b:Branch {{name: "{repo.branch}"}})
        MATCH (b)<-[:IN_BRANCH]-(c:Commit)
        WHERE c.date IS NOT NULL
        WITH datetime("{created_at}") AS special_created_at, datetime(replace(c.date, ' ', 'T')) AS commit_dt
        WITH (commit_dt.year - special_created_at.year)*12 + (commit_dt.month - special_created_at.month) AS month_offset
        WHERE month_offset >= -{months_before} AND month_offset <= {months_after}
        RETURN toInteger(month_offset) AS month_offset, count(*) AS commits_in_month
        ORDER BY month_offset
        """

        df = load_df(query)
        if df.empty:
            print("No data returned for artifact aligned commit frequency.")
            return
        # only include repos with at least 1 commit in a month
        df["commits_in_month"] = pd.to_numeric(df["commits_in_month"], errors="coerce").fillna(0)
        df["month_offset"] = pd.to_numeric(df["month_offset"], errors="coerce").astype(int)
        df["repo_key"] = f"{repo.url}::{repo.branch}"
        rows.append(df)
    
    if not rows:
        print("No data collected for artifact aligned commit frequency")
        return

    all_df = pd.concat(rows, ignore_index=True)

    # aggregate across repos per month (iqr and median)
    grouped = all_df.groupby("month_offset")["commits_in_month"]
    stats = grouped.agg(
        median="median",
        q1=lambda x: x.quantile(0.25),
        q3=lambda x: x.quantile(0.75),
        repos="count"   # number of repo per month observations
    ).reset_index()

    # add missing months with 0 commits
    total_months = pd.DataFrame({"month_offset": list(range(-months_before, months_after+1))})
    stats = total_months.merge(stats, on="month_offset", how="left").fillna({"median": 0, "q1": 0, "q3": 0, "repos": 0})

    # plot median with iqr band
    plt.figure(figsize=(10, 4))
    plt.plot(stats["month_offset"], stats["median"], marker="o", linewidth=1)
    plt.fill_between(stats["month_offset"], stats["q1"], stats["q3"], alpha=0.2)
    plt.axvline(0, linestyle="--")
    plt.title("Artifact creation-aligned commit frequency (median +- iqr across repos)")
    plt.xlabel("Months relative to artifact creation (month 0 is creation month)")
    plt.ylabel("Commits per repo per month")
    plt.tight_layout()
    plt.savefig("artifact_aligned_commit_frequency_median_iqr_month.png")

    # plot coverage, so how many repos contribute with data per month
    plt.figure(figsize=(10, 3.2))
    plt.plot(stats["month_offset"], stats["repos"], marker="o", linewidth=1)
    plt.axvline(0, linestyle="--")
    plt.title("Repo coverage per relative month (repos with data in respective month)")
    plt.xlabel("Months relative to artifact creation")
    plt.ylabel("Month repo observations")
    plt.tight_layout()
    plt.savefig("artifact_aligned_commit_frequency_coverage_month.png")


def chart_commit_loc(weeks_before, weeks_after, csv_path: str = ARTIFACT_CSV):
   
    from interact_with_neo4j import iter_repos

    lookup = artifact_date_lookup(csv_path)

    rows = []

    # get artifact creation date for each repo
    for repo in iter_repos():
        created_at = get_artifact_creation_date(repo, lookup)
        if not created_at:
            continue

        # get LOC per week in window around artifact creation date
        query = f"""
        MATCH (r:Repository {{url: "{repo.url}"}})<-[:PART_OF]-(b:Branch {{name: "{repo.branch}"}})
        MATCH (b)<-[:IN_BRANCH]-(c:Commit)-[m:MODIFIED]->(:File)
        WHERE c.date IS NOT NULL

        WITH datetime("{created_at}") AS special_created_at,
            datetime(replace(c.date, ' ', 'T')) AS commit_dt,
            coalesce(toInteger(m.added_lines),0) + coalesce(toInteger(m.deleted_lines),0) AS file_loc

        // sum file LOC per commit and compute day offset relative to artifact
        WITH special_created_at,
            commit_dt,
            sum(file_loc) AS commit_loc,
            duration.inDays(special_created_at, commit_dt).days AS day_offset

        // restrict to symmetric window
        WHERE day_offset >= -{weeks_before}*7 AND day_offset <= {weeks_after}*7

        // aggregate into week bins
        RETURN toInteger(floor(day_offset/7.0)) AS week_offset,
            sum(commit_loc) AS loc_in_week
        ORDER BY week_offset
        """

        df = load_df(query)
        if df.empty:
            print(f"No data returned for repo {repo.url}::{repo.branch} - skipping.")
            continue

        df["loc_in_week"] = pd.to_numeric(df["loc_in_week"], errors="coerce").fillna(0)
        df["week_offset"] = pd.to_numeric(df["week_offset"], errors="coerce").astype(int)
        df["repo_key"] = f"{repo.url}::{repo.branch}"
        rows.append(df)
   
    if not rows:
        print("No data collected for artifact aligned commit frequency")
        return

    all_df = pd.concat(rows, ignore_index=True)

    # aggregate LOC across repos per week (iqr and median)
    grouped = all_df.groupby("week_offset")["loc_in_week"]
    stats = grouped.agg(
        median="median",
        q1=lambda x: x.quantile(0.25),
        q3=lambda x: x.quantile(0.75),
        repos="count"   # number of repo per week observations
    ).reset_index()

    # add missing weeks with 0 loc
    total_weeks = pd.DataFrame({"week_offset": list(range(-weeks_before, weeks_after+1))})
    stats = total_weeks.merge(stats, on="week_offset", how="left").fillna({"median": 0, "q1": 0, "q3": 0, "repos": 0})

    # plot median with iqr band
    plt.figure(figsize=(10, 4))
    plt.plot(stats["week_offset"], stats["median"], marker="o", linewidth=1)
    plt.fill_between(stats["week_offset"], stats["q1"], stats["q3"], alpha=0.2)
    plt.axvline(0, linestyle="--")
    plt.title("Added + Removed LOC per week")
    plt.xlabel("Weeks relative to artifact creation")
    plt.ylabel("LOC per repo per week")
    plt.tight_layout()
    plt.savefig("artifact_aligned_loc_median_iqr.png")

    # boxplot comparing before/after periods (weeks_before and weeks_after), outliers removed
    all_df["period"] = all_df["week_offset"].apply(lambda w: "before" if w < 0 else "after")
    before_vals = all_df.loc[(all_df["period"] == "before") & (all_df["week_offset"] >= -weeks_before), "loc_in_week"]
    after_vals = all_df.loc[(all_df["period"] == "after") & (all_df["week_offset"] <= weeks_after), "loc_in_week"]
    
    # remove outliers using IQR method
    def trim_outliers(series):
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        return series[(series >= lower_bound) & (series <= upper_bound)]
    
    before_trimmed = trim_outliers(before_vals)
    after_trimmed = trim_outliers(after_vals)
    
    plt.figure(figsize=(6, 5))
    box = plt.boxplot([before_trimmed, after_trimmed], tick_labels=["before", "after"], patch_artist=True)
    for patch, color in zip(box["boxes"], ["#8172B2", "#55A868"]):
        patch.set_facecolor(color)
    plt.title("Modified LOC per repo-week before vs after artifact creation")
    plt.ylabel("LOC per repo-week")
    plt.tight_layout()
    plt.savefig("artifact_loc_before_after_boxplot.png")


# for each repo compute commits per week before and after artifact creation
# this includes repos even if they have 0 commits before or 0 commits after
def chart_commits_per_week_before_after_(weeks_before, weeks_after, csv_path: str = ARTIFACT_CSV):
    
    from interact_with_neo4j import iter_repos

    lookup = artifact_date_lookup(csv_path)

    rows = []
    for repo in iter_repos():
        created_at = get_artifact_creation_date(repo, lookup)
        if not created_at:
            continue

        query = f"""
        MATCH (r:Repository {{url: "{repo.url}"}})<-[:PART_OF]-(b:Branch {{name: "{repo.branch}"}})
        MATCH (b)<-[:IN_BRANCH]-(c:Commit)
        WHERE c.date IS NOT NULL
        WITH datetime("{created_at}") AS t0, datetime(replace(c.date, ' ', 'T')) AS dt
        WITH duration.inDays(t0, dt).days AS day_offset
        WHERE day_offset >= -{weeks_before}*7 AND day_offset <= {weeks_after}*7
        WITH sum(CASE WHEN day_offset < 0 THEN 1 ELSE 0 END) AS commits_before,
            sum(CASE WHEN day_offset >= 0 THEN 1 ELSE 0 END) AS commits_after
        RETURN commits_before, commits_after
        """

        df = load_df(query)
        if df.empty:
            print("No data returned for commit frequency before and after creation of artifact.")
            return
        
        rows.append({
            "repo_key": f"{repo.url}::{repo.branch}",
            "commits_before": float(df.loc[0, "commits_before"]) / float(weeks_before) if weeks_before > 0 else float("nan"),
            "commits_after": float(df.loc[0, "commits_after"]) / float(weeks_after) if weeks_after > 0 else float("nan"),
        })
    
    if not rows:
        print("No data collected for commit frequency before and after creation of artifact.")
        return
    
    all_df = pd.DataFrame(rows).dropna()

    plt.figure(figsize=(7, 5))
    box = plt.boxplot(
        [all_df["commits_before"], all_df["commits_after"]],
        tick_labels=["Before", "After"],
        patch_artist=True
    )
    box["boxes"][0].set_facecolor("#4C72B0")
    box["boxes"][1].set_facecolor("#55A868")
    plt.title("Commits per week per repo (before vs after artifact creation)")
    plt.ylabel("Commits per repo per week")
    plt.yscale("log")
    plt.tight_layout()
    plt.savefig("commits_per_week_before_after_boxplot.png")


def chart_total_commits_before_after_artifact(csv_path: str = ARTIFACT_CSV):

    from interact_with_neo4j import iter_repos

    lookup = artifact_date_lookup(csv_path)

    total_before = 0
    total_after = 0
    used_repos = 0

    for repo in iter_repos():
        created_at = get_artifact_creation_date(repo, lookup)
        if not created_at:
            continue

        query = f"""
        MATCH (r:Repository {{url: "{repo.url}"}})<-[:PART_OF]-(b:Branch {{name: "{repo.branch}"}})
        MATCH (b)<-[:IN_BRANCH]-(c:Commit)
        WHERE c.date IS NOT NULL
        WITH datetime("{created_at}") AS t0, datetime(replace(c.date, ' ', 'T')) AS dt
        RETURN
            sum(CASE WHEN dt < t0 THEN 1 ELSE 0 END) AS commits_before,
            sum(CASE WHEN dt >= t0 THEN 1 ELSE 0 END) AS commits_after
        """

        df = load_df(query)
        if df.empty:
            print("No data returned for total commits before and after creation of artifact.")
            return

        total_before += int(df.loc[0, "commits_before"] or 0)
        total_after += int(df.loc[0, "commits_after"] or 0)
        used_repos += 1
    
    if used_repos == 0:
        print("No repositories with artifact creation date found for total commits before and after artifact creation.")
        return
    
    # plot
    plt.figure(figsize=(6, 4))
    plt.bar(["Before", "After"], [total_before, total_after])
    plt.title("Total commits before vs after artifact creation")
    plt.ylabel("Total commits")
    plt.tight_layout()
    plt.savefig("total_commits_before_after.png")


if __name__ == "__main__":
    chart_repositories_per_year()
    chart_commits_per_year()
    chart_commits_per_project()
    chart_artifact_creation()
    chart_before_after_commits()
    chart_event_aligned_commit_frequency_week(weeks_before=30, weeks_after=30, csv_path=ARTIFACT_CSV) # change number of weeks if necessary
    chart_event_aligned_commit_frequency_month(months_before=3, months_after=3, csv_path=ARTIFACT_CSV) # change number of months if necessary
    chart_commit_loc(weeks_before=30, weeks_after=30, csv_path=ARTIFACT_CSV)
    chart_commits_per_week_before_after_(weeks_before=30, weeks_after=30, csv_path=ARTIFACT_CSV)
    chart_total_commits_before_after_artifact(csv_path=ARTIFACT_CSV)