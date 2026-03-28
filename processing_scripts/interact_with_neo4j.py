from dataclasses import dataclass

from neo4j import GraphDatabase
import pandas as pd
import matplotlib.pyplot as plt
from typing import Any, Generator, cast

HOST = "100.65.19.90"
URI = f"neo4j://{HOST}:7687"
USER = "neo4j"
PASSWORD = "neo4j123"

date_format = "yyyy-MM-dd HH:mm:ss"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def load_df(query: str, params: dict | None = None) -> pd.DataFrame:
    with driver.session() as session:
        result = session.run(cast(Any, query), params or {})
        data = result.data()
    return pd.DataFrame(data)

artifacts_data = None

def load_artifact_creation_dates() -> pd.DataFrame:
    global artifacts_data
    if artifacts_data is not None:
        return artifacts_data
    artifacts_data = pd.read_csv(f"agents_claude_artifact_creations.csv")
    return artifacts_data

@dataclass
class RepoInfo:
    repository : str
    url : str
    branch : str
    branch_hash : str
    artifact_original_name : str
    artifact_creation_commit : str
    artifact_creation_date : str
    commits_before : int
    commits_after : int
    total_commits : int

    def to_dict(self):
        return {
            "repository": self.repository,
            "url": self.url,
            "branch": self.branch,
            "branch_hash": self.branch_hash,
            "artifact_original_name": self.artifact_original_name,
            "artifact_creation_commit": self.artifact_creation_commit,
            "artifact_creation_date": self.artifact_creation_date,
            "commits_before": self.commits_before,
            "commits_after": self.commits_after,
            "total_commits": self.total_commits,
        }

def iter_repos() -> Generator[RepoInfo, None, None]:
    for repo in load_artifact_creation_dates().itertuples(index=False):
        yield RepoInfo(*repo)

def get_included_file_extensions() -> list[str]:
    df = pd.read_csv("file_types_inclusion.csv")

    df["extension"] = (
        df["extension"]
        .astype(str)
        .str.replace('"', "", regex=False)
        .str.strip()
        .str.lower()
    )

    df["will_include"] = (
        df["will_include"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False})
    )

    included_extensions = (
        df.loc[df["will_include"] == True, "extension"]
        .dropna()
        .unique()
        .tolist()
    )

    return included_extensions

def get_file_extension_mappings() -> dict[str, str]:
    df = pd.read_csv("file_types_inclusion.csv")

    # Clean extension column caused by included escape quotes
    df["extension"] = (
        df["extension"]
        .astype(str)
        .str.replace('"', "", regex=False)
        .str.strip()
        .str.lower()
    )

    # Add back the leading dot for suffix matching in scripts
    df["extension"] = "." + df["extension"]

    # will_include to boolean
    df["will_include"] = (
        df["will_include"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False})
    )

    # Create a mapping of extension to category for included extensions
    extension_mapping = (
        df.loc[df["will_include"] == True, ["extension", "grouping"]]
        .dropna()
        .set_index("extension")["grouping"]
        .to_dict()
    )

    return extension_mapping # type: ignore

if __name__ == "__main__":
    # print(get_included_file_extensions())
    print(get_file_extension_mappings())