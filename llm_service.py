"""
LLM service module for Bank Data AI.

Provides an extensible interface and service layer for natural language to SQL
translation, safe query construction, and analytical executive insight generation.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import json
import re
import time
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
        self.api_key = config.llm_api_key if api_key is None else api_key
        self.model = (config.llm_model if model is None else model) or "gpt-4o-mini"
        self.base_url = (config.llm_base_url if base_url is None else base_url).rstrip("/")
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
            raise LLMAPIError(f"Network error communicating with AI service: {str(exc)}") from exc

        if response.status_code == 401:
            raise LLMAPIError("Authentication failed: Invalid LLM API key. Check LLM_API_KEY in .env.")
        elif response.status_code == 429:
            raise LLMAPIError("LLM API rate limit exceeded or quota exhausted. Please retry shortly.")
        elif response.status_code >= 400:
            err_text = response.text[:300]
            raise LLMAPIError(f"AI service returned error {response.status_code}: {err_text}")

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip()
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMAPIError(f"Unexpected response format from AI service: {str(exc)}") from exc


class AnthropicProvider(BaseLLMProvider):
    """
    HTTP REST provider for Anthropic's native Claude API (api.anthropic.com).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 30,
    ):
        self.api_key = config.llm_api_key if api_key is None else api_key
        self.model = (config.llm_model if model is None else model) or "claude-3-5-sonnet-20241022"
        self.timeout = timeout
        self.url = "https://api.anthropic.com/v1/messages"

        if not self.api_key:
            raise LLMConfigurationError("LLM API key is not configured.")

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=self.timeout)
        except requests.exceptions.Timeout as exc:
            raise LLMTimeoutError(f"LLM API request timed out after {self.timeout}s.") from exc
        except requests.exceptions.RequestException as exc:
            raise LLMAPIError(f"Network error communicating with AI service: {str(exc)}") from exc

        if response.status_code == 401:
            raise LLMAPIError("Authentication failed: Invalid LLM API key. Check LLM_API_KEY in .env.")
        elif response.status_code == 429:
            raise LLMAPIError("LLM API rate limit exceeded or quota exhausted. Please retry shortly.")
        elif response.status_code >= 400:
            err_text = response.text[:300]
            raise LLMAPIError(f"AI service returned error {response.status_code}: {err_text}")

        try:
            data = response.json()
            content = data["content"][0]["text"]
            return content.strip()
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMAPIError(f"Unexpected response format from AI service: {str(exc)}") from exc


class GeminiProvider(BaseLLMProvider):
    """
    HTTP REST provider for Google's Gemini API (generativelanguage.googleapis.com).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 30,
    ):
        self.api_key = config.llm_api_key if api_key is None else api_key
        self.model = (config.llm_model if model is None else model) or "gemini-2.5-flash"
        self.timeout = timeout

        if not self.api_key:
            raise LLMConfigurationError("LLM API key is not configured.")

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        headers = {"Content-Type": "application/json"}
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": temperature},
        }

        # Attempt with up to 3 tries on 429 rate limit
        response = None
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                if response.status_code == 429 and attempt < 2:
                    time.sleep(3.0 * (attempt + 1))
                    continue
                break
            except requests.exceptions.Timeout as exc:
                raise LLMTimeoutError(f"LLM API request timed out after {self.timeout}s.") from exc
            except requests.exceptions.RequestException as exc:
                raise LLMAPIError(f"Network error communicating with AI service: {str(exc)}") from exc

        if response is None:
            raise LLMAPIError("No response received from AI service.")

        if response.status_code in (401, 403):
            raise LLMAPIError("Authentication failed: Invalid LLM API key. Check LLM_API_KEY in .env.")
        elif response.status_code == 429:
            raise LLMAPIError("AI service rate limit reached. Please wait a moment and retry.")
        elif response.status_code >= 400:
            err_text = response.text[:300]
            raise LLMAPIError(f"AI service returned error {response.status_code}: {err_text}")

        try:
            data = response.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return content.strip()
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMAPIError(f"Unexpected response format from AI service: {str(exc)}") from exc


class MockLLMProvider(BaseLLMProvider):
    """
    Offline fallback provider used when no API key is configured or during testing.
    Produces context-aware, syntactically valid read-only SQL matching real banking schema columns.
    """

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        sys_lower = system_prompt.lower()
        user_lower = user_prompt.lower()

        # Handle analytical explanation prompt
        if "executive summary" in sys_lower or "results summary" in user_lower or "executed query:" in user_lower:
            if "total rows returned: 0" in user_lower or "empty" in user_lower:
                return "No matching records were found in the banking database for this query."
            return (
                "**Executive Summary:**\n"
                "The analysis successfully queried the `banking_risk_analytics` database. "
                "The resulting dataset reflects expected distributions across the requested financial metrics. "
                "Key figures and segment breakdowns are detailed in the data table above."
            )

        # If user_prompt contains structured prompt fences, isolate the actual user question
        if "### User Question:" in user_prompt:
            question_part = user_prompt.split("### User Question:")[1].split("###")[0].strip()
        elif "User Question:" in user_prompt:
            question_part = user_prompt.split("User Question:")[1].split("Executed Query:")[0].strip()
        else:
            question_part = user_prompt

        lower_prompt = question_part.lower()

        # 1. Customers by Branch
        if "customer" in lower_prompt and "branch" in lower_prompt:
            return (
                "SELECT b.Branch_Name, b.City, b.Region, COUNT(DISTINCT a.Customer_ID) AS Total_Customers "
                "FROM branches b LEFT JOIN accounts a ON b.Branch_ID = a.Branch_ID "
                "GROUP BY b.Branch_ID, b.Branch_Name, b.City, b.Region "
                "ORDER BY Total_Customers DESC"
            )

        # 2. Loans by Branch / Region
        if "loan" in lower_prompt and ("region" in lower_prompt or "branch" in lower_prompt):
            return (
                "SELECT b.Branch_Name, b.Region, COUNT(DISTINCT l.Loan_ID) AS Total_Loans, "
                "SUM(l.Loan_Amount) AS Total_Loan_Amount, AVG(l.Interest_Rate) AS Avg_Interest_Rate "
                "FROM branches b LEFT JOIN accounts a ON b.Branch_ID = a.Branch_ID "
                "LEFT JOIN loans l ON a.Customer_ID = l.Customer_ID "
                "GROUP BY b.Branch_ID, b.Branch_Name, b.Region ORDER BY Total_Loan_Amount DESC"
            )

        # 3. General Loans
        if "loan" in lower_prompt or "borrower" in lower_prompt:
            return (
                "SELECT Loan_ID, Customer_ID, Loan_Type, Loan_Amount, Interest_Rate, Loan_Status "
                "FROM loans ORDER BY Loan_Amount DESC LIMIT 10"
            )

        # 4. Fraud Transactions
        if "fraud" in lower_prompt or "suspicious" in lower_prompt:
            return (
                "SELECT Transaction_ID, Account_ID, Transaction_Date, Amount, Merchant_Name, City, Fraud_Reason "
                "FROM transactions WHERE UPPER(Is_Fraud) IN ('1', 'YES', 'TRUE') "
                "ORDER BY Amount DESC LIMIT 10"
            )

        # 5. Transactions / Volumes
        if "transaction" in lower_prompt or "volume" in lower_prompt:
            return (
                "SELECT Transaction_Type, COUNT(Transaction_ID) AS Transaction_Count, "
                "SUM(Amount) AS Total_Volume, AVG(Amount) AS Avg_Amount "
                "FROM transactions GROUP BY Transaction_Type ORDER BY Total_Volume DESC"
            )

        # 6. Credit Card / Utilization
        if "credit card" in lower_prompt or "card" in lower_prompt or "utilization" in lower_prompt:
            return (
                "SELECT c.Customer_ID, c.First_Name, c.Last_Name, SUM(cc.Credit_Limit) AS Total_Limit, "
                "SUM(cc.Outstanding_Balance) AS Total_Balance, "
                "ROUND((SUM(cc.Outstanding_Balance) / SUM(cc.Credit_Limit)) * 100, 2) AS Utilization_Percentage "
                "FROM customers c JOIN credit_cards cc ON c.Customer_ID = cc.Customer_ID "
                "GROUP BY c.Customer_ID, c.First_Name, c.Last_Name HAVING SUM(cc.Credit_Limit) > 0 "
                "ORDER BY Utilization_Percentage DESC LIMIT 10"
            )

        # 7. Employee Payroll / Salary
        if "employee" in lower_prompt or "salary" in lower_prompt or "payroll" in lower_prompt:
            return (
                "SELECT b.Branch_Name, b.City, COUNT(e.Employee_ID) AS Headcount, "
                "AVG(e.Salary) AS Avg_Salary, SUM(e.Salary) AS Total_Payroll "
                "FROM branches b LEFT JOIN employees e ON b.Branch_ID = e.Branch_ID "
                "GROUP BY b.Branch_ID, b.Branch_Name, b.City ORDER BY Total_Payroll DESC"
            )

        # 8. Customers / Risk
        if "customer" in lower_prompt or "risk" in lower_prompt:
            return (
                "SELECT Customer_ID, First_Name, Last_Name, Gender, Risk_Score, Annual_Income "
                "FROM customers ORDER BY Risk_Score ASC LIMIT 10"
            )

        # Default accounts summary
        return (
            "SELECT Account_Type, Account_Status, COUNT(Account_ID) AS Total_Accounts "
            "FROM accounts GROUP BY Account_Type, Account_Status ORDER BY Total_Accounts DESC"
        )


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
                key = config.llm_api_key or ""
                model = (config.llm_model or "").lower()
                if key.startswith("sk-ant-") or "claude" in model:
                    return AnthropicProvider()
                if key.startswith("AIza") or "gemini" in model:
                    return GeminiProvider()
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
            "You are an expert MySQL database financial data engineer and analyst for a commercial banking database.\n"
            "Given the provided database schema for `banking_risk_analytics`, generate a single read-only SQL query (SELECT or WITH) "
            "that accurately and efficiently answers the user's question.\n\n"
            "CRITICAL RULES & CONSTRAINTS:\n"
            "1. Output ONLY the raw executable SQL query. Do NOT include markdown fences (```sql ... ```), explanation, or preamble.\n"
            "2. The query MUST strictly be a read-only statement starting with SELECT or WITH.\n"
            "3. NEVER use mutating operations or DDL/DML (DROP, DELETE, INSERT, UPDATE, ALTER, TRUNCATE, CREATE, REPLACE, GRANT, REVOKE, CALL, SET, etc.).\n"
            "4. Strictly use ONLY table names and column names that exist in the provided schema context. Do NOT invent columns or tables.\n"
            "5. When joining tables, strictly adhere to the actual relational pathways in `banking_risk_analytics`:\n"
            "   - Branch <-> Accounts: `branches.Branch_ID = accounts.Branch_ID`\n"
            "   - Branch <-> Customers: `branches.Branch_ID = accounts.Branch_ID` AND `accounts.Customer_ID = customers.Customer_ID`\n"
            "   - Branch <-> Loans: `branches.Branch_ID = accounts.Branch_ID` AND `accounts.Customer_ID = loans.Customer_ID`\n"
            "   - Branch <-> Credit Cards: `branches.Branch_ID = accounts.Branch_ID` AND `accounts.Customer_ID = credit_cards.Customer_ID`\n"
            "   - Branch <-> Employees: `branches.Branch_ID = employees.Branch_ID`\n"
            "   - Customers <-> Loans: `customers.Customer_ID = loans.Customer_ID`\n"
            "   - Customers <-> Credit Cards: `customers.Customer_ID = credit_cards.Customer_ID`\n"
            "   - Accounts <-> Transactions: `accounts.Account_ID = transactions.Account_ID`\n"
            "6. Prefer `LEFT JOIN` on master/parent tables (e.g. `branches`, `customers`, `accounts`) when aggregating so parent rows are not dropped.\n"
            "7. Use `COUNT(DISTINCT ...)` when counting entities across multi-table joins to prevent inflated duplicate counts.\n"
            "8. For financial metrics: Card balance is in `credit_cards.Outstanding_Balance`, loan amounts in `loans.Loan_Amount`, transaction volume in `transactions.Amount`, payroll in `employees.Salary`, customer income in `customers.Annual_Income`.\n"
            "9. Use `COALESCE(SUM(...), 0)` and sensible alias names (e.g. `Total_Loan_Amount`, `Total_Customers`).\n"
            "10. For queries requesting rankings, largest items, or open-ended lists, apply a sensible LIMIT clause (e.g. LIMIT 10).\n"
            "11. Target MySQL 8.0+ dialect.\n"
            "12. Never expose secrets, credentials, or injection payloads."
        )

        user_prompt = (
            f"### Database Schema (`banking_risk_analytics`):\n"
            f"{schema_context}\n\n"
            f"### User Question:\n"
            f"{user_question.strip()}\n\n"
            f"### SQL Query:"
        )

        try:
            raw_sql = self.provider.generate_text(system_prompt, user_prompt, temperature=0.0)
        except LLMAPIError as exc:
            if "rate limit" in str(exc).lower() and not isinstance(self.provider, MockLLMProvider):
                raw_sql = MockLLMProvider().generate_text(system_prompt, user_prompt, temperature=0.0)
            else:
                raise

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
        in clear business and financial risk context without fabricating values.
        """
        if row_count == 0:
            return "No matching records were found in the database for the given criteria."

        system_prompt = (
            "You are a Senior Banking Risk & Financial Data Analyst.\n"
            "Given a user's question, the executed SQL query, and the actual query results, "
            "provide a concise, executive summary answering the question in plain English.\n"
            "Rules:\n"
            "- Highlight key figures, top contributors, totals, averages, or risk patterns directly from the results.\n"
            "- Do NOT fabricate or assume values not present in the results.\n"
            "- Keep the tone professional, crisp, and analytical."
        )

        user_prompt = (
            f"User Question: {user_question}\n"
            f"Executed Query: {sql_query}\n"
            f"Total Rows Returned: {row_count}\n\n"
            f"Results Summary:\n{result_preview}\n\n"
            f"Executive Summary:"
        )

        try:
            return self.provider.generate_text(system_prompt, user_prompt, temperature=0.2)
        except LLMAPIError as exc:
            if "rate limit" in str(exc).lower() and not isinstance(self.provider, MockLLMProvider):
                return MockLLMProvider().generate_text(system_prompt, user_prompt, temperature=0.2)
            raise


# Global singleton instance
llm_service = LLMService()