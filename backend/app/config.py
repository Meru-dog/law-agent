"""Application configuration using Pydantic Settings.

All configuration is loaded from environment variables with sensible defaults.
Sensitive values (API keys, DB passwords) should NEVER be logged.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    Attributes:
        app_name: Display name for the application.
        debug: Enable debug mode (verbose logging, detailed errors).
        log_level: Logging verbosity level.
        log_format: Output format for logs (json for production, console for dev).
        environment: Deployment environment identifier.
    """

    model_config = SettingsConfigDict(
        env_prefix="LAW_RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "law-rag-app"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Logging - NEVER log sensitive document text
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # Database
    database_url: str = "sqlite:///./law_rag.db"

    # File storage
    storage_path: str = "./storage/documents"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Authorization – maps user_id → list of authorized matter_ids.
    # Set via LAW_RAG_USER_MATTERS env var as JSON, e.g.:
    #   LAW_RAG_USER_MATTERS='{"alice":["matter-1","matter-2"]}'
    # Empty by default (deny-by-default).
    user_matters: dict[str, list[str]] = {}

    # LLM Configuration
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro"
    max_context_chunks: int = 10

    # Neo4j Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings singleton.
    
    Returns:
        Settings instance loaded from environment.
    """
    return Settings()
