"""Celery signal handlers for job status updates"""
import logging
import os
import socket
import requests
from celery import signals
from common.models.driller_config import SingleDrillConfig

logger = logging.getLogger(__name__)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")


def _get_worker_name(request=None) -> str:
    if request is not None and getattr(request, "hostname", None):
        return request.hostname
    return os.environ.get("HOSTNAME", socket.gethostname())


def _extract_drill_config_json(args=None, kwargs=None, request=None):
    if args and len(args) > 0 and isinstance(args[0], str):
        return args[0]

    if kwargs and isinstance(kwargs, dict):
        for key in ("drill_config_json", "config", "payload"):
            value = kwargs.get(key)
            if isinstance(value, str):
                return value

    if request is not None:
        request_args = getattr(request, "args", None)
        if request_args and len(request_args) > 0 and isinstance(request_args[0], str):
            return request_args[0]

        request_kwargs = getattr(request, "kwargs", None)
        if request_kwargs and isinstance(request_kwargs, dict):
            for key in ("drill_config_json", "config", "payload"):
                value = request_kwargs.get(key)
                if isinstance(value, str):
                    return value

    return None


def _is_drill_repository_task(sender=None, request=None) -> bool:
    sender_name = getattr(sender, "name", None)
    request_task = getattr(request, "task", None) if request is not None else None
    return sender_name == "src.tasks.drill_repository" or request_task == "src.tasks.drill_repository"


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
    request = getattr(task, "request", None) if task is not None else None
    if _is_drill_repository_task(sender=sender, request=request):
        try:
            drill_config_json = _extract_drill_config_json(args=args, kwargs=kwargs, request=request)
            if drill_config_json is None:
                return

            drill_config = SingleDrillConfig.model_validate_json(drill_config_json)
            worker_name = _get_worker_name(request)
            send_status_update(
                drill_config.job_id,
                "started",
                f"Drilling started for {drill_config.repository.name} on worker {worker_name}"
            )
        except Exception as e:
            logger.error(f"Failed to send started status: {e}")


@signals.task_success.connect
def task_success_handler(sender=None, result=None, task_id=None, **kwargs):
    """Send 'complete' status when task succeeds"""
    if result and isinstance(result, dict):
        job_id = result.get("job_id")
        if job_id:
            request = getattr(sender, "request", None) if sender is not None else None
            worker_name = _get_worker_name(request)
            send_status_update(
                job_id,
                result.get("status", "complete"),
                f"{result.get('message', 'Drilling complete')} (worker {worker_name})"
            )


@signals.task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, **extra):
    """Send 'failed' status when task fails permanently"""
    request = getattr(sender, "request", None) if sender is not None else None
    if _is_drill_repository_task(sender=sender, request=request):
        try:
            drill_config_json = _extract_drill_config_json(args=args, kwargs=kwargs, request=request)
            if drill_config_json is None:
                return

            drill_config = SingleDrillConfig.model_validate_json(drill_config_json)
            worker_name = _get_worker_name(request)
            send_status_update(
                drill_config.job_id,
                "failed",
                f"Drilling failed on worker {worker_name}: {str(exception)}"
            )
        except Exception as e:
            logger.error(f"Failed to send failure status: {e}")


@signals.task_retry.connect
def task_retry_handler(request=None, reason=None, einfo=None, sender=None, **kwargs):
    """Send failure+retrying status when task retries."""
    task_id = getattr(request, "id", None)
    logger.warning(f"Task {task_id} retrying: {reason}")

    if _is_drill_repository_task(sender=sender, request=request):
        try:
            drill_config_json = _extract_drill_config_json(request=request)
            if drill_config_json is None:
                return

            drill_config = SingleDrillConfig.model_validate_json(drill_config_json)
            worker_name = _get_worker_name(request)

            retries = getattr(request, "retries", 0)
            attempt = retries + 1
            retry_delay = getattr(reason, "when", None)
            retry_in = f" in {retry_delay}s" if retry_delay is not None else ""

            # Emit failed-attempt status first, then retrying status for queue visibility.
            send_status_update(
                drill_config.job_id,
                "failed",
                f"Attempt {attempt} failed on worker {worker_name}; will retry{retry_in}. Error: {reason}",
            )

            send_status_update(
                drill_config.job_id,
                "retrying",
                f"Retry queued for {drill_config.repository.name} on worker {worker_name}{retry_in}"
            )
        except Exception as e:
            logger.error(f"Failed to send retry status: {e}")
