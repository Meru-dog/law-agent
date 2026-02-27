"""Tests for pydantic settings configuration."""

import os
from unittest.mock import patch

import pytest

from app.config import Settings


def test_settings_default_values() -> None:
    """Settings should have sensible defaults without any env vars."""
    # Clear cache and create fresh settings
    settings = Settings()
    
    assert settings.app_name == "law-rag-app"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.log_level == "INFO"
    assert settings.log_format == "json"


def test_settings_env_override() -> None:
    """Settings should be overridable via environment variables."""
    env_vars = {
        "LAW_RAG_APP_NAME": "test-app",
        "LAW_RAG_ENVIRONMENT": "production",
        "LAW_RAG_DEBUG": "true",
        "LAW_RAG_LOG_LEVEL": "DEBUG",
        "LAW_RAG_LOG_FORMAT": "console",
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        settings = Settings()
        
        assert settings.app_name == "test-app"
        assert settings.environment == "production"
        assert settings.debug is True
        assert settings.log_level == "DEBUG"
        assert settings.log_format == "console"
