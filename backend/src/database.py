import logging
import os
from sqlmodel import Session, create_engine

logger = logging.getLogger(__name__)

# Configuring database connection.
# Database migrations are handled by Alembic. If any changed are made to the database models
# then consult backend README about how to migrate.

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, echo=True)


def get_session():
    """Dependency that is injected into endpoints for DB access"""
    with Session(engine) as session:
        yield session
