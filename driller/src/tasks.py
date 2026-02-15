"""Celery task definitions for drilling repositories"""
import logging
import os
from celery import Task

from common.models.driller_config import SingleDrillConfig, RepositoryConfig
from src.drillers.driller import RepositoryDriller
from src.drillers.neo4j_pydriller_repository_storage import RepositoryNeo4jStorage
from src.celery_app import app
from src.cloner import clone_repository, remove_repository_clone
from src.log_buffer import LogBuffer, LogBufferHandler

logger = logging.getLogger(__name__)

# Get settings from environment
BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")

# Get settings from environment
NEO4J_HOST = os.environ.get("NEO4J_HOST", "neo4j")
NEO4J_PORT = os.environ.get("NEO4J_PORT", 7687)
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
REPO_CLONE_LOCATION = os.environ.get("REPO_CLONE_LOCATION", "/app/repositories")


class CallbackTask(Task):
    """Base task with callback support for status updates"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        logger.error(f"Task {task_id} failed: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        logger.info(f"Task {task_id} completed successfully")


@app.task(
    base=CallbackTask,
    bind=True,
    max_retries=3,
    soft_time_limit=3600,
    time_limit=3900,
    acks_late=True,
    reject_on_worker_lost=True,
)
def drill_repository(self, drill_config_json: str) -> dict:
    """
    Drill a repository and store results in Neo4j.

    Args:
        drill_config_json: JSON string of SingleDrillConfig

    Returns:
        dict: {"status": "complete", "job_id": int, "message": str}
    """
    drill_config = None
    storage = None
    log_buffer = None
    log_handler = None

    try:
        # Parse config
        drill_config = SingleDrillConfig.model_validate_json(drill_config_json)
        job_id = drill_config.job_id
        repository = drill_config.repository

        # Set up log buffer to send logs to backend periodically
        log_buffer = LogBuffer(job_id, BACKEND_URL, send_interval=5)
        log_handler = LogBufferHandler(log_buffer)
        log_handler.setLevel(logging.INFO)
        log_handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))
        logger.addHandler(log_handler)
        log_buffer.start()

        logger.info(f"Starting drill for {repository.name} (job_id={job_id})")

        # Apply defaults to repository config
        if drill_config.defaults:
            repository.apply_defaults(drill_config.defaults)

        # Set path to clone or find repo
        repo_path = f"{REPO_CLONE_LOCATION}/{repository.name}"

        # Clone repository if URL exists
        if repository.url is not None:
            clone_repository(
                repository_url=repository.url,
                repository_location=repo_path
            )
            logger.debug(f"Cloned repository {repository.name} to {repo_path}")

        # Initialize storage
        storage = RepositoryNeo4jStorage(
            host=NEO4J_HOST,
            port=NEO4J_PORT,
            user=NEO4J_USER,
            password=NEO4J_PASSWORD,
        )
        storage.connect()

        # Initialize driller
        driller = RepositoryDriller(
            repository_path=repo_path,
            storage=storage,
            config=repository,
        )

        # Drill repository
        driller.drill_repository()
        driller.drill_commits(
            filters=repository.filters,
            pydriller_filters=repository.pydriller,
        )

        logger.info(f"Drilling complete for {repository.name}")

        return {
            "status": "complete",
            "job_id": job_id,
            "message": f"Successfully drilled {repository.name}",
        }

    except Exception as e:
        job_id = drill_config.job_id if drill_config else None
        logger.exception(f"Drilling failed: {e}")

        # Retry on transient errors with exponential backoff
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task (attempt {self.request.retries + 1}/{self.max_retries})")
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(exc=e, countdown=countdown)

        return {
            "status": "failed",
            "job_id": job_id,
            "message": f"Drilling failed: {str(e)}",
        }

    finally:
        # Stop log buffer and send remaining logs
        if log_buffer is not None:
            log_buffer.stop()
        if log_handler is not None:
            logger.removeHandler(log_handler)

        # Cleanup
        if storage is not None:
            storage.close()

        # Delete clone if configured
        if drill_config and drill_config.repository.delete_clone:
            try:
                repo_path = f"{REPO_CLONE_LOCATION}/{drill_config.repository.name}"
                remove_repository_clone(repo_path)
                logger.debug(f"Deleted cloned repository {repo_path}")
            except Exception as e:
                logger.warning(f"Failed to delete cloned repository: {e}")
