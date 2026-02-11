"""Celery signal handlers for job status updates"""
import logging
import os
import requests
from celery import signals
from common.models.driller_config import SingleDrillConfig

logger = logging.getLogger(__name__)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")


def send_status_update(job_id: int, status: str, message: str):
    """Send status update to backend API"""
    if job_id is None:
        logger.warning("Cannot send status update: job_id is None")
        return

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/job-status",
            json={
                "job_id": job_id,
                "status": status,
                "message": message,
            },
            timeout=5.0
        )
        response.raise_for_status()
        logger.info(f"Sent {status} status for job {job_id}")
    except Exception as e:
        logger.error(f"Failed to send status update for job {job_id}: {e}")


@signals.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """Send 'started' status when task begins"""
    if task.name == 'src.tasks.drill_repository' and args:
        try:
            drill_config_json = args[0]
            drill_config = SingleDrillConfig.model_validate_json(drill_config_json)
            send_status_update(
                drill_config.job_id,
                "started",
                f"Drilling started for {drill_config.repository.name}"
            )
        except Exception as e:
            logger.error(f"Failed to send started status: {e}")


@signals.task_success.connect
def task_success_handler(sender=None, result=None, task_id=None, **kwargs):
    """Send 'complete' status when task succeeds"""
    if result and isinstance(result, dict):
        job_id = result.get("job_id")
        if job_id:
            send_status_update(
                job_id,
                result.get("status", "complete"),
                result.get("message", "Drilling complete")
            )


@signals.task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, **kwargs):
    """Send 'failed' status when task fails permanently"""
    if sender.name == 'src.tasks.drill_repository' and args:
        try:
            drill_config_json = args[0]
            drill_config = SingleDrillConfig.model_validate_json(drill_config_json)
            send_status_update(
                drill_config.job_id,
                "failed",
                f"Drilling failed: {str(exception)}"
            )
        except Exception as e:
            logger.error(f"Failed to send failure status: {e}")


@signals.task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, **kwargs):
    """Log retry attempts"""
    logger.warning(f"Task {task_id} retrying: {reason}")
