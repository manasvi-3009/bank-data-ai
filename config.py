"""
Configuration module for Bank Data AI.

Loads and validates environment settings for database connections (MySQL or bundled SQLite)
and LLM services without exposing secrets or plaintext credentials.
"""

from __future__ import annotations
import os
from pathlib import Path
from urllib.parse import urlparse

# Resolve project root and bundled SQLite path
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "data" / "bank_data.db"

try:
    from dotenv import load_dotenv
    # Explicitly locate .env in project root if available
    _env_path = PROJECT_ROOT / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path, override=False)
    else:
        load_dotenv(override=False)
except ImportError:
    pass


class AppConfig:
    """Application configuration container with safe credential handling and SQLite fallback."""

    @property
    def database_url(self) -> str:
        """
        Retrieve the configured DATABASE_URL.
        If DATABASE_URL is not set or empty, falls back to bundled SQLite database
        at data/bank_data.db relative to the project root.
        """
        env_url = os.getenv("DATABASE_URL", "").strip()
        if env_url:
            return env_url
        if DEFAULT_SQLITE_PATH.exists():
            return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
        return ""

    @property
    def is_sqlite(self) -> bool:
        """Check if active database backend is SQLite."""
        return self.database_url.startswith("sqlite")

    @property
    def database_backend(self) -> str:
        """Returns the active database backend type ('SQLite' or 'MySQL')."""
        if self.is_sqlite:
            return "SQLite"
        if self.database_url.startswith("mysql"):
            return "MySQL"
        return "Unknown"

    @property
    def llm_api_key(self) -> str:
        """Retrieve the LLM API key."""
        return os.getenv("LLM_API_KEY", "").strip()

    @property
    def llm_model(self) -> str:
        """Retrieve the LLM model identifier."""
        return os.getenv("LLM_MODEL", "gpt-4o-mini").strip()

    @property
    def llm_base_url(self) -> str:
        """Retrieve the LLM Base URL (defaults to standard OpenAI endpoint)."""
        return os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")

    @property
    def is_database_configured(self) -> bool:
        """Check if a valid database URL is supplied or bundled SQLite exists."""
        url = self.database_url
        return bool(
            url
            and (
                url.startswith("mysql://")
                or url.startswith("mysql+pymysql://")
                or url.startswith("sqlite://")
            )
        )

    @property
    def is_llm_configured(self) -> bool:
        """Check if an LLM API key is provided."""
        return bool(self.llm_api_key)

    @property
    def database_name(self) -> str:
        """Extracts the database name from the configured DATABASE_URL or defaults to banking_risk_analytics."""
        raw_url = self.database_url
        if not raw_url:
            return "banking_risk_analytics"
        if self.is_sqlite:
            return "bank_data.db"
        try:
            parsed = urlparse(raw_url)
            path = parsed.path.lstrip("/")
            return path if path else "banking_risk_analytics"
        except Exception:
            return "banking_risk_analytics"

    def get_masked_db_url(self) -> str:
        """
        Return a safe representation of the database URL with the password masked.
        Never exposes plaintext credentials in logs or the UI.
        """
        raw_url = self.database_url
        if not raw_url:
            return "Not Configured"

        if self.is_sqlite:
            return "data/bank_data.db (SQLite Snapshot)"

        try:
            parsed = urlparse(raw_url)
            netloc = parsed.netloc
            if "@" in netloc:
                auth_part, host_part = netloc.rsplit("@", 1)
                username = auth_part.split(":")[0] if ":" in auth_part else auth_part
                masked_netloc = f"{username}:******@{host_part}"
            else:
                masked_netloc = netloc

            return f"{parsed.scheme}://{masked_netloc}{parsed.path}"
        except Exception:
            return "mysql://******"

    def __repr__(self) -> str:
        return (
            f"<AppConfig database_configured={self.is_database_configured} "
            f"backend='{self.database_backend}' "
            f"database_name='{self.database_name}' "
            f"llm_configured={self.is_llm_configured} model='{self.llm_model}'>"
        )


# Global singleton instance
config = AppConfig()
