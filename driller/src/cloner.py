import logging
import os
import shutil
from git import GitCommandError, InvalidGitRepositoryError, Repo

logger = logging.getLogger(__name__)


def clone_repository(repository_url, repository_location):
    """Clones a Git Repository to a specified local directory.

    Args:
        repository_url (str): http url for a git repository
        repository_location (str): location where the repository should be cloned to

    Throws:
        `GitCommandError` when git clone fails
        `InvalidGitRepositoryError` if directory already exists and isn't a git repository.
    """

    try:
        if os.path.exists(repository_location):
            repo = Repo(repository_location)
            if repo.remotes.origin.url == repository_url:
                logger.info(f"Repo `{repository_url}` already cloned. Pulling latest changes.")
                repo.remotes.origin.pull()
                return
            else:
                return  # Another repo at location
        Repo.clone_from(repository_url, repository_location)

    except GitCommandError as e:
        stderr = str(e.stderr) if e.stderr else str(e)
        if "rate limit" in stderr.lower() or "403" in stderr:
            logger.error(f"Rate limited by remote host when cloning `{repository_url}`.")
            raise ConnectionError(f"Rate limited by remote host: {repository_url}")
        elif "not found" in stderr.lower() or "404" in stderr:
            logger.error(f"Repository `{repository_url}` not found on remote host.")
            raise LookupError(f"Repository not found: {repository_url}")
        else:
            logger.error(f"Git clone failed for `{repository_url}`: {stderr}")
            raise ConnectionError(f"Git clone failed for {repository_url}: {stderr}")
    except InvalidGitRepositoryError as e:
        logger.error(
            f"Directory `{repository_location}` already exists but isn't a Git Repo."
        )
        raise e  # Directory exists but not a Git repo.
    except Exception as e:
        logger.exception(e)
        raise e


def remove_repository_clone(repository_location):
    """Deletes a folder from a given path. Intended to be used with repositories, but is just deleting a folder."""
    try:
        if os.path.exists(repository_location):
            shutil.rmtree(repository_location)
    except Exception as e:
        logger.exception(e)
        raise e
