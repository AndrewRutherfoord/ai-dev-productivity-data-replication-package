"""Celery client for enqueueing drill jobs"""
import logging
import os
from celery import Celery

logger = logging.getLogger(__name__)

# Get settings from environment
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_BROKER_DB = os.environ.get("REDIS_BROKER_DB", "1")


class DrillerTaskClient:
    """Client for enqueueing drill tasks via Celery"""

    def __init__(self):
        """Initialize Celery app instance"""
        self.app = Celery('driller')
        self.app.conf.update(
            broker_url=f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_BROKER_DB}',
            result_backend='redis://redis:6379/0',
            task_serializer='json',
            result_serializer='json',
            accept_content=['json'],
            timezone='UTC',
            enable_utc=True,
            broker_transport_options={
                'queue_order_strategy': 'priority',
                'visibility_timeout': 7200,  # 2 hours (exceeds task time limit)
                'priority_steps': [0, 3, 6, 9],
            },
        )

    async def startup(self):
        """Verify Celery connection on startup"""
        try:
            # Celery connects lazily, so just verify we can get the connection
            with self.app.connection_or_acquire(block=False) as conn:
                conn.connect()
            logger.info("Celery client connected successfully")
        except Exception as e:
            logger.warning(f"Could not verify Celery connection: {e}")

    async def shutdown(self):
        """Close Celery connection"""
        try:
            with self.app.connection_or_acquire(block=False) as conn:
                conn.close()
        except Exception as e:
            logger.warning(f"Error closing Celery connection: {e}")

    def enqueue_drill_job(self, drill_config_json: str) -> str:
        """
        Enqueue a drill job.

        Args:
            drill_config_json: JSON string of SingleDrillConfig

        Returns:
            str: Task ID for tracking
        """
        try:
            # Send task to driller_queue
            result = self.app.send_task(
                'src.tasks.drill_repository',
                args=(drill_config_json,),
                queue='driller_queue',
                priority=5,  # Normal priority (0-10 range)
            )
            logger.info(f"Enqueued drill task: {result.id}")
            return result.id
        except Exception as e:
            logger.error(f"Failed to enqueue drill job: {e}")
            raise
