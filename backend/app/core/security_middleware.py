"""Application Security Middleware: Security Headers, Request Size Limits, and Rate Limiting."""

import time
from collections.abc import Callable

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)

# Maximum allowed request body size (15 MB) to prevent denial-of-service
MAX_REQUEST_BODY_BYTES = 15 * 1024 * 1024

# In-memory sliding window rate limiter (client_ip -> list of timestamps)
_RATE_LIMIT_BUCKET: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_MAX_REQUESTS_PER_WINDOW = 300


async def security_headers_middleware(request: Request, call_next: Callable) -> Response:
    """Attaches standard enterprise security headers to every outgoing HTTP response."""
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )

    # Apply HSTS for production deployments
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


async def request_size_limit_middleware(request: Request, call_next: Callable) -> Response:
    """Enforces request payload size limits to guard against buffer exhaustion attacks."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            length = int(content_length)
            if length > MAX_REQUEST_BODY_BYTES:
                logger.warning(
                    "request_size_exceeded",
                    size=length,
                    max_size=MAX_REQUEST_BODY_BYTES,
                    path=str(request.url.path),
                )
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "type": "https://developerscodepulse.com/errors/PAYLOAD_TOO_LARGE",
                        "title": "Payload Too Large",
                        "status": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        "detail": f"Request body exceeds the maximum permitted size of {MAX_REQUEST_BODY_BYTES // (1024 * 1024)}MB.",
                        "code": "PAYLOAD_TOO_LARGE",
                    },
                )
        except ValueError:
            pass

    return await call_next(request)


async def rate_limiting_middleware(request: Request, call_next: Callable) -> Response:
    """
    Applies sliding window rate-limiting per client IP address.
    Excludes liveness/readiness/metrics probes from rate limits.
    """
    path = request.url.path
    if path in ("/api/v1/health", "/api/v1/ready", "/metrics"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    # Clean expired records for client
    timestamps = _RATE_LIMIT_BUCKET.get(client_ip, [])
    active_timestamps = [t for t in timestamps if t > window_start]

    if len(active_timestamps) >= DEFAULT_MAX_REQUESTS_PER_WINDOW:
        logger.warning(
            "rate_limit_exceeded",
            client_ip=client_ip,
            request_count=len(active_timestamps),
            path=path,
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={
                "Retry-After": str(RATE_LIMIT_WINDOW_SECONDS),
                "X-RateLimit-Limit": str(DEFAULT_MAX_REQUESTS_PER_WINDOW),
                "X-RateLimit-Remaining": "0",
            },
            content={
                "type": "https://developerscodepulse.com/errors/RATE_LIMIT_EXCEEDED",
                "title": "Too Many Requests",
                "status": status.HTTP_429_TOO_MANY_REQUESTS,
                "detail": f"Rate limit exceeded: maximum {DEFAULT_MAX_REQUESTS_PER_WINDOW} requests per minute.",
                "code": "RATE_LIMIT_EXCEEDED",
            },
        )

    active_timestamps.append(now)
    _RATE_LIMIT_BUCKET[client_ip] = active_timestamps

    response = await call_next(request)
    remaining = max(0, DEFAULT_MAX_REQUESTS_PER_WINDOW - len(active_timestamps))
    response.headers["X-RateLimit-Limit"] = str(DEFAULT_MAX_REQUESTS_PER_WINDOW)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response
