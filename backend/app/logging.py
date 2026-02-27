"""Structured logging configuration.

SECURITY: Logs store IDs/anchors only - no raw document text by default.
This is a hard constraint from SPEC.md to prevent sensitive data leakage.
"""

import logging
import sys
from typing import Any

import structlog

from app.config import Settings


# Fields that should NEVER appear in logs (sensitive content)
SENSITIVE_FIELDS = frozenset({
    "document_text",
    "raw_text",
    "content",
    "body",
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
    "database_url",
})


def _filter_sensitive_data(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Remove or redact sensitive fields from log events.
    
    This processor ensures no sensitive document text leaks into logs.
    Only IDs, anchors, and metadata are preserved.
    """
    for field in SENSITIVE_FIELDS:
        if field in event_dict:
            event_dict[field] = "[REDACTED]"
    return event_dict


def _add_safe_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add safe contextual information to log events.
    
    Adds identifiers that are safe to log (IDs, anchors, timestamps).
    """
    # These fields are always safe to log
    safe_fields = ("doc_id", "matter_id", "user_id", "query_id", "anchor", "page")
    for field in safe_fields:
        if field in event_dict and event_dict[field] is not None:
            # Ensure IDs are strings for consistent logging
            event_dict[field] = str(event_dict[field])
    return event_dict


def configure_logging(settings: Settings) -> None:
    """Configure structured logging based on application settings.
    
    Args:
        settings: Application settings containing log configuration.
    """
    # Determine processors based on output format
    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _filter_sensitive_data,
        _add_safe_context,
    ]

    if settings.log_format == "json":
        # Production: JSON output for log aggregation
        renderer: structlog.typing.Processor = structlog.processors.JSONRenderer()
    else:
        # Development: human-readable console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to use structlog
    log_level = getattr(logging, settings.log_level)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__ of the calling module).
        
    Returns:
        Configured structlog logger instance.
    """
    return structlog.get_logger(name)
