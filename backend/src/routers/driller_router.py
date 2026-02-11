from contextlib import asynccontextmanager
from enum import Enum
import json
from typing import List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
)

import logging

from fastapi.responses import JSONResponse
from sqlalchemy import case, func
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from src.database import get_session
from common.models.jobs import (
    Job,
    JobCreate,
    JobDetails,
    JobList,
    JobStatus,
    JobStatusOverview,
    JobStatusEnum,
)
from common.models.driller_config import DrillConfig, SingleDrillConfig

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
router = APIRouter()


@router.get("/jobs/")
def list_jobs(
    *,
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    statuses: List[str] = Query(default=[], description="Statuses of the job"),
):
    subquery = (
        select(JobStatus.job_id, func.max(JobStatus.timestamp).label("max_timestamp"))
        .group_by(JobStatus.job_id)
        .subquery()
    )

    latest_statuses = (
        select(JobStatus)
        .join(
            subquery,
            (JobStatus.job_id == subquery.c.job_id)
            & (JobStatus.timestamp == subquery.c.max_timestamp),
        )
        .subquery()
    )

    status_order = case(
        (latest_statuses.c.status == JobStatusEnum.STARTED, 1),
        (latest_statuses.c.status == JobStatusEnum.PENDING, 2),
        (latest_statuses.c.status == JobStatusEnum.FAILED, 3),
        (latest_statuses.c.status == JobStatusEnum.COMPLETE, 4),
        else_=5,
    )

    base_statement = select(Job).join(
        latest_statuses, Job.id == latest_statuses.c.job_id
    )

    if statuses:
        try:
            status_enum_list = [JobStatusEnum(status) for status in statuses]
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"One or more statuses are not valid: {statuses}",
            )
        base_statement = base_statement.where(
            latest_statuses.c.status.in_(status_enum_list)
        )

    # Query to get the total count of jobs matching the criteria
    count_statement = select(func.count()).select_from(base_statement.subquery())
    total = session.exec(count_statement).one()

    # Apply pagination
    statement = (
        base_statement.order_by(status_order)
        .offset(offset)
        .limit(limit)
        .options(selectinload(Job.job_statuses))
    )

    result = session.exec(statement).all()

    # logger.warning(result)
    items = []
    for item in result:
        job = item if item else item
        if job is None:
            return JSONResponse(status_code=404, content={"error": "Job not found"})
        items.append(
            JobList(id=job.id, name=job.name, data=job.data, statuses=job.job_statuses)
        )

    return {"items": items, "total": total}


@router.delete("/jobs/{job_id}")
def delete_job(*, session: Session = Depends(get_session), job_id: int):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    session.delete(job)
    session.commit()
    return Response(status_code=200)


@router.delete("/jobs/")
def delete_all_jobs(*, session: Session = Depends(get_session)):
    results = session.exec(select(Job))
    for job in results:
        session.delete(job)
    session.commit()
    return Response(status_code=200)


@router.get("/jobs/{job_id}", response_model=JobDetails)
def detail_job(*, session: Session = Depends(get_session), job_id: int):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/", response_model=list[JobList])
async def create_jobs(
    *,
    session: Session = Depends(get_session),
    drill_config: DrillConfig,
    background_tasks: BackgroundTasks,
    request: Request,
):
    job_list = []
    for repository in drill_config.repositories:
        single_job = SingleDrillConfig(
            defaults=drill_config.defaults, repository=repository
        )

        db_job = Job.model_validate(
            JobCreate(name=repository.name, data=single_job.model_dump())
        )

        session.add(db_job)
        session.commit()
        session.refresh(db_job)

        single_job.job_id = db_job.id

        db_job_status = JobStatus(job_id=db_job.id)
        session.add(db_job_status)
        session.commit()
        session.refresh(db_job_status)

        # Enqueue drill job with Celery
        task_id = request.state.driller_client.enqueue_drill_job(
            single_job.model_dump_json()
        )

        job_list.append(
            JobList(
                id=db_job.id,
                name=db_job.name,
                data=db_job.data,
                statuses=[
                    JobStatusOverview(
                        status=db_job_status.status, timestamp=db_job_status.timestamp
                    )
                ],
            )
        )

    # result = await driller_client.call(body)
    return job_list
    # return Response(jobs_list, status_code=201)
