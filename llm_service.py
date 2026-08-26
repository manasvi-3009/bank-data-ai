"""
LLM service abstraction module for Bank Data AI.

Provides an extensible interface and service layer for natural language to SQL
translation and analytical insight generation.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from config import config


class BaseLLMProvider(ABC):
    """Abstract base class defining the interface for LLM providers."""

    @abstractmethod
    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        """Generate text completion from prompt."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """Fallback / Mock LLM provider used when no API key is configured or during offline testing."""

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return (
            "-- LLM API key not configured.\n"
            "-- Please set LLM_API_KEY in your .env file to enable NL-to-SQL generation.\n"
            "SELECT * FROM accounts LIMIT 5;"
        )


class LLMService:
    """
    High-level LLM service coordinating prompt construction and responses
    for natural language to SQL and analytical insights.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or self._init_default_provider()

    def _init_default_provider(self) -> BaseLLMProvider:
        """Initializes provider based on environment configuration."""
        if not config.is_llm_configured:
            return MockLLMProvider()

        # Architecture ready for provider integration (e.g. OpenAI, Google GenAI, Anthropic)
        # For setup stage, return mock if client library is not yet initialized
        return MockLLMProvider()

    def generate_sql(self, user_question: str, schema_context: str) -> str:
        """
        Translates a natural language question into a safe, dialect-correct MySQL query.
        (Placeholder for NL-to-SQL pipeline implementation).
        """
        system_prompt = (
            "You are an expert MySQL database analyst for a commercial bank. "
            "Given the database schema for `banking_risk_analytics`, write a single read-only SQL query "
            "that answers the user's question accurately. Do not include markdown explanations, only SQL."
        )
        user_prompt = f"Database Schema:\n{schema_context}\n\nUser Question: {user_question}"
        return self.provider.generate_text(system_prompt, user_prompt)

    def explain_results(
        self,
        user_question: str,
        sql_query: str,
        result_preview: str,
    ) -> str:
        """
        Generates a concise executive summary answering the user's question based on query results.
        (Placeholder for NL-to-SQL pipeline implementation).
        """
        system_prompt = (
            "You are a helpful banking financial analyst. Summarize the findings from the query result "
            "in clear, executive-ready language."
        )
        user_prompt = (
            f"User Question: {user_question}\n"
            f"Executed SQL: {sql_query}\n"
            f"Query Results Summary:\n{result_preview}"
        )
        return self.provider.generate_text(system_prompt, user_prompt, temperature=0.3)


# Global singleton instance
llm_service = LLMService()
