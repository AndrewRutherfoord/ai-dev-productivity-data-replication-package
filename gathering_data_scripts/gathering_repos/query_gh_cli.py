"""
    This script is used to gather projects using the GitHub CLI.
    It searches for AI Agent artifacts, namely: "agents.md" and "claude.md"
    This script has to contend with the GitHub Search API's rate limits...

    This script requires having the GitHub CLI installed and authenticated.
"""

import subprocess
import json
import csv
import time
import datetime
import sys
import os

OUTPUT_FILE = "github_agents_results.csv"
STATE_FILE = "search_state.json"
QUERIES = ["filename:agents.md", "filename:claude.md"]

# This was the most that GitHub would let me do
PAGE_SIZE = 200

# The joy of rate limited APIs...

def get_rate_limit_reset():
    cmd = ["gh", "api", "rate_limit"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("Failed to fetch rate limit info")
        sys.exit(1)

    data = json.loads(result.stdout)
    reset_ts = data["resources"]["code_search"]["reset"]
    remaining = data["resources"]["code_search"]["remaining"]

    return remaining, reset_ts


def sleep_until_reset(reset_ts):
    now = int(time.time())
    wait_seconds = reset_ts - now + 2

    if wait_seconds > 0:
        reset_time = datetime.datetime.fromtimestamp(reset_ts)
        print(
            f"Rate limit hit. Waiting until {reset_time} ({wait_seconds} seconds)"
        )
        time.sleep(wait_seconds)


# Keep track of state incase it crashes so I don't waste the rate limit

def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "query_index": 0,
            "page": 1,
            "seen_urls": [],
        }

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)



def run_page_query(query: str, page: int):
    while True:
        cmd = [
            "gh",
            "api",
            "-X",
            "GET",
            "search/code",
            "-f",
            f"q={query}",
            "-f",
            f"per_page={PAGE_SIZE}",
            "-f",
            f"page={page}",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return json.loads(result.stdout)

        if "rate limit" in result.stderr.lower():
            remaining, reset_ts = get_rate_limit_reset()
            if remaining == 0:
                sleep_until_reset(reset_ts)
                continue

        print(result.stderr.strip())
        return None

def main():
    state = load_state()

    query_index = state["query_index"]
    page = state["page"]
    seen = set(state["seen_urls"])

    file_exists = os.path.exists(OUTPUT_FILE)

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["repository", "path", "url"]
        )

        if not file_exists:
            writer.writeheader()

        while query_index < len(QUERIES):
            query = QUERIES[query_index]
            print(f"Running query: {query}")

            while True:
                print(f"  Page {page}")
                data = run_page_query(query, page)

                if not data or "items" not in data:
                    break

                items = data["items"]
                if not items:
                    break

                for item in items:
                    url = item["html_url"]
                    if url in seen:
                        continue

                    seen.add(url)

                    writer.writerow(
                        {
                            "repository": item["repository"][
                                "full_name"
                            ],
                            "path": item["path"],
                            "url": url,
                        }
                    )

                f.flush()

                # Update state after each page
                state["query_index"] = query_index
                state["page"] = page + 1
                state["seen_urls"] = list(seen)
                save_state(state)

                page += 1

            # Next query page
            query_index += 1
            page = 1
            state["query_index"] = query_index
            state["page"] = page
            save_state(state)

    print("Scrape complete.")


if __name__ == "__main__":
    main()