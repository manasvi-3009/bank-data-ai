"""
Unit tests for LLM service, providers, prompt generation, and mock fallbacks.
"""

from __future__ import annotations
import os
import unittest
from unittest.mock import MagicMock, patch

from llm_service import (
    LLMService,
    MockLLMProvider,
    OpenAICompatibleProvider,
    GeminiProvider,
    AnthropicProvider,
    LLMError,
    LLMConfigurationError,
    LLMAPIError,
)


class TestLLMService(unittest.TestCase):
    def test_mock_provider_generates_schema_aligned_sql(self):
        mock = MockLLMProvider()
        service = LLMService(provider=mock)

        # Test branch loan query
        sql_branch = service.generate_sql("Which branch has the highest loan amount?", "Schema context")
        self.assertIn("Branch_Name", sql_branch)
        self.assertIn("Loan_Amount", sql_branch)
        self.assertTrue(sql_branch.startswith("SELECT"))

        # Test credit card query
        sql_card = service.generate_sql("Show credit card utilization", "Schema context")
        self.assertIn("credit_cards", sql_card.lower())
        self.assertIn("Outstanding_Balance", sql_card)

        # Test fraud query
        sql_fraud = service.generate_sql("Show fraud transactions", "Schema context")
        self.assertIn("transactions", sql_fraud.lower())
        self.assertIn("Is_Fraud", sql_fraud)

    def test_mock_provider_explains_results(self):
        mock = MockLLMProvider()
        service = LLMService(provider=mock)

        explanation = service.explain_results(
            user_question="What is the average loan amount?",
            sql_query="SELECT AVG(Loan_Amount) FROM loans",
            result_preview="Avg_Loan: 45000",
            row_count=1,
        )
        self.assertIn("Executive Summary", explanation)
        self.assertIn("banking_risk_analytics", explanation)

    def test_mock_provider_explains_empty_results(self):
        mock = MockLLMProvider()
        service = LLMService(provider=mock)

        explanation = service.explain_results(
            user_question="Show transactions above 1000000",
            sql_query="SELECT * FROM transactions WHERE Amount > 1000000",
            result_preview="",
            row_count=0,
        )
        self.assertIn("No matching records were found", explanation)

    def test_generate_sql_empty_question_raises(self):
        service = LLMService(provider=MockLLMProvider())
        with self.assertRaises(ValueError):
            service.generate_sql("", "Schema context")
        with self.assertRaises(ValueError):
            service.generate_sql("   ", "Schema context")

    def test_provider_initialization_gemini(self):
        original_key = os.environ.get("LLM_API_KEY")
        original_model = os.environ.get("LLM_MODEL")
        try:
            os.environ["LLM_API_KEY"] = "AIzaSyTestGeminiKey123"
            os.environ["LLM_MODEL"] = "gemini-2.5-flash"
            service = LLMService()
            self.assertIsInstance(service.provider, GeminiProvider)
        finally:
            if original_key is not None:
                os.environ["LLM_API_KEY"] = original_key
            else:
                os.environ.pop("LLM_API_KEY", None)
            if original_model is not None:
                os.environ["LLM_MODEL"] = original_model
            else:
                os.environ.pop("LLM_MODEL", None)

    def test_provider_initialization_anthropic(self):
        original_key = os.environ.get("LLM_API_KEY")
        original_model = os.environ.get("LLM_MODEL")
        try:
            os.environ["LLM_API_KEY"] = "sk-ant-api03-testkey"
            os.environ["LLM_MODEL"] = "claude-3-5-sonnet-20241022"
            service = LLMService()
            self.assertIsInstance(service.provider, AnthropicProvider)
        finally:
            if original_key is not None:
                os.environ["LLM_API_KEY"] = original_key
            else:
                os.environ.pop("LLM_API_KEY", None)
            if original_model is not None:
                os.environ["LLM_MODEL"] = original_model
            else:
                os.environ.pop("LLM_MODEL", None)

    def test_provider_missing_key_raises_configuration_error(self):
        with self.assertRaises(LLMConfigurationError):
            OpenAICompatibleProvider(api_key="")
        with self.assertRaises(LLMConfigurationError):
            GeminiProvider(api_key="")
        with self.assertRaises(LLMConfigurationError):
            AnthropicProvider(api_key="")


if __name__ == "__main__":
    unittest.main()
