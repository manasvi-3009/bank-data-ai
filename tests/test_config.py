"""
Unit tests for AppConfig and credential masking.
"""

import os
import unittest
from config import AppConfig


class TestAppConfig(unittest.TestCase):
    def test_config_masks_password(self):
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


if __name__ == "__main__":
    unittest.main()
