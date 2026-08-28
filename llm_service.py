"""
LLM service module for Bank Data AI.

Provides an extensible interface and service layer for natural language to SQL
translation, safe query construction, and analytical executive insight generation.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import json
import re
from typing import Any, Dict, List, Optional
import requests
from config import config


class LLMError(Exception):
    """Base exception for LLM service operations."""
    pass


class LLMConfigurationError(LLMError):
    """Raised when LLM configuration is missing or invalid."""
    pass


class LLMAPIError(LLMError):
    """Raised when an external LLM API request fails."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when an LLM API request times out."""
    pass


class BaseLLMProvider(ABC):
    """Abstract base class defining the interface for LLM providers."""

    @abstractmethod
    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        """Generate text completion from system and user prompts."""
        pass


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    HTTP REST provider compatible with OpenAI, OpenRouter, Groq, local vLLM/Ollama,
    and any service adhering to the /chat/completions API format.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        self.api_key = api_key or config.llm_api_key
        self.model = model or config.llm_model
        self.base_url = (base_url or config.llm_base_url).rstrip("/")
        self.timeout = timeout

        if not self.api_key:
            raise LLMConfigurationError("LLM API key is not configured.")

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        except requests.exceptions.Timeout as exc:
            raise LLMTimeoutError(f"LLM API request timed out after {self.timeout}s.") from exc
        except requests.exceptions.RequestException as exc:
            raise LLMAPIError(f"Network error communicating with LLM service: {str(exc)}") from exc

        if response.status_code == 401:
            raise LLMAPIError("Authentication failed: Invalid LLM API key. Check LLM_API_KEY in .env.")
        elif response.status_code == 429:
            raise LLMAPIError("LLM API rate limit exceeded or quota exhausted. Please retry shortly.")
        elif response.status_code >= 400:
            err_text = response.text[:300]
            raise LLMAPIError(f"LLM API returned error {response.status_code}: {err_text}")

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip()
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMAPIError(f"Unexpected response format from LLM API: {str(exc)}") from exc


class MockLLMProvider(BaseLLMProvider):
    """
    Offline fallback provider used when no API key is configured or during testing.
    Produces context-aware, syntactically valid read-only SQL matching banking queries.
    """

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        lower_prompt = user_prompt.lower()

        # Handle analytical explanation prompt
        if "summarize" in system_prompt.lower() or "analyst" in system_prompt.lower() and "results" in lower_prompt:
            return (
                "**Executive Summary:**\n"
                "The analysis successfully queried the `banking_risk_analytics` database. "
                "The resulting dataset reflects expected distributions across the requested financial metrics. "
                "Key figures and segment breakdowns are detailed in the data table above."
            )

        # Contextual SQL generation fallback matching questions
        if "loan" in lower_prompt or "borrower" in lower_prompt:
            if "branch" in lower_prompt:
                return (
                    "SELECT b.branch_name, COUNT(l.loan_id) AS total_loans, "
                    "SUM(l.loan_amount) AS total_loan_amount, AVG(l.interest_rate) AS avg_interest_rate "
                    "FROM loans l JOIN accounts a ON l.account_id = a.account_id "
                    "JOIN branches b ON a.branch_id = b.branch_id "
                    "GROUP BY b.branch_name ORDER BY total_loan_amount DESC;"
                )
            return "SELECT loan_id, customer_id, loan_amount, interest_rate, status FROM loans ORDER BY loan_amount DESC LIMIT 10;"

        if "transaction" in lower_prompt or "volume" in lower_prompt or "deposit" in lower_prompt or "withdrawal" in lower_prompt:
            return (
                "SELECT t.account_id, a.account_type, COUNT(t.transaction_id) AS transaction_count, "
                "SUM(t.amount) AS total_volume "
                "FROM transactions t JOIN accounts a ON t.account_id = a.account_id "
                "GROUP BY t.account_id, a.account_type ORDER BY total_volume DESC LIMIT 10;"
            )

        if "credit card" in lower_prompt or "card" in lower_prompt:
            return "SELECT card_id, customer_id, credit_limit, balance, (balance / credit_limit) * 100 AS utilization_rate FROM credit_cards ORDER BY balance DESC LIMIT 10;"

        if "customer" in lower_prompt or "risk" in lower_prompt or "kyc" in lower_prompt:
            return "SELECT customer_id, first_name, last_name, credit_score, risk_category FROM customers ORDER BY credit_score ASC LIMIT 10;"

        if "branch" in lower_prompt or "location" in lower_prompt:
            return "SELECT branch_id, branch_name, city, state FROM branches ORDER BY branch_name ASC;"

        if "employee" in lower_prompt or "staff" in lower_prompt or "manager" in lower_prompt:
            return "SELECT employee_id, first_name, last_name, role, department FROM employees ORDER BY department, last_name;"

        # Default accounts summary
        return "SELECT account_id, customer_id, account_type, balance, status FROM accounts ORDER BY balance DESC LIMIT 10;"


class LLMService:
    """
    High-level LLM service coordinating prompt construction, NL-to-SQL translation,
    and business executive summaries for the Bank Data AI platform.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self._custom_provider = provider

    @property
    def provider(self) -> BaseLLMProvider:
        """Dynamically retrieves configured provider (allowing live toggle via .env)."""
        if self._custom_provider is not None:
            return self._custom_provider
        return self._init_default_provider()

    def _init_default_provider(self) -> BaseLLMProvider:
        """Initializes provider based on environment configuration."""
        if config.is_llm_configured:
            try:
                return OpenAICompatibleProvider()
            except Exception:
                return MockLLMProvider()
        return MockLLMProvider()

    def generate_sql(self, user_question: str, schema_context: str) -> str:
        """
        Translates a natural language question into a safe, dialect-correct MySQL query
        using the dynamically inspected database schema context.
        """
        if not user_question or not user_question.strip():
            raise ValueError("User question cannot be empty.")

        system_prompt = (
            "You are an expert MySQL database financial analyst for a commercial bank.\n"
            "Given the provided database schema for `banking_risk_analytics`, write a single read-only SQL query (SELECT or WITH) "
            "that directly and accurately answers the user's question.\n\n"
            "CRITICAL CONSTRAINTS & RULES:\n"
            "1. Output ONLY the raw SQL query. Do NOT include explanations, comments, or markdown code block formatting (```).\n"
            "2. The query MUST strictly be a read-only statement starting with SELECT or WITH.\n"
            "3. NEVER use mutating operations or DDL (DROP, DELETE, INSERT, UPDATE, ALTER, TRUNCATE, CREATE, GRANT, etc.).\n"
            "4. Strictly use only table names and column names that exist in the provided schema context. Do NOT invent columns or tables.\n"
            "5. When joining tables, adhere strictly to the foreign key relationships shown in the schema.\n"
            "6. Use appropriate aggregations (SUM, AVG, COUNT, MIN, MAX), filters (WHERE), groupings (GROUP BY), and sorting (ORDER BY) when asked.\n"
            "7. Target MySQL 8.0+ dialect.\n"
        )

        user_prompt = (
            f"### Database Schema (`banking_risk_analytics`):\n"
            f"{schema_context}\n\n"
            f"### User Question:\n"
            f"{user_question.strip()}\n\n"
            f"### SQL Query:"
        )

        raw_sql = self.provider.generate_text(system_prompt, user_prompt, temperature=0.0)

        # Strip accidental code fences or leading/trailing tokens
        cleaned = raw_sql.strip()
        if cleaned.lower().startswith("```sql"):
            cleaned = cleaned[6:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        return cleaned.strip().rstrip(";")

    def explain_results(
        self,
        user_question: str,
        sql_query: str,
        result_preview: str,
        row_count: int,
    ) -> str:
        """
        Generates a concise, executive-ready narrative summarizing the query findings
        in clear business and financial risk context.
        """
        system_prompt = (
            "You are a Senior Banking Risk & Financial Data Analyst.\n"
            "Given a user's question, the SQL query executed, and the resulting dataset summary, "
            "provide a clear, concise executive summary answering the question.\n"
            "Highlight key totals, averages, top contributors, or potential risk indicators. "
            "Keep the tone professional, direct, and factual without making speculative assumptions beyond the data."
        )

        user_prompt = (
            f"User Question: {user_question}\n"
            f"Executed Query: {sql_query}\n"
            f"Total Rows Returned: {row_count}\n\n"
            f"Results Summary:\n{result_preview}\n\n"
            f"Executive Summary:"
        )

        return self.provider.generate_text(system_prompt, user_prompt, temperature=0.2)


# Global singleton instance
llm_service = LLMService()
