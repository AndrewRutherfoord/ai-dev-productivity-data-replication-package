"""Add logs field to JobStatus

Revision ID: add_logs_to_jobstatus
Revises: c60111c8977d
Create Date: 2026-02-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'add_logs_to_jobstatus'
down_revision: Union[str, None] = 'c60111c8977d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobstatus', sa.Column('logs', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    op.drop_column('jobstatus', 'logs')
