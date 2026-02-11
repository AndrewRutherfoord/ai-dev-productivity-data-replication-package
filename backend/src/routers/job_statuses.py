import logging
import time

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel
from sqlmodel import Session

from common.models.jobs import (
    JobStatus,
    JobStatusDetails,
    Job,
)

from src.database import get_session
from src.ws_connection_manager import socket_connections

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()


@router.websocket("/jobs/statuses/")
async def websocket_endpoint(
    *,
    websocket: WebSocket,
):
    await socket_connections.connect(websocket)
    logger.warning("WS COnnect")
    try:
        while True:
            logger.info(socket_connections)
            text = await websocket.receive_text()  # not really necessary
            logger.info(f"Received text: {text}")

    except WebSocketDisconnect:
        socket_connections.disconnect(websocket)


@router.post("/jobs/status/")
def create_job_status(
    *, session: Session = Depends(get_session), job_status: JobStatus
):
    """Creates a Job Status in the database. Mostly for testing as the
    job statuses should be created based on reponses from the workers"""
    session.add(job_status)
    session.commit()
    session.refresh(job_status)
    return job_status


@router.get("/jobs/status/{job_status_id}", response_model=JobStatusDetails)
def detail_job_status(*, session: Session = Depends(get_session), job_status_id: int):
    """Get a particular job status based on the id"""
    job_status = session.get(JobStatus, job_status_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_status


class StatusUpdate(BaseModel):
    """Status update from worker"""
    job_id: int
    status: str  # "started", "complete", "failed"
    message: str


@router.post("/api/job-status")
async def receive_job_status(
    status_update: StatusUpdate,
    session: Session = Depends(get_session)
):
    """Receive status update from worker and notify WebSocket clients"""

    logger.info(f"Received status update: job_id={status_update.job_id}, status={status_update.status}")

    # Get job to verify it exists
    job = session.get(Job, status_update.job_id)
    if not job:
        logger.warning(f"Job {status_update.job_id} not found")
        raise HTTPException(status_code=404, detail=f"Job {status_update.job_id} not found")

    # Create and save status record
    db_status = JobStatus(
        job_id=status_update.job_id,
        status=status_update.status,
        message=status_update.message
    )
    session.add(db_status)
    session.commit()
    session.refresh(db_status)

    # Send WebSocket notification to all connected clients
    await socket_connections.send_message({
        "job_status": db_status.model_dump(),
        "job": job.model_dump() if job else None
    })

    logger.info(f"Status update saved and broadcast for job {status_update.job_id}")
    return {"ok": True}
