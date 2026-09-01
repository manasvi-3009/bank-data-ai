"""
Unit tests for intelligent visualization selection heuristics.
"""

from __future__ import annotations
import unittest
import pandas as pd
from visualization import get_chart_recommendation


class TestVisualizationHeuristics(unittest.TestCase):
    def test_empty_or_none_returns_none(self):
        self.assertIsNone(get_chart_recommendation(None))
        self.assertIsNone(get_chart_recommendation(pd.DataFrame()))

    def test_single_row_kpi_metrics(self):
        df = pd.DataFrame([{"total_loan_amount": 5000000.00, "avg_rate": 10.5}])
        rec = get_chart_recommendation(df)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["type"], "metric")
        self.assertIn("total_loan_amount", rec["columns"])

    def test_categorical_bar_chart(self):
        df = pd.DataFrame(
            {
                "Branch_Name": ["Hazratganj", "Park Street", "Banjara Hills", "MG Road"],
                "Total_Customers": [31, 29, 29, 27],
            }
        )
        rec = get_chart_recommendation(df)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["type"], "bar")
        self.assertEqual(rec["x"], "Branch_Name")
        self.assertEqual(rec["y"], "Total_Customers")

    def test_time_series_line_chart(self):
        df = pd.DataFrame(
            {
                "Transaction_Date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                "Daily_Volume": [150000.0, 220000.0, 180000.0, 310000.0],
            }
        )
        rec = get_chart_recommendation(df)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["type"], "line")
        self.assertEqual(rec["x"], "Transaction_Date")
        self.assertEqual(rec["y"], "Daily_Volume")

    def test_two_numeric_scatter_plot(self):
        df = pd.DataFrame(
            {
                "Risk_Score": [300, 450, 600, 720, 800, 850],
                "Annual_Income": [30000, 45000, 70000, 95000, 120000, 180000],
            }
        )
        rec = get_chart_recommendation(df)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["type"], "scatter")

    def test_single_numeric_histogram(self):
        df = pd.DataFrame({"Salary": [40000 + i * 5000 for i in range(30)]})
        rec = get_chart_recommendation(df)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["type"], "histogram")
        self.assertEqual(rec["column"], "Salary")

    def test_all_null_numeric_returns_none(self):
        df = pd.DataFrame({"Account_Type": ["Savings", "Current"], "Current_Balance": [None, None]})
        rec = get_chart_recommendation(df)
        self.assertIsNone(rec)


if __name__ == "__main__":
    unittest.main()
