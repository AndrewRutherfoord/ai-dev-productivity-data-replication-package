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
    def store_commit(self, repo_url: str, commit: Commit):
        pass

    @abstractmethod
    def store_developer(self, developer: Developer):
        pass

    @abstractmethod
    def store_modified_file(
        self, commit: Commit, file: ModifiedFile, repository_url: str, index_diff=False
    ):
        pass


class LogRepositoryStorage(RepositoryDataStorage):
    """An example Repository storage which logs the data to the console.
    Just for testing purposes.
    """

    def __init__(self):
        pass

    def store_commit(self, repo_url: str, commit: Commit):
        logger.info(
            {
                "repository_url": repo_url,
                "hash": commit.hash,
                "message": commit.msg,
                "author": commit.author.name,
                "date": commit.author_date.strftime("%Y-%m-%d %H:%M:%S"),
                "parents": commit.parents,
                "dmm_unit_size": commit.dmm_unit_size,
                "dmm_unit_complexity": commit.dmm_unit_complexity,
                "dmm_unit_interfacing": commit.dmm_unit_interfacing,
                "merge": commit.merge,
            }
        )

    def store_repository(self, repo_name, repo_url):
        logger.info(f"{repo_name} ({repo_url})")

    def store_branch(self, repo_url, branch_name):
        logger.info(f"Branch {branch_name} from {repo_url}.")
