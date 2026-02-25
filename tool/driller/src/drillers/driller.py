import logging
import time
from collections import Counter
from pathlib import Path
from pydriller import Repository, Commit

from common.models.driller_config import (
    RepositoryConfig,
    PydrillerConfig,
    FiltersConfig,
)
from pydriller.domain.commit import ModifiedFile
from src.drillers.pydriller_repository_storage import RepositoryDataStorage

logger = logging.getLogger(__name__)


IGNORED_PATH_PARTS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "coverage",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "venv",
}

IGNORED_FILE_EXTENSIONS = {
    # Archives / compressed files
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".jar",
    ".war",
    ".ear",
    # Images
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".svg",
    ".ico",
    ".avif",
    ".heic",
    # Audio / video
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".aac",
    ".m4a",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".wmv",
    ".m4v",
    # Source maps
    ".map",
    # Binary executables and libraries
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".class",
    ".o",
    ".a",
    ".pyc",
    ".pyo",
    # Documents and other large non-code artifacts
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
}

MAX_INDEXED_DIFF_CHARS = 400_000
MAX_FILE_DIFF_CHARS = 1_000_000
MAX_FILE_NLOC = 50_000
FILE_PROGRESS_LOG_INTERVAL = 10
FILE_SLOW_THRESHOLD_SECONDS = 30
FILE_STORAGE_SLOW_THRESHOLD_SECONDS = 60


def _candidate_path(file: ModifiedFile) -> str:
    return file.new_path or file.old_path or file.filename or ""


def _path_parts(path: str) -> set[str]:
    return {
        part.lower()
        for part in path.replace("\\", "/").split("/")
        if part and part not in {".", ".."}
    }


def _looks_binary_diff(diff: str | None) -> bool:
    if not diff:
        return False
    return "\x00" in diff


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

    def _should_index_diff(self, file: ModifiedFile) -> bool:
        if not self.config.index_file_diff:
            return False

        candidate_path = _candidate_path(file)
        if not candidate_path:
            return False

        lower_path = candidate_path.lower()

        if any(lower_path.endswith(ext) for ext in IGNORED_FILE_EXTENSIONS):
            return False

        if _path_parts(candidate_path) & IGNORED_PATH_PARTS:
            return False

        if (file.added_lines + file.deleted_lines) > 10_000:
            return False

        return True

    def _diff_skip_reason(self, file: ModifiedFile) -> str:
        if not self.config.index_file_diff:
            return "diff_disabled"

        candidate_path = _candidate_path(file)
        if not candidate_path:
            return "missing_path"

        lower_path = candidate_path.lower()

        matched_ext = next(
            (ext for ext in IGNORED_FILE_EXTENSIONS
            if lower_path.endswith(ext)),
            None,
        )
        if matched_ext:
            return f"ignored_extension:{matched_ext}"

        blocked_path_parts = _path_parts(candidate_path) & IGNORED_PATH_PARTS
        if blocked_path_parts:
            return f"ignored_path:{next(iter(blocked_path_parts))}"

        churn = file.added_lines + file.deleted_lines
        if churn > 10_000:
            return f"diff_too_large_by_churn:{churn}"

        return "unknown"

    def _handle_modified_files(self, commit: Commit, files: list[ModifiedFile]):
        """Iterates over the modified files of a commit and passes them to the storage."""
        if self.config.index_file_diff is None:
            self.config.index_file_diff = False

        started_at = time.monotonic()
        indexed_files = 0
        indexed_diffs = 0
        skipped_diffs = 0
        diff_skip_reasons = Counter()

        logger.info(
            "Commit %s: starting file loop (%s files)", commit.hash, len(files)
        )

        for index, file in enumerate(files, start=1):
            file_started_at = time.monotonic()

            logger.info(
                "Commit %s: processing file %s/%s (%s)",
                commit.hash,
                index,
                len(files),
                _candidate_path(file),
            )

            should_index_diff = self._should_index_diff(file)
            if self.config.index_file_diff and not should_index_diff:
                skipped_diffs += 1
                diff_skip_reasons[self._diff_skip_reason(file)] += 1
                logger.info(
                    "Skipping diff content for file %s in commit %s",
                    _candidate_path(file),
                    commit.hash,
                )
            elif should_index_diff:
                indexed_diffs += 1

            store_started_at = time.monotonic()
            self.storage.store_modified_file(
                commit,
                file,
                self.repository_url,
                index_diff=should_index_diff,
                include_metrics=should_index_diff,
            )
            store_elapsed = time.monotonic() - store_started_at
            if store_elapsed > FILE_STORAGE_SLOW_THRESHOLD_SECONDS:
                logger.warning(
                    "Commit %s: storing file relation %s/%s (%s) took %.1fs",
                    commit.hash,
                    index,
                    len(files),
                    _candidate_path(file),
                    store_elapsed,
                )
            indexed_files += 1

            file_elapsed = time.monotonic() - file_started_at
            if file_elapsed > FILE_SLOW_THRESHOLD_SECONDS:
                logger.warning(
                    "Commit %s: file %s/%s (%s) took %.1fs",
                    commit.hash,
                    index,
                    len(files),
                    _candidate_path(file),
                    file_elapsed,
                )

            if index % FILE_PROGRESS_LOG_INTERVAL == 0:
                elapsed = time.monotonic() - started_at
                logger.info(
                    "Commit %s progress: %s/%s files processed (indexed=%s, skipped=%s, diff_indexed=%s, diff_skipped=%s, elapsed=%.1fs)",
                    commit.hash,
                    index,
                    len(files),
                    indexed_files,
                    0,
                    indexed_diffs,
                    skipped_diffs,
                    elapsed,
                )

        elapsed = time.monotonic() - started_at
        logger.info(
            "Commit %s file processing complete: total=%s, indexed=%s, skipped=%s, diff_indexed=%s, diff_skipped=%s, elapsed=%.1fs",
            commit.hash,
            len(files),
            indexed_files,
            0,
            indexed_diffs,
            skipped_diffs,
            elapsed,
        )
        if diff_skip_reasons:
            logger.info(
                "Commit %s diff skip reasons: %s",
                commit.hash,
                dict(diff_skip_reasons),
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
                if self.config.skip_existing_commits and self.storage.commit_exists(commit.hash):
                    needs_modifications = (
                        self.config.index_file_modifications
                        and not self.storage.commit_has_modifications(commit.hash, len(commit.modified_files))
                    )
                    if not needs_modifications:
                        logger.info("Skipping already processed commit %s", commit.hash)
                        counter += 1
                        if counter % 100 == 0:
                            logger.info(f"Processed {counter} commits")
                        continue
                    # Commit exists but modifications were never stored — process files only.
                    logger.info(
                        "Commit %s exists but has no modifications; indexing files only", commit.hash
                    )
                    self._handle_modified_files(commit, commit.modified_files)
                    counter += 1
                    if counter % 100 == 0:
                        logger.info(f"Processed {counter} commits")
                    continue

                logger.info(
                    "Processing commit %s (%s modified files, index_file_modifications=%s, index_file_diff=%s)",
                    commit.hash,
                    len(commit.modified_files),
                    self.config.index_file_modifications,
                    self.config.index_file_diff,
                )
                self._handle_branches(list(commit.branches))
                self._handle_committer(commit.author)

                if self.config.compute_dmm:
                    logger.info("Storing commit %s metadata (computing DMM metrics)…", commit.hash)
                else:
                    logger.info("Storing commit %s metadata (DMM disabled)", commit.hash)
                self.storage.store_commit(self.repository_url, commit, compute_dmm=self.config.compute_dmm)
                counter += 1
                if self.config.index_file_modifications:
                    logger.info("Beginning file modification indexing for commit %s", commit.hash)
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
