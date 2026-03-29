# This script takes the CSV output from 1_gather_repos.py, extracts the unique GitHub repository URLs
# and creates a YAML config file that can be used for cloning and analysis in NeoRepro

import csv
from urllib.parse import urlparse
import yaml


AGENT_REPO_CSV = "./gathering_repos/agent_repos.csv"
OUTPUT_CONFIG = "./gathering_repos/agent_repos.yaml"

def extract_repo_info(github_url: str):
    """Extract owner/repo from either a GitHub repo URL or a GitHub file URL.

    Examples accepted:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo/blob/main/AGENTS.md
    """
    parsed = urlparse(github_url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        return None

    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    repo_url = f"https://github.com/{owner}/{repo}.git"
    return {"name": repo, "url": repo_url}

def build_yaml_from_csv(csv_path: str, yaml_path: str):
    repositories = []
    seen = set()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            link = (row.get("url") or row.get("link") or "").strip()
            if not link or "github.com" not in link:
                continue

            repo_info = extract_repo_info(link)
            if not repo_info:
                continue

            key = repo_info["url"]
            if key not in seen:
                repositories.append(repo_info)
                seen.add(key)
            
            print(f"Processed: {link} → {repo_info['url']}")

    # Construct base config
    base_config = {
        "defaults": {
            "delete_clone": True,
            "index_file_modifications": True, # WIthout this it will only index the commit information with no modifications
            "index_file_diff": True, # Without this it will not index the diff information at all, so we won't have churn or files touched
            "pydriller": {},
        },
        "repositories": repositories,
    }

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(base_config, f, sort_keys=False)

    print(f"Created YAML config with {len(repositories)} repositories → {yaml_path}")

if __name__ == "__main__":
    build_yaml_from_csv(AGENT_REPO_CSV, OUTPUT_CONFIG)