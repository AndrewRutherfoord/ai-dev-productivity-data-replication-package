# uv run -m pull_requests.count_pull_req_stats
import pandas as pd
from interact_with_neo4j import iter_repos, load_df
import matplotlib.pyplot as plt
import math

RESULT_FILE = "./pull_requests/agents_claude_pr_commit_stats.csv"
MIN_PR_COMMITS = 10

data = pd.read_csv(RESULT_FILE)

ratios = []
for index, row in data.iterrows():
    print(row)
    name = row["repository"] + " / " + row["branch"]
    commits_before = row["pr_commits_before"]
    commits_after = row["pr_commits_after"]

    ratio = commits_before / commits_after
    log2_ratio = math.log2(ratio)
    ratios.append({
        "name": name,
        "commits_before": commits_before,
        "commits_after": commits_after,
        "ratio": ratio,
        "log2_ratio": log2_ratio
    })

ratios_raw = [entry["ratio"] for entry in ratios]
log2_ratios = [entry["log2_ratio"] for entry in ratios]

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
plt.suptitle("PR Commit Ratios Before vs After Artifact Creation")

Y_TITLE = "commits_before / commits_after"

# Raw ratios
axes[0].boxplot(ratios_raw)
axes[0].axhline(1, color="black", linewidth=1)
axes[0].set_title("Raw Ratio")
axes[0].set_ylabel(Y_TITLE)
axes[0].grid(axis="y", alpha=0.3)

# Log2 ratios
axes[1].boxplot(log2_ratios)
axes[1].axhline(0, color="black", linewidth=1)
axes[1].set_title("Log2 Ratio")
axes[1].set_ylabel("log2(" + Y_TITLE + ")")
axes[1].grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.savefig("./pull_requests/pr_commit_ratios.png")

