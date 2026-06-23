import pytest
import logging

logging.basicConfig(level=logging.INFO)

@pytest.fixture(scope="session")
def setup_test_env():
    logging.info("Setting up test environment...")
    yield "env_ready"
    logging.info("Tearing down test environment...")

