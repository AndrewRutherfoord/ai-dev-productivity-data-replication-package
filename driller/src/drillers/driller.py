import logging
from pydriller import Repository, Commit

from common.models.driller_config import (
    RepositoryConfig,
    PydrillerConfig,
    FiltersConfig,
)
from pydriller.domain.commit import ModifiedFile
from src.drillers.pydriller_repository_storage import RepositoryDataStorage

logger = logging.getLogger(__name__)


class RepositoryDriller:
    """Drills a repository with PyDriller and inserts the data into the given repository storage.
    Uses dependency injection to separate storage of repository data from the storage of the data.
    This could theoretically make it possible to implement a storage for a relational database or some other storage system.
    """

    def __init__(
        self,
        repository_path: str,
        storage: RepositoryDataStorage,
        config: RepositoryConfig,
    ):
        self.repository_path = repository_path
        self.repository_name = config.name
        # Use URL as unique identifier; fall back to name for local repos
        self.repository_url = config.url if config.url else config.name
        self.storage: RepositoryDataStorage = storage
        self.config: RepositoryConfig = config

    def get_commits(self, pydriller_filters: PydrillerConfig | None = None):
        """Gets the commit iterator from Pydriller with the provided pydriller configurations"""

        kwargs = {}
        if pydriller_filters is not None:
            kwargs = pydriller_filters.model_dump(exclude_none=True, exclude_unset=True)
            kwargs["since"] = pydriller_filters.since
            kwargs["to"] = pydriller_filters.to

        return Repository(self.repository_path, **kwargs).traverse_commits()

    def _handle_branches(self, branch_names: list[str]):
        """Stores a list of branch names."""
        for b in branch_names:
            self.storage.store_branch(self.repository_url, b)

    def _handle_committer(self, committer):
        self.storage.store_developer(committer)

    def _handle_modified_files(self, commit: Commit, files: list[ModifiedFile]):
        """Iterates over the modified files of a commit and passes them to the storage."""
        if self.config.index_file_diff is None:
            self.config.index_file_diff = False
        for file in files:
            self.storage.store_modified_file(
                commit,
                file,
                self.repository_url,
                index_diff=self.config.index_file_diff,
            )

    def drill_commits(
        self,
        filters: FiltersConfig | None = None,
        pydriller_filters: PydrillerConfig | None = None,
    ):
        """Drills all the commits based on the filters and pydriller configs.
        Inserts all the data into the storage.
        Args:
            filters (dict, optional): Filters to apply to the commits. Defaults to {}.
            pydriller_filters (dict, optional): Pydriller configurations. Defaults to {}.
            index_file_modifications (bool, optional): Whether to index file modifications. Defaults to True.
        """
        counter = 0
        for commit in self.get_commits(pydriller_filters):
            if self.commit_filter(commit, filters):
                self._handle_branches(list(commit.branches))
                self._handle_committer(commit.author)

                self.storage.store_commit(self.repository_url, commit)
                counter += 1
                if self.config.index_file_modifications:
                    self._handle_modified_files(commit, commit.modified_files)
            if counter % 100 == 0 and counter > 0:
                logger.info(f"Processed {counter} commits")

    def commit_filter(
        self, commit, filter_configs: FiltersConfig | None = None
    ) -> bool:
        """Used to determine whether a commit should be inserted into the database

        Args:
            commit (Commit): PyDriller Commit instance.

        Returns:
            bool: whether it should be indexed. If True, commit inserted into storage.
        """

        if filter_configs is None:
            # If no filters given, then automatically accept.
            return True

        for item in filter_configs.commit:

            value = getattr(commit, item.field, f"`{item.field}` not in Commit.")

            # TODO: This can probably be done in a nicer way.
            # TODO: Regex support??
            if isinstance(item.value, list):
                if item.method == "exact" and not any(fv == value for fv in item.value):
                    return False
                elif item.method == "!exact" and any(fv == value for fv in item.value):
                    return False
                elif item.method == "contains" and not any(
                    fv in value for fv in item.value
                ):
                    return False
                elif item.method == "!contains" and any(
                    fv in value for fv in item.value
                ):
                    return False
            else:
                if item.method == "exact" and value != item.value:
                    return False
                elif item.method == "!exact" and value == item.value:
                    return False
                elif item.method == "contains" and item.value not in value:
                    return False
                elif item.method == "!contains" and item.value in value:
                    return False

        return True

    def drill_repository(self):
        """Drills the repository information and inserts it into the storage."""
        self.storage.store_repository(self.repository_name, self.repository_url)
