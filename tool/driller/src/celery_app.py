"""Celery application configuration"""
import os
from celery import Celery

# Get Redis settings from environment
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_BROKER_DB = os.environ.get("REDIS_BROKER_DB", "1")
REDIS_RESULT_DB = os.environ.get("REDIS_RESULT_DB", "0")
TASK_SOFT_TIME_LIMIT = int(os.environ.get("TASK_SOFT_TIME_LIMIT", "14400"))  # 4h
TASK_TIME_LIMIT = int(os.environ.get("TASK_TIME_LIMIT", "14700"))  # 4h + 5m
DEFAULT_VISIBILITY_TIMEOUT = TASK_TIME_LIMIT + 3600  # add safety buffer
VISIBILITY_TIMEOUT = int(
    os.environ.get("CELERY_VISIBILITY_TIMEOUT", str(DEFAULT_VISIBILITY_TIMEOUT))
)

# Initialize Celery app
app = Celery('driller')

# Configuration
app.conf.update(
    # Broker (Redis)
    broker_url=f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_BROKER_DB}',
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        'queue_order_strategy': 'priority',
        # Must be larger than max task runtime when using acks_late, otherwise
        # Redis may re-deliver in-flight tasks and create duplicate "started" jobs.
        'visibility_timeout': VISIBILITY_TIMEOUT,
        'priority_steps': [0, 3, 6, 9],
    },

    # Result backend (Redis)
    result_backend=f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULT_DB}',
    result_expires=86400,  # 24 hours

    # Task settings
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,

    # Performance
    worker_prefetch_multiplier=1,  # One task at a time (ensures even distribution)
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    worker_cancel_long_running_tasks_on_connection_loss=True,

    # Retry and timeout
    task_soft_time_limit=TASK_SOFT_TIME_LIMIT,
    task_time_limit=TASK_TIME_LIMIT,
    task_default_max_retries=3,
    task_default_retry_delay=60,  # 1 minute between retries
)

# Auto-discover tasks in src.tasks module
app.autodiscover_tasks(['src'])

# Import signal handlers to register them
from src import signals  # noqa: F401, E402
