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

def load_df(query: str) -> pd.DataFrame:
    with driver.session() as session:
        data = session.run(cast(Any, query)).data()
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

def iter_repos() -> Generator[RepoInfo, None, None]:
    for repo in load_artifact_creation_dates().itertuples(index=False):
        yield RepoInfo(*repo)