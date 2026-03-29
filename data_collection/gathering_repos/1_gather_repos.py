# This script uses SerpAPI to search for GitHub repositories that have recently edited files named "agents.md" or "claude.md"

import os
import time
import csv
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SERPAPI_KEY")

if not API_KEY:
    raise ValueError("Missing SERPAPI_KEY in .env")


# Prepare CSV file
output_file = "./gathering_repos/agent_repos.csv"
fieldnames = ["name", "url"]
artifact_files = ["agents.md", "claude.md"]

# Overwrite any existing file and write header
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for artifact in artifact_files:
        query = 'site:github.com inurl:blob "{}"'.format(artifact)
        page = 0
        total_results = 0

        while True:
            print(f"Fetching results page {page + 1}...")

            params = {
                "engine": "google",
                "q": query,
                "google_domain": "google.com",
                "num": 10,
                "hl": "en",
                "gl": "us",
                "api_key": API_KEY,
                "start": page * 10,  # pagination: 10 results per page
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            organic = results.get("organic_results", [])
            if not organic:
                print("No more results")
                break

            for result in organic:
                git_url = result.get("link", "").split("/blob/")[0] if "/blob/" in result.get("link", "") else ""
                repo_name = git_url.split("/")[-1]
                git_url += ".git"
                row = {
                    "url": git_url,
                    "name": repo_name
                }
                writer.writerow(row)
                total_results += 1
                print(row["url"])

            page += 1
            time.sleep(1) # rate lim

print(f"Saved {total_results} results to {output_file}")