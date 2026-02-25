import pytest
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pydriller_logger = logging.getLogger('pydriller')
pydriller_logger.setLevel(logging.WARNING)

@pytest.fixture(autouse=True)
def log_execution_time(request):
    start_time = time.time()

    # This function will be executed when the test is completed
    def fin():
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Test {request.node.name} took {duration:.4f} seconds")
    request.addfinalizer(fin)
