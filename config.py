"""
Configuration module for Bank Data AI.

Loads and validates environment settings for the MySQL database connection
and LLM services without exposing secrets.
"""

import os
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class AppConfig:
    """Application configuration container."""

    @property
    def database_url(self) -> str:
        """Retrieve the configured DATABASE_URL."""
        return os.getenv("DATABASE_URL", "").strip()

    @property
    def llm_api_key(self) -> str:
        """Retrieve the LLM API key."""
        return os.getenv("LLM_API_KEY", "").strip()

    @property
    def llm_model(self) -> str:
        """Retrieve the LLM model identifier."""
        return os.getenv("LLM_MODEL", "gpt-4o-mini").strip()

    @property
    def is_database_configured(self) -> bool:
        """Check if a valid database URL is supplied."""
        url = self.database_url
        return bool(url and (url.startswith("mysql://") or url.startswith("mysql+pymysql://") or url.startswith("sqlite://")))

    @property
    def is_llm_configured(self) -> bool:
        """Check if an LLM API key is provided."""
        return bool(self.llm_api_key)

    def get_masked_db_url(self) -> str:
        """
        Return a safe representation of the database URL with the password masked.
        Never exposes plaintext credentials in logs or the UI.
        """
        raw_url = self.database_url
        if not raw_url:
            return "Not Configured"

        try:
            parsed = urlparse(raw_url)
            # Mask user:password if present
            netloc = parsed.netloc
            if "@" in netloc:
                auth_part, host_part = netloc.split("@", 1)
                username = auth_part.split(":")[0] if ":" in auth_part else auth_part
                masked_netloc = f"{username}:******@{host_part}"
            else:
                masked_netloc = netloc

            return f"{parsed.scheme}://{masked_netloc}{parsed.path}"
        except Exception:
            return "mysql://******"

    def __repr__(self) -> str:
        return f"<AppConfig database_configured={self.is_database_configured} llm_configured={self.is_llm_configured} model={self.llm_model}>"


# Global singleton instance
config = AppConfig()
