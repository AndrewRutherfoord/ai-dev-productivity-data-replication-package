from enum import Enum
from pydantic import (
    BaseModel,
    ValidationError,
    field_validator,
    field_serializer,
    ConfigDict,
)
from typing import List, Optional
from datetime import datetime


class PydrillerConfig(BaseModel):
    """Holds the arguments for the Pydriller Repository class instance used in drilling.
    Documentation for each argument's meaning at https://pydriller.readthedocs.io/en/latest/repository.html.
    """

    since: Optional[datetime] = None
    to: Optional[datetime] = None
    from_commit: Optional[str] = None
    to_commit: Optional[str] = None
    from_tag: Optional[str] = None
    to_tag: Optional[str] = None
    only_in_branch: Optional[str] = None
    only_no_merge: Optional[bool] = None
    only_authors: Optional[list[str]] = None
    only_commits: Optional[list[str]] = None
    only_release: Optional[bool] = None
    filepath: Optional[str] = None
    only_modifications_with_file_types: Optional[list[str]] = None

    @field_validator("since", "to")
    def parse_dates(cls, value):
        """Parses datetime strings of the format YYYY-MM-DD. Is applied to `since` and `to` variables."""

        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_serializer("since", "to")
    def serialize_dt(self, dt: datetime, _info):
        """Converts the datetime object to a string in the format of YYYY-MM-DD. Is applied to `since` and `to` variables."""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d")

    def apply_defaults(self, defaults):
        for attr in vars(defaults):
            if getattr(self, attr) is None:
                setattr(self, attr, getattr(defaults, attr))


class FilterMethod(str, Enum):
    exact = "exact"  # Checks if field's value is exactly equal to search value
    not_exact = "!exact"  # Checks if field's value is not equal to search value
    contains = "contains"  # Checks if field's value contains the search value
    not_contains = (
        "!contains"  # Checks if field's value does not contain the search value
    )


class Filter(BaseModel):
    field: str
    value: str | list[str]
    method: FilterMethod = FilterMethod.contains

    model_config = {"use_enum_values": True}


class FiltersConfig(BaseModel):
    commit: list[Filter] = []

    def apply_defaults(self, defaults):
        if len(self.commit) < 1:
            self.commit = defaults.commit


class DefaultsConfig(BaseModel):
    delete_clone: bool = False
    index_file_modifications: bool = False
    index_file_diff: bool = False
    compute_dmm: bool = False
    skip_existing_commits: bool = True
    pydriller: Optional[PydrillerConfig] = None
    filters: Optional[FiltersConfig] = None


class RepositoryConfig(DefaultsConfig):
    name: str
    url: Optional[str] = None

    # Have to set to None because to make it optional
    delete_clone: Optional[bool] = None
    index_file_modifications: Optional[bool] = None
    index_file_diff: Optional[bool] = None
    compute_dmm: Optional[bool] = None
    skip_existing_commits: Optional[bool] = None

    def apply_defaults(self, defaults: DefaultsConfig):
        """Applies the defaults to the repository config. If value is set to None, it will be set to the default value (if one exists).

        Args:
            defaults (DefaultsConfig): The defaults to apply.
        """
        if self.delete_clone is None and defaults.delete_clone is not None:
            self.delete_clone = defaults.delete_clone
        if self.index_file_modifications is None:
            self.index_file_modifications = defaults.index_file_modifications
        if self.index_file_diff is None:
            self.index_file_diff = defaults.index_file_diff
        if self.compute_dmm is None:
            self.compute_dmm = defaults.compute_dmm
        if self.skip_existing_commits is None:
            self.skip_existing_commits = defaults.skip_existing_commits

        if self.pydriller is None:
            self.pydriller = defaults.pydriller
        else:
            self.pydriller.apply_defaults(defaults.pydriller)

        if self.filters is None:
            self.filters = defaults.filters
        else:
            self.filters.apply_defaults(defaults.filters)


class DrillConfig(BaseModel):
    defaults: DefaultsConfig
    repositories: list[RepositoryConfig]


class SingleDrillConfig(BaseModel):
    defaults: Optional[DefaultsConfig] = None
    repository: RepositoryConfig

    job_id: Optional[int] = None

    def apply_defaults(self):
        """Applies the defaults to the repository config.

        Returns:
            RepositoryConfig: The repository config with the defaults applied. (Also store in self.repository)
        """
        if self.defaults is None:
            self.repository.apply_defaults(self.defaults)
        return self.repository
