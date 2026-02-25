#!/usr/bin/env python3

import logging
import sys

from src.settings.default import LOG_FORMAT, LOG_LEVEL, NEO4J_LOG_LEVEL
from src.celery_app import app
from src import signals  # Import to register signal handlers

logger = logging.getLogger(__name__)
logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
std_out_handler = logging.StreamHandler(sys.stdout)

neo4j_logger = logging.getLogger("neo4j")
neo4j_logger.setLevel(NEO4J_LOG_LEVEL)
neo4j_logger.addHandler(std_out_handler)

logger.info("Driller Celery worker starting...")


def exec():
    """Entry point for driller worker"""
    app.worker_main(['worker', '--loglevel=info', '-Q', 'driller_queue'])


if __name__ == "__main__":
    exec()
