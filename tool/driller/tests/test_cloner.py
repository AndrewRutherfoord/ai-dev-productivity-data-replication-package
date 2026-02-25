import pytest
from unittest.mock import patch
from src.cloner import clone_repository
from git import InvalidGitRepositoryError, GitCommandError


@patch("driller.cloner.os.path.exists")
@patch("driller.cloner.Repo")
def test_clone_repository_already_cloned(mock_repo, mock_path_exists):
    mock_path_exists.return_value = True
    mock_repo.return_value.remotes.origin.url = "http://example.com/repo.git"

    clone_repository("http://example.com/repo.git", "/path/to/repo")

    mock_repo.assert_called_with("/path/to/repo")


@patch("driller.cloner.os.path.exists")
@patch("driller.cloner.Repo")
def test_clone_repository_invalid_repo(mock_repo, mock_path_exists):
    mock_path_exists.return_value = True
    mock_repo.side_effect = InvalidGitRepositoryError

    with pytest.raises(InvalidGitRepositoryError):
        clone_repository("http://example.com/repo.git", "/path/to/repo")

    mock_repo.assert_called_with("/path/to/repo")


@patch("driller.cloner.os.path.exists")
@patch("driller.cloner.Repo")
def test_clone_repository_clone_successful(mock_repo, mock_path_exists):
    mock_path_exists.return_value = False

    clone_repository("http://example.com/repo.git", "/path/to/repo")

    mock_repo.clone_from.assert_called_with(
        "http://example.com/repo.git", "/path/to/repo"
    )


@patch("driller.cloner.os.path.exists")
@patch("driller.cloner.Repo")
def test_clone_repository_clone_failure(mock_repo, mock_path_exists):
    mock_path_exists.return_value = False
    mock_repo.clone_from.side_effect = GitCommandError("clone", "error")

    with pytest.raises(LookupError, match="Repository not found on remote host."):
        clone_repository("http://example.com/repo.git", "/path/to/repo")

    mock_repo.clone_from.assert_called_with(
        "http://example.com/repo.git", "/path/to/repo"
    )


if __name__ == "__main__":
    pytest.main()
