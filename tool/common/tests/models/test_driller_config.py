from datetime import datetime
import json
from src.models.driller_config import (
    DrillConfig,
    Filter,
    FilterMethod,
    FiltersConfig,
    RepositoryConfig,
    DefaultsConfig,
    PydrillerConfig,
    SingleDrillConfig,
)

import logging

logger = logging.getLogger(__name__)


def all_other_none(data: dict, not_none_fields):
    # Utility function to check that all fields in data are None except for the ones in not_none_fields
    for key, value in data.items():
        if key not in not_none_fields:
            assert value is None
        else:
            assert value is not None


def test_parse_minimum_repository_config():
    """Test that RepositoryConfig parses the minimum config correctly"""

    data = {"name": "test", "url": "https://github.com/test/test.git"}

    conf = RepositoryConfig.model_validate(data)

    all_other_none(conf.model_dump(), ["name", "url"])


def test_parse_defaults_config():
    data = {}

    conf = DefaultsConfig.model_validate(data)

    all_other_none(
        conf.model_dump(),
        [
            "delete_clone",
            "index_file_modifications",
            "index_file_diff",
        ],
    )


def test_parse_minimum_pydriller():
    data = {}

    conf = PydrillerConfig.model_validate(data)

    all_other_none(conf.model_dump(), [])


def test_apply_bool_defaults():

    defaults = DefaultsConfig(
        delete_clone=True,
        index_file_modifications=True,
        index_file_diff=True,
    )

    conf = RepositoryConfig(
        name="test", url="https://github.com/test/test.git", index_file_diff=False
    )

    assert not conf.delete_clone
    assert not conf.index_file_diff

    conf.apply_defaults(defaults)

    assert conf.delete_clone

    # Should stay false because it's set in repo config
    assert not conf.index_file_diff


def test_apply_none_pydriller_defaults():
    defaults = DefaultsConfig(
        pydriller=PydrillerConfig(
            to_commit="hash",
            from_commit="abc123",
        )
    )

    conf = RepositoryConfig(
        name="test",
        url="https://github.com/test/test.git",
    )

    assert conf.pydriller is None

    conf.apply_defaults(defaults)

    assert conf.pydriller is not None
    assert conf.pydriller.to_commit == "hash" 
    assert conf.pydriller.from_commit == "abc123"


def test_apply_pydriller_defaults():
    defaults = DefaultsConfig(
        pydriller=PydrillerConfig(
            to_tag="default-tag", to_commit="default-to-commit-hash"
        )
    )

    conf = RepositoryConfig(
        name="test",
        url="https://github.com/test/test.git",
        pydriller=PydrillerConfig(
            from_commit="from-commit-hash",
            to_commit="to-commit-hash",
        ),
    )

    conf.apply_defaults(defaults)

    assert conf.pydriller.to_tag == "default-tag"
    assert conf.pydriller.to_commit == "to-commit-hash"
    assert conf.pydriller.from_commit == "from-commit-hash"


def test_apply_none_filters_defaults():
    defaults = DefaultsConfig(
        filters=FiltersConfig(
            commit=[
                Filter(
                    field="author",
                    value="test",
                    method=FilterMethod.exact,
                ),
            ],
        )
    )
    conf = RepositoryConfig(
        name="test",
        url="https://github.com/test/test.git",
    )

    assert conf.filters is None

    conf.apply_defaults(defaults)

    assert conf.filters is not None
    assert len(conf.filters.commit) == 1
    assert conf.filters.commit[0].field == "author"
    assert conf.filters.commit[0].value == "test"
    assert conf.filters.commit[0].method == FilterMethod.exact


def test_parse_single_drill_config_json():
    data = {
        "job_id": 1,
        "repository": {
            "name": "test",
            "url": "https://github.com/test/test.git",
            "pydriller": {
                "since": "2023-01-01",
                "to": "2023-01-02",
            },
        },
    }

    json_data = json.dumps(data)

    config = SingleDrillConfig.model_validate_json(json_data)

    assert config.job_id == 1
    assert config.repository.name == "test"
    assert config.defaults is None
    assert config.repository.pydriller is not None


def test_pydriller_config_parse_dates():
    data = {
        "since": "2023-01-01",
        "to": "2023-01-02",
    }

    config = PydrillerConfig.model_validate(data)

    assert config.since == datetime(2023, 1, 1)
    assert config.to == datetime(2023, 1, 2)
    
def test_pydriller_config_serialize_date():
    config = PydrillerConfig(since=datetime(2023,1,1), to=datetime(2023,1,2))

    config_json = json.loads(config.model_dump_json())
    
    assert config_json["since"] == "2023-01-01"
    assert config_json["to"] == "2023-01-02"
    
    