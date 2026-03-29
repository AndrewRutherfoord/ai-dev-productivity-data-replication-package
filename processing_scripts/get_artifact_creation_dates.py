"""
This script finds the original creation commit for "agents.md" and "claude.md" and applied the exclusions criteria.
This allows us to use the creation date for all analysis
"""

from interact_with_neo4j import load_df, driver
import pandas as pd

EXCLUSION_TOTAL_COMMITS = 500
EXCLUSION_COMMITS_BEFORE = 50
EXCLUSION_COMMITS_AFTER = 50

OUTPUT_CSV = "agents_claude_artifact_creations.csv"
EXCLUDED_CSV = "agents_claude_artifact_creations_excluded.csv"

def find_original_file(file_hash, max_depth=50):
    # Need to walk the rename history to find the original artifact creation commit.
    visited = set()
    current_hash = file_hash

    # commit date of the starting file
    date_query = f"""
    MATCH (c:Commit)-[m:MODIFIED]->(f:File {{hash: "{current_hash}"}})
    WHERE m.change_type = "RENAME"
    RETURN c.date AS commit_date
    ORDER BY c.date ASC
    LIMIT 1
    """
    date_df = load_df(date_query)
    if date_df.empty:
        return current_hash
    current_date = date_df.iloc[0]["commit_date"]

    for _ in range(max_depth):
        if current_hash in visited:
            print(f"Cycle detected at file hash {current_hash}")
            return None
        visited.add(current_hash)

        query = f"""
        MATCH (c:Commit)-[m:MODIFIED]->(f:File {{hash: "{current_hash}"}})
        WHERE m.change_type = "RENAME"
        MATCH (prev:File)-[:RENAMED_TO]->(f)
        WHERE prev.hash <> f.hash
        MATCH (c2:Commit)-[m2:MODIFIED]->(prev)
        WHERE m2.change_type IN ["ADD", "RENAME"]
        AND c2.date < "{current_date}"
        RETURN prev.hash AS prev_hash, prev.name AS prev_name, c2.date AS prev_date
        ORDER BY c2.date ASC
        LIMIT 1
        """
        df = load_df(query)
        if df.empty:
            # Nothing older
            return current_hash

        current_hash = df.iloc[0]["prev_hash"]
        current_date = df.iloc[0]["prev_date"]

    print(f"Max depth reached for file hash {file_hash}")
    return None


# Get all repos and branches
repos_query = f"""
MATCH (r:Repository)<-[:PART_OF]-(b:Branch)
WITH r, b
MATCH (b)<-[:IN_BRANCH]-(c:Commit)
WITH r, b, COUNT(c) AS commit_count
WHERE commit_count >= {EXCLUSION_TOTAL_COMMITS}
MATCH (b)<-[:IN_BRANCH]-(c2:Commit)-[:MODIFIED]->(f:File)
WHERE toLower(f.name) IN ["agents.md", "claude.md"]
WITH r, b
ORDER BY r.name, b.name
WITH r, COLLECT(b)[0] AS b
RETURN r.name AS repository, r.url AS url, b.name AS branch, b.hash AS branch_hash
"""
repos = load_df(repos_query)

results = []

for repo in repos.itertuples(index=False):
    print(f"Processing {repo.repository} / {repo.branch}...")
    combined_rows = []

    # --- Direct ADDs ---
    direct_query = f"""
    MATCH (b:Branch {{hash: "{repo.branch_hash}"}})<-[:IN_BRANCH]-(c:Commit)-[m:MODIFIED]->(f:File)
    WHERE toLower(f.name) IN ["agents.md", "claude.md"]
    AND m.change_type = "ADD"
    RETURN f.name AS original_name, c.hash AS creation_commit, c.date AS creation_date
    """
    direct_adds = load_df(direct_query)
    if not direct_adds.empty:
        combined_rows.append(direct_adds)

    # Walk back through renames
    renamed_query = f"""
    MATCH (b:Branch {{hash: "{repo.branch_hash}"}})<-[:IN_BRANCH]-(c:Commit)-[m:MODIFIED]->(f:File)
    WHERE toLower(f.name) IN ["agents.md", "claude.md"]
    AND m.change_type = "RENAME"
    RETURN f.hash AS file_hash, f.name AS file_name
    """
    renamed_files = load_df(renamed_query)

    for row in renamed_files.itertuples(index=False):
        original_hash = find_original_file(row.file_hash)
        if original_hash is None:
            print(f" Skipping {row.file_name} in {repo.repository} / {repo.branch} — cycle or max depth")
            continue

        add_query = f"""
        MATCH (b:Branch {{hash: "{repo.branch_hash}"}})<-[:IN_BRANCH]-(c2:Commit)-[m2:MODIFIED]->(original:File {{hash: "{original_hash}"}})
        WHERE m2.change_type = "ADD"
        RETURN original.name AS original_name, c2.hash AS creation_commit, c2.date AS creation_date
        """
        add_commit = load_df(add_query)
        if not add_commit.empty:
            combined_rows.append(add_commit)

    # Earliest is the artifact creation commit
    if combined_rows:
        combined = pd.concat(combined_rows, ignore_index=True)
        if not combined.empty:
            earliest = combined.sort_values("creation_date").iloc[0]
            results.append({
                "repository": repo.repository,
                "url": repo.url,
                "branch": repo.branch,
                "branch_hash": repo.branch_hash,
                "artifact_original_name": earliest["original_name"],
                "artifact_creation_commit": earliest["creation_commit"],
                "artifact_creation_date": earliest["creation_date"],
            })


final_results = []
excluded_results = []

for result in results:
    # Count commits before and after artifact creation
    print(f"Counting commits for {result['repository']} / {result['branch']}...")
    counts_query = f"""
    MATCH (b:Branch {{hash: "{result['branch_hash']}"}})<-[:IN_BRANCH]-(c:Commit)
    WHERE c.date < "{result['artifact_creation_date']}"
    RETURN COUNT(c) AS commits_before
    """
    before_df = load_df(counts_query)
    commits_before = before_df.iloc[0]["commits_before"] if not before_df.empty else 0

    counts_query = f"""
    MATCH (b:Branch {{hash: "{result['branch_hash']}"}})<-[:IN_BRANCH]-(c:Commit)
    WHERE c.date > "{result['artifact_creation_date']}"
    RETURN COUNT(c) AS commits_after
    """
    after_df = load_df(counts_query)
    commits_after = after_df.iloc[0]["commits_after"] if not after_df.empty else 0

    total_commits = commits_before + commits_after

    result["commits_before"] = commits_before
    result["commits_after"] = commits_after
    result["total_commits"] = total_commits

    if (commits_before >= EXCLUSION_COMMITS_BEFORE and
        commits_after >= EXCLUSION_COMMITS_AFTER and
        total_commits >= EXCLUSION_TOTAL_COMMITS):
        final_results.append(result)
    else:
        excluded_results.append(result)
        print(f" Excluding {result['repository']} / {result['branch']} — not enough commits around artifact creation")

df_results = pd.DataFrame(results)
df_results.to_csv(OUTPUT_CSV, index=False)
print(df_results)

df_excluded = pd.DataFrame(excluded_results)
df_excluded.to_csv(EXCLUDED_CSV, index=False)
print(df_excluded)