from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class DCPException(Exception):
    """Base exception for Developers Code Pulse application errors."""

    def __init__(
        self,
        title: str,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "INTERNAL_SERVER_ERROR",
        errors: list[dict[str, Any]] | None = None,
    ):
        self.title = title
        self.detail = detail
        self.status_code = status_code
        self.code = code
        self.errors = errors or []
        super().__init__(detail)


class ServiceUnavailableException(DCPException):
    """Raised when a required backing service (PostgreSQL, Redis) is unreachable."""

    def __init__(self, detail: str, service: str):
        super().__init__(
            title="Service Unavailable",
            detail=detail,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=f"{service.upper()}_UNAVAILABLE",
        )


async def dcp_exception_handler(request: Request, exc: DCPException) -> JSONResponse:
    """Formats DCP exceptions into RFC 7807 compliant JSON problem details."""
    trace_id = getattr(request.state, "trace_id", "none")
    payload = {
        "type": f"https://developerscodepulse.com/errors/{exc.code}",
        "title": exc.title,
        "status": exc.status_code,
        "detail": exc.detail,
        "instance": str(request.url.path),
        "code": exc.code,
        "errors": exc.errors,
        "timestamp": datetime.now(UTC).isoformat(),
        "trace_id": trace_id,
    }
    logger.warning(
        "application_exception", code=exc.code, status=exc.status_code, detail=exc.detail
    )
    return JSONResponse(status_code=exc.status_code, content=payload)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches unhandled exceptions and returns a sanitized 500 error."""
    trace_id = getattr(request.state, "trace_id", "none")
    logger.exception("unhandled_server_error", path=str(request.url.path), error=str(exc))
    payload = {
        "type": "https://developerscodepulse.com/errors/INTERNAL_SERVER_ERROR",
        "title": "Internal Server Error",
        "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "detail": "An unexpected server error occurred. Please contact system support.",
        "instance": str(request.url.path),
        "code": "INTERNAL_SERVER_ERROR",
        "timestamp": datetime.now(UTC).isoformat(),
        "trace_id": trace_id,
    }
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)
