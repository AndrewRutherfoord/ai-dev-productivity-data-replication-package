
import csv
from urllib.parse import urlparse
import yaml


AGENT_REPO_CSV = "github_agents_results.csv"

def extract_repo_info(github_url: str):
    parts = urlparse(github_url).path.strip("/").split("/")
    if len(parts) < 3:
        return None
    owner, repo = parts[0], parts[1]
    repo_url = f"https://github.com/{owner}/{repo}.git"
    return {"name": repo, "url": repo_url}

def build_yaml_from_csv(csv_path: str, yaml_path: str):
    repositories = []
    seen = set()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            link = row.get("url", "").strip()
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
    return

    # Construct base config
    base_config = {
        "defaults": {
            "delete_clone": False,
            "index_file_modifications": True,
            "pydriller": {},
        },
        "repositories": repositories,
    }

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(base_config, f, sort_keys=False)

    print(f"✅ Created YAML config with {len(repositories)} repositories → {yaml_path}")

if __name__ == "__main__":
    build_yaml_from_csv(AGENT_REPO_CSV, "agent_repos.yaml")