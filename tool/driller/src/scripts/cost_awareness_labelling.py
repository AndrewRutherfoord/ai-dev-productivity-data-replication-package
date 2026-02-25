import json
import logging
import sys
from typing import Optional

from pydantic import BaseModel
from src.drillers.neo4j_storage import Neo4jStorage

""" For case study of reproducing data from `Cloud Cost Awareness` study.
Replication package that this replication is based on: https://github.com/feitosa-daniel/cloud-cost-awareness

Aim of this script is to add the commit labels to the Neo4j Database. During the the original study the 
commit and issues were manually labelled by the researchers based on the commit message contents. 

In this replication of their data we will focus on the commit messages, so issues will be filtered out in this script. 

**Note**: This script assumes that the repositories from the study have been mined and the commits are in the database.

This does the following:
1. Loads the dataset which contains the commit and the codes that were assigned to it
2. Load the codes (this contains the name of the code and it's description)
3. Filter out the issues from the dataset (since we aren't using them in this replication)
4. Extract the commit hashes from the GitHub commit URLs
5. For each code, a node is created on the database of type `Code` which contains the name and description
6. For each commit, it is linked to the relevant with a `Member_OF` relationship.
    - If a given commit hash is not present in the database, it will just be skipped. Won't fail.

**Executing the script:**

Best to run it inside docker since all Env variables will be set already.

```
docker compose run driller-worker poetry run python3 -m driller.scripts.cost_awareness_labelling
```
"""

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))
neo4j_logger = logging.getLogger("neo4j")
neo4j_logger.setLevel(logging.INFO)
neo4j_logger.addHandler(logging.StreamHandler(sys.stdout))

"""Pydantic models used for holding data loaded from datasets."""


class LabelledCommit(BaseModel):
    type: str
    url: str
    hash: Optional[str] = None
    content: dict
    codes: list[str]


class Code(BaseModel):
    name: str
    description: str


class LabellingStorage(Neo4jStorage):
    """Uses `Neo4jStorage` to easily access the Neo4j database."""

    def load_codes(self):
        """Loads the codes dataset into pydantic models."""
        with open("./driller/scripts/cost_awareness_codes.json", "r") as file:
            codes = json.load(file)
        self.codes = list(map(lambda c: Code.model_validate(c), codes))
        # for code in codes:
        #     self.codes.append(Code.model_validate(code))

    def load_dataset(self):
        """Loads the commit and issue data with the codes into `self.dataset` in LabelledCommit objects."""
        with open("./driller/scripts/cost_awareness_dataset.json", "r") as file:
            data = json.load(file)

        self.dataset: list[LabelledCommit] = []
        for item in data:
            obj = LabelledCommit.model_validate(item)
            self.dataset.append(obj)

    def get_commit_hash_from_url(self, url: str):
        """Extracts the commit hash from the GitHub commit url.
        Assumes that hash is the part of the URL.

        Raises:
            ValueError: If url is in the wrong format.
        """
        url_split = url.split("/")

        if url_split[-2] != "commit":
            raise ValueError(f"URL in the wrong format:  {url}")

        return url_split[-1]

    def filter_remove_issues(self):
        """In this case I am only using commit data, but dataset contains labelled issues."""

        self.dataset = list(filter(lambda o: o.type == "commit", self.dataset))

    def add_commit_hashes(self):
        """For each LabelledCommit, extracts and adds the commit hash"""
        for obj in self.dataset:
            obj.hash = self.get_commit_hash_from_url(obj.url)

    def store_code(self, code: Code):
        """Stores a code as a `Code` node with name and description."""
        logger.debug(f"Storing code {code.name}")
        self._run_query(
            "MERGE (code:Code {name: $name}) SET code.description = $description",
            {"name": code.name, "description": code.description},
        )

    def store_codes(self):
        for code in self.codes:
            self.store_code(code)

    def store_code_commit_relationship(self, code: str, commit_hash: str):
        """Creates the `MEMBER_OF` relationship between the commit and the code"""
        logger.debug(
            f"Creating relationship `MEMBER_OF` between commit {commit_hash} and code {code}."
        )
        self._run_query(
            "MATCH (commit:Commit {hash: $commit_hash}) "
            "MATCH (code:Code {name: $code_name})"
            "MERGE (commit)-[:MEMBER_OF]->(code)",
            {"commit_hash": commit_hash, "code_name": code},
        )

    def store_code_commit_relationships(self):
        """Creates all the code-commit relationships"""
        for obj in self.dataset:
            if obj.hash is None:
                raise ValueError("Expected a string commit hash, not None.")

            for code in obj.codes:
                self.store_code_commit_relationship(code, obj.hash)

    def execute(self):
        """Executes all of the steps of the insertion of the labels."""

        # Loading Datasets
        self.load_dataset()
        self.load_codes()

        logger.info("Dataset & Codes Loaded.")

        # Filtering out issue and extracting commit hashes.
        self.filter_remove_issues()
        self.add_commit_hashes()

        logger.info("Setup Complete. Adding to DB.")

        # Storing each code as a node on DB
        self.store_codes()

        logger.info("Codes stored.")

        # Creates the relationships between the commits and the codes.
        self.store_code_commit_relationships()

        logger.info("Complete.")


def run():
    # Create the labelling storage instance. Also connects to the database as the same time.
    storage = LabellingStorage(
        user="neo4j", password="neo4j123", host="neo4j", port=7687, batch_size=10
    )

    storage.execute()

    # Disconnect from Neo4j
    storage.close()


if __name__ == "__main__":
    run()
