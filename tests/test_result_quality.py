"""
Unit tests for query result quality, NULL vs empty set handling, and factual summary generation.
"""

from __future__ import annotations
import unittest
import pandas as pd
from llm_service import MockLLMProvider, LLMService


class TestResultQuality(unittest.TestCase):
    def setUp(self):
        self.mock_provider = MockLLMProvider()
        self.service = LLMService(provider=self.mock_provider)

    def test_distinguish_genuinely_empty_result_set(self):
        """0 rows returned should state that no matching records were found."""
        summary = self.service.explain_results(
            user_question="Show accounts with balance > 1000000000",
            sql_query="SELECT * FROM accounts WHERE Current_Balance > 1000000000",
            result_preview="",
            row_count=0,
        )
        self.assertIn("No matching records were found", summary)

    def test_populated_result_summary_includes_executive_finding(self):
        """Populated rows generate structured factual finding."""
        df = pd.DataFrame(
            {
                "Branch_Name": ["Hazratganj", "Park Street"],
                "Total_Customers": [31, 29],
            }
        )
        summary = self.service.explain_results(
            user_question="Which branch has the highest number of customers?",
            sql_query="SELECT b.Branch_Name, COUNT(DISTINCT a.Customer_ID) AS Total_Customers ...",
            result_preview=df.to_string(index=False),
            row_count=2,
        )
        self.assertIn("Executive Summary", summary)
        self.assertIn("banking_risk_analytics", summary)


if __name__ == "__main__":
    unittest.main()
