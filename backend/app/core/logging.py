"""Structured JSON logging configuration for Developers Code Pulse (DCP) with sensitive data masking."""

import logging
import sys
from typing import Any

import structlog

from app.core.config import get_settings

settings = get_settings()

SENSITIVE_FIELD_NAMES = {
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
    "gemini_api_key",
    "github_token",
    "private_key",
    "client_secret",
    "credentials",
}


def mask_sensitive_data_processor(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Recursively redacts sensitive values such as tokens, passwords, and API keys."""

    def _sanitize(item: Any) -> Any:
        if isinstance(item, dict):
            sanitized: dict[str, Any] = {}
            for k, v in item.items():
                if any(sens in k.lower() for sens in SENSITIVE_FIELD_NAMES):
                    sanitized[k] = "***REDACTED***"
                else:
                    sanitized[k] = _sanitize(v)
            return sanitized
        elif isinstance(item, list):
            return [_sanitize(x) for x in item]
        return item

    return _sanitize(event_dict)


def add_service_name_processor(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Ensures service_name is present in all structured log lines for distributed correlation."""
    if "service" not in event_dict:
        event_dict["service"] = "dcp-backend"
    return event_dict


def setup_logging(service_name: str = "dcp-backend") -> None:
    """Configures structured logging for the application using structlog."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    structlog.contextvars.bind_contextvars(service=service_name)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        add_service_name_processor,
        mask_sensitive_data_processor,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.LOG_FORMAT.lower() == "json":
        formatter_processor = structlog.processors.JSONRenderer()
    else:
        formatter_processor = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                formatter_processor,
            ],
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery.beat").setLevel(logging.INFO)
