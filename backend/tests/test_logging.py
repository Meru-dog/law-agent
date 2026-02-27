"""Tests for structured logging configuration."""

import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest
import structlog

from app.config import Settings
from app.logging import (
    SENSITIVE_FIELDS,
    _filter_sensitive_data,
    configure_logging,
    get_logger,
)


def test_sensitive_fields_are_redacted() -> None:
    """Sensitive fields should be redacted from log events."""
    event_dict = {
        "event": "test_event",
        "doc_id": "doc123",
        "document_text": "This is sensitive contract text",
        "password": "secret123",
        "content": "More sensitive data",
    }
    
    result = _filter_sensitive_data(None, "info", event_dict.copy())
    
    assert result["doc_id"] == "doc123"  # Safe field preserved
    assert result["document_text"] == "[REDACTED]"
    assert result["password"] == "[REDACTED]"
    assert result["content"] == "[REDACTED]"


def test_safe_fields_are_preserved() -> None:
    """Safe identifier fields should be preserved and stringified."""
    event_dict = {
        "event": "test_event",
        "doc_id": 123,
        "matter_id": "M-2024-001",
        "user_id": "user@example.com",
        "anchor": "section_2.1",
        "page": 5,
    }
    
    # Import the function to test
    from app.logging import _add_safe_context
    
    result = _add_safe_context(None, "info", event_dict.copy())
    
    assert result["doc_id"] == "123"  # Converted to string
    assert result["matter_id"] == "M-2024-001"
    assert result["user_id"] == "user@example.com"
    assert result["anchor"] == "section_2.1"
    assert result["page"] == "5"


def test_configure_logging_json_format() -> None:
    """Logging should be configurable for JSON output."""
    settings = Settings(log_format="json", log_level="INFO")
    
    # Should not raise
    configure_logging(settings)
    
    logger = get_logger("test")
    assert logger is not None


def test_configure_logging_console_format() -> None:
    """Logging should be configurable for console output."""
    settings = Settings(log_format="console", log_level="DEBUG")
    
    # Should not raise
    configure_logging(settings)
    
    logger = get_logger("test")
    assert logger is not None
