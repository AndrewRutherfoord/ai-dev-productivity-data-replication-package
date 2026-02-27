
import json
import yaml


AGENTS_NEOREPRO_YAML = "./remove_failed/agents-file-config.yaml"
FAILED_JSON_FILE = "./remove_failed/failed.json"
FAILED_REMOVED_NEOREPRO_YAML = "./remove_failed/agents-file-config-with-failed-removed.yaml"

failed = []
with open(FAILED_JSON_FILE, "r", encoding="utf-8") as f:
    failed = json.load(f)

config_repos = {}
with open(AGENTS_NEOREPRO_YAML, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

    for repo in config.get("repositories", []):
        url = repo.get("url")
        if url:
            config_repos[url] = repo

for f in failed:
    url = f['url']
    if url in config_repos:
        print(f"Removing {url} from {AGENTS_NEOREPRO_YAML}...")
        config_repos.pop(url)

config["repositories"] = []
for k, v in config_repos.items():
    config["repositories"].append(v)

with open(FAILED_REMOVED_NEOREPRO_YAML, "w", encoding="utf-8") as f:
    yaml.dump(config, f, default_flow_style=False)