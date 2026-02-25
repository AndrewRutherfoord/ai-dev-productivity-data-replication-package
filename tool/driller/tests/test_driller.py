import logging
from datetime import datetime

from common.models.driller_config import (
    Filter,
    FilterMethod,
    FiltersConfig,
    PydrillerConfig,
    RepositoryConfig,
)
from pydriller import Commit

from src.drillers.driller import RepositoryDriller
from src.drillers.neo4j_pydriller_repository_storage import RepositoryNeo4jStorage
from src.drillers.pydriller_repository_storage import RepositoryDataStorage
from src.settings.default import (
    NEO4J_HOST,
    NEO4J_PASSWORD,
    NEO4J_PORT,
    NEO4J_USER,
    REPO_CLONE_LOCATION,
)

logger = logging.getLogger(__name__)

now = datetime.now()

period = datetime(2023, 1, 1)

# class TestConfigDriller(TestCase):
# def test_commit_drill():
#     storage = LogRepositoryStorage()

#     driller = RepositoryDriller("repos/pydriller", storage)

#     driller.drill_commits(since=period)
#     assert False


def test_commit_drill_neo4j_insert():
    storage = RepositoryNeo4jStorage(
        host=NEO4J_HOST,
        port=NEO4J_PORT,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD,
    )

    repo_config = RepositoryConfig(
        name="pydriller", url="https://github.com/ishepard/pydriller.git"
    )
    driller = RepositoryDriller(
        f"{REPO_CLONE_LOCATION }/pydriller", storage, repo_config
    )
    pydriller_filters = PydrillerConfig(since=period)
    driller.drill_repository()
    driller.drill_commits(pydriller_filters=pydriller_filters)

    storage.close()


class RepositoryTestStorage(RepositoryDataStorage):

    def store_repository(self, repo_name):
        assert repo_name == "pydriller"

    def store_branch(self, repo_name, branch_name):
        pass

    def store_commit(self, repo_name, commit):
        pass

    def store_developer(self, developer):
        pass

    def store_modified_file(self, commit, file, repository_name):
        pass


def setup_test_driller(storage_class):
    storage = storage_class()

    return RepositoryDriller(
        f"{REPO_CLONE_LOCATION }/pydriller",
        storage,
        RepositoryConfig(
            name="pydriller", url="https://github.com/ishepard/pydriller.git"
        ),
    )


def test_commit_exact_filter():
    msg = "Update continuous-integration-workflow.yml"

    class TestCaseStorage(RepositoryTestStorage):
        def store_commit(self, repo_name, commit: Commit):
            assert commit.msg == msg
            logger.info(commit.msg)

    driller = setup_test_driller(TestCaseStorage)

    driller.drill_repository()
    driller.drill_commits(
        pydriller_filters=PydrillerConfig(since=period),
        filters=FiltersConfig(
            commit=[
                Filter(
                    field="msg",
                    value=msg,
                    method=FilterMethod.exact,
                )
            ]
        ),
    )


def test_commit_contains_filter():
    check_str = "Update"

    class TestCaseStorage(RepositoryTestStorage):
        def store_commit(self, repo_name, commit: Commit):
            assert check_str in commit.msg
            logger.info(commit.msg)

    driller = setup_test_driller(TestCaseStorage)

    driller.drill_repository()
    driller.drill_commits(
        pydriller_filters=PydrillerConfig(since=period),
        filters=FiltersConfig(
            commit=[
                Filter(
                    field="msg",
                    value=check_str,
                    method=FilterMethod.contains,
                )
            ]
        ),
    )


# Tests the OR functionality with commit filters
def test_commit_contains_list_filter():
    check_strs = ["Update", "docs"]

    class TestCaseStorage(RepositoryTestStorage):
        def store_commit(self, repo_name, commit: Commit):
            logger.info(commit.msg)
            assert any(s in commit.msg for s in check_strs)

    driller = setup_test_driller(TestCaseStorage)

    driller.drill_repository()
    driller.drill_commits(
        pydriller_filters=PydrillerConfig(since=period),
        filters=FiltersConfig(
            commit=[
                Filter(
                    field="msg",
                    value=check_strs,
                    method=FilterMethod.contains,
                )
            ],
        ),
    )


# Tests the AND functionality with commit filters
def test_commit_contains_filter_AND():
    check_strs = ["Update", "docs"]

    class TestCaseStorage(RepositoryTestStorage):
        def store_commit(self, repo_name, commit: Commit):
            logger.info(commit.msg)
            assert all(s in commit.msg for s in check_strs)

    driller = setup_test_driller(TestCaseStorage)
    driller.drill_repository()
    driller.drill_commits(
        pydriller_filters=PydrillerConfig(since=period),
        filters=FiltersConfig(
            commit=[
                Filter(
                    field="msg",
                    value=check_strs[0],
                    method=FilterMethod.contains,
                ),
                Filter(
                    field="msg",
                    value=check_strs[1],
                    method=FilterMethod.contains,
                ),
            ]
        ),
    )
