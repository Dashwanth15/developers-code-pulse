import os
import sys
from collections.abc import AsyncGenerator

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Force testing configuration
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://dcp_user:dcp_password@localhost:5432/dcp_test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"

from app.core.config import get_settings
from app.main import create_application


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provides an asynchronous HTTP test client for the FastAPI app."""
    app = create_application()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
