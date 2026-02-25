from datetime import datetime
from enum import Enum
import json
import logging
from typing import Optional, Type
import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy_utils import ChoiceType

logger = logging.getLogger(__name__)


class JobBase(SQLModel):
    name: str
    data: dict = Field(sa_column=sa.Column(sa.JSON), default={})


class Job(JobBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    job_statuses: list["JobStatus"] = Relationship(back_populates="job")


class JobList(JobBase):
    id: int
    statuses: list["JobStatusOverview"]


class JobDetails(JobList):
    job_statuses: list["JobStatusDetails"] = []


class JobCreate(JobBase):
    pass


class JobStatusEnum(str, Enum):
    STARTED = "started"
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"
    RETRYING = "retrying"

    @classmethod
    def from_string(cls, status_str):
        try:
            return cls(status_str)
        except ValueError:
            raise ValueError(f"'{status_str}' is not a valid {cls.__name__}")


class JobStatusBase(SQLModel):
    # status: Enum[JobStatusEnum]  = Field(sa_column=Column(Enum(JobStatusEnum)))
    status: JobStatusEnum = Field(
        sa_column=sa.Column(ChoiceType(JobStatusEnum), nullable=False),
        default=JobStatusEnum.PENDING,
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    job_id: int | None = Field(default=None, foreign_key="job.id")
    message : str = Field(default="")
    logs: list[dict] = Field(sa_column=sa.Column(sa.JSON), default_factory=list)


class JobStatus(JobStatusBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job: Job | None = Relationship(back_populates="job_statuses")


class JobStatusOverview(JobStatusBase):
    pass


class JobStatusDetails(JobStatusBase):
    job: JobBase | None
    pass
