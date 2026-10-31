from fastapi import status

from app.core.exceptions import (
    DCPException,
    ServiceUnavailableException,
)
from app.database.base import Base, TimestampMixin, UUIDMixin


def test_dcp_exception_properties():
    """Validates custom DCP exception attributes."""
    exc = DCPException(
        title="Bad Request",
        detail="Invalid payload",
        status_code=status.HTTP_400_BAD_REQUEST,
        code="INVALID_PAYLOAD",
    )
    assert exc.title == "Bad Request"
    assert exc.detail == "Invalid payload"
    assert exc.status_code == 400
    assert exc.code == "INVALID_PAYLOAD"


def test_service_unavailable_exception():
    """Validates ServiceUnavailableException default status and code."""
    exc = ServiceUnavailableException(detail="Database timeout", service="postgres")
    assert exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc.code == "POSTGRES_UNAVAILABLE"
    assert exc.detail == "Database timeout"


def test_model_mixins():
    """Asserts DeclarativeBase and mixins compile properly."""
    assert Base is not None
    assert UUIDMixin is not None
    assert TimestampMixin is not None
