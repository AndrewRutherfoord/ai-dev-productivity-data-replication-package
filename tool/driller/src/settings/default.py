import logging
import os

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# DATE_FORMAT = "%d %B, %Y %H:%M"
DATE_FORMAT = "%Y-%m-%d"

NEO4J_LOG_LEVEL = logging.getLevelName(os.environ.get("NEO4J_LOG_LEVEL", LOG_LEVEL))
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", None)
NEO4J_HOST = os.environ.get("NEO4J_HOST", "neo4j")
NEO4J_PORT = os.environ.get("NEO4J_PORT")

NEO4J_DEFAULT_BATCH_SIZE = None
try:
    NEO4J_DEFAULT_BATCH_SIZE = int(os.environ.get("NEO4J_DEFAULT_BATCH_SIZE", 50))
except ValueError:
    raise ValueError("NEO4J_DEFAULT_BATCH_SIZE must be an integer.")

LOG_LEVEL = logging.getLevelName(LOG_LEVEL)

REPO_CLONE_LOCATION = os.environ.get("REPO_CLONE_LOCATION", "/tmp/repos")

# To replace the storage class, driller class or worker class that is used, replace the following
# strings with the location of the replacement class. This allows you to add custom functionality
DEFAULT_CONFIGS = {
    "REPOSITORY_STORAGE_CLASS": "src.drillers.neo4j_pydriller_repository_storage.RepositoryNeo4jStorage",
    "REPOSITORY_DRILLER_CLASS": "src.drillers.driller.RepositoryDriller",
    "WORKER_CLASS": "src.workers.queue_driller_worker.QueueRepositoryNeo4jDrillerWorker",
}

CONFIGS = {**DEFAULT_CONFIGS}
