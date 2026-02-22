from abc import ABC, abstractmethod
from pydriller import Commit
from pydriller.domain.commit import Developer, ModifiedFile

import logging

logger = logging.getLogger(__name__)


class RepositoryDataStorage(ABC):
    @abstractmethod
    def store_repository(self, repo_name: str, repo_url: str):
        pass

    @abstractmethod
    def store_branch(self, repo_url: str, branch_name: str):
        pass

    @abstractmethod
    def store_commit(self, repo_url: str, commit: Commit, compute_dmm: bool = False):
        pass

    @abstractmethod
    def store_developer(self, developer: Developer):
        pass

    @abstractmethod
    def store_modified_file(
        self,
        commit: Commit,
        file: ModifiedFile,
        repository_url: str,
        index_diff=False,
        include_metrics: bool = True,
    ):
        pass

    @abstractmethod
    def commit_exists(self, commit_hash: str) -> bool:
        pass

    @abstractmethod
    def commit_has_modifications(self, commit_hash: str, expected_count: int) -> bool:
        pass


class LogRepositoryStorage(RepositoryDataStorage):
    """An example Repository storage which logs the data to the console.
    Just for testing purposes.
    """

    def __init__(self):
        pass

    def store_commit(self, repo_url: str, commit: Commit, compute_dmm: bool = False):
        logger.info(
            {
                "repository_url": repo_url,
                "hash": commit.hash,
                "message": commit.msg,
                "author": commit.author.name,
                "date": commit.author_date.strftime("%Y-%m-%d %H:%M:%S"),
                "parents": commit.parents,
                "dmm_unit_size": commit.dmm_unit_size if compute_dmm else None,
                "dmm_unit_complexity": commit.dmm_unit_complexity if compute_dmm else None,
                "dmm_unit_interfacing": commit.dmm_unit_interfacing if compute_dmm else None,
                "merge": commit.merge,
            }
        )

    def store_repository(self, repo_name, repo_url):
        logger.info(f"{repo_name} ({repo_url})")

    def store_branch(self, repo_url, branch_name):
        logger.info(f"Branch {branch_name} from {repo_url}.")

    def store_developer(self, developer: Developer):
        logger.info(f"Developer {developer.name} ({developer.email}).")

    def store_modified_file(
        self,
        commit,
        file,
        repository_url,
        index_diff=False,
        include_metrics: bool = True,
    ):
        logger.info(f"Modified file {file.filename} in commit {commit.hash}.")

    def commit_exists(self, commit_hash: str) -> bool:
        return False

    def commit_has_modifications(self, commit_hash: str, expected_count: int) -> bool:
        return False
