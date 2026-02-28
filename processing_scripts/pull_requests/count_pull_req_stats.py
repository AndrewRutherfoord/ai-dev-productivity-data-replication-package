# uv run -m pull_requests.count_pull_req_stats
import pandas as pd

from interact_with_neo4j import iter_repos, load_df

RESULT_FILE = "./pull_requests/agents_claude_pr_commit_stats.csv"
MIN_PR_COMMITS = 10

results = []
for repo in iter_repos():
    # Get the artifact creation date
    query = f"""
    MATCH (r:Repository {{url: "{repo.url}"}})<-[:PART_OF]-(b:Branch {{name: "{repo.branch}"}})<-[:IN_BRANCH]-(c:Commit {{hash: "{repo.artifact_creation_commit}"}})
    RETURN c.date AS artifact_creation_date
    """
    df = load_df(query)

    artifact_creation_date = df.iloc[0]["artifact_creation_date"]

    # Count PR merge commits before and after artifact creation date
    query = f"""
    MATCH (r:Repository {{url: "{repo.url}"}})<-[:PART_OF]-(b:Branch {{name: "{repo.branch}"}})<-[:IN_BRANCH]-(c:Commit)
    WHERE c.is_merge = true AND c.message CONTAINS "Merge pull request"
    RETURN 
        SUM(CASE WHEN c.date < "{artifact_creation_date}" THEN 1 ELSE 0 END) AS pr_commits_before,
        SUM(CASE WHEN c.date >= "{artifact_creation_date}" THEN 1 ELSE 0 END) AS pr_commits_after
    """
    counts = load_df(query)
    pr_before = counts.iloc[0]["pr_commits_before"]
    pr_after = counts.iloc[0]["pr_commits_after"]
    if pr_before < MIN_PR_COMMITS or pr_after < MIN_PR_COMMITS:
        print(f"Excluding {repo.url} / {repo.branch} (before: {pr_before}, after: {pr_after})")
        continue
    else:
        results.append({
            **repo.to_dict(),
            "artifact_creation_date": artifact_creation_date,
            "pr_commits_before": pr_before,
            "pr_commits_after": pr_after,
        })

results_df = pd.DataFrame(results)
results_df.to_csv(RESULT_FILE, index=False)