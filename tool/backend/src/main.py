from contextlib import asynccontextmanager
import os

from fastapi import Depends, FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware

import logging


from src.celery_client import DrillerTaskClient
from src.routers import driller_router, files, job_statuses

logger = logging.getLogger(__name__)

driller_client: DrillerTaskClient | None = None

# ---------- Celery ----------


async def setup_celery_client():
    global driller_client
    driller_client = DrillerTaskClient()
    await driller_client.startup()
    logger.info("Celery client initialized")


async def teardown_celery_client():
    global driller_client
    if driller_client is not None:
        await driller_client.shutdown()
    driller_client = None
    logger.info("Celery client shutdown")


async def get_client(request: Request = None) -> DrillerTaskClient:
    """Gets the Celery Driller Client
    To be used with dependency injection for endpoint to access the Celery client.
    """
    global driller_client

    if driller_client is None:
        raise ConnectionError("Could not initialize Celery client.")

    if request is not None:
        # Sets the drill client state in request. Can be accessed in endpoint with request injection and `request.state.driller_client`
        request.state.driller_client = driller_client
        return driller_client
    return None


# ---------- FastAPI ----------


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup the Celery client on startup
    await setup_celery_client()

    yield

    # Shutdown Celery client on teardown
    await teardown_celery_client()

# Instantiate app with global dependency injection and the lifespan
# `get_client` adds the Celery client instance to the request object
app = FastAPI(dependencies=[Depends(get_client)], lifespan=lifespan)

prefix_router = APIRouter(prefix="/api")

# Attach the routers to the FastAPI App
prefix_router.include_router(driller_router.router)
prefix_router.include_router(files.router)
prefix_router.include_router(job_statuses.router)

# Allow all origins
origins = [
    "*",
]

# Very open CORS. Stricter not necessary since app won't be deployed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@prefix_router.get("/healthcheck")
def get_healthcheck():
    """Endpoint to use to check backend life."""
    return "OK"


app.include_router(prefix_router)