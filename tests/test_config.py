"""
Unit tests for AppConfig, environment variables, and credential masking.
"""

from __future__ import annotations
import os
import unittest
from config import AppConfig


class TestAppConfig(unittest.TestCase):
    def test_config_masks_password(self):
        """Verifies that plaintext database passwords are never exposed in get_masked_db_url."""
        original = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATABASE_URL"] = (
                "mysql+pymysql://analytics_user:SecretPassword123!@127.0.0.1:3306/banking_risk_analytics"
            )
            cfg = AppConfig()
            masked = cfg.get_masked_db_url()

            self.assertNotIn("SecretPassword123!", masked)
            self.assertIn("analytics_user:******@127.0.0.1:3306/banking_risk_analytics", masked)
        finally:
            if original is not None:
                os.environ["DATABASE_URL"] = original
            else:
                os.environ.pop("DATABASE_URL", None)

    def test_config_unconfigured(self):
        """Verifies safe fallback when DATABASE_URL is not set."""
        original = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATABASE_URL"] = ""
            cfg = AppConfig()
            self.assertFalse(cfg.is_database_configured)
            self.assertEqual(cfg.get_masked_db_url(), "Not Configured")
        finally:
            if original is not None:
                os.environ["DATABASE_URL"] = original
            else:
                os.environ.pop("DATABASE_URL", None)

    def test_database_name_extraction(self):
        """Verifies that database_name correctly parses the DB name from DATABASE_URL."""
        original = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATABASE_URL"] = "mysql+pymysql://root:pass@localhost:3306/banking_risk_analytics"
            cfg = AppConfig()
            self.assertEqual(cfg.database_name, "banking_risk_analytics")
        finally:
            if original is not None:
                os.environ["DATABASE_URL"] = original
            else:
                os.environ.pop("DATABASE_URL", None)

    def test_llm_configuration_check(self):
        """Verifies is_llm_configured reflects LLM_API_KEY presence."""
        original = os.environ.get("LLM_API_KEY")
        try:
            os.environ["LLM_API_KEY"] = "sk-test-key-12345"
            cfg = AppConfig()
            self.assertTrue(cfg.is_llm_configured)

            os.environ["LLM_API_KEY"] = ""
            cfg2 = AppConfig()
            self.assertFalse(cfg2.is_llm_configured)
        finally:
            if original is not None:
                os.environ["LLM_API_KEY"] = original
            else:
                os.environ.pop("LLM_API_KEY", None)


if __name__ == "__main__":
    unittest.main()
