"""
End-to-end integration tests for Bank Data AI query flow.

Tests the full pipeline from natural-language question to schema extraction,
SQL generation, security validation, execution against an isolated SQLite test database,
and executive summary formulation.
"""

from __future__ import annotations
import unittest
from sqlalchemy import create_engine, text
import pandas as pd

from database import inspect_database_schema, get_schema_summary_text
from sql_service import validate_sql, execute_query_with_metadata, SQLValidationError
from llm_service import LLMService, MockLLMProvider


class TestQueryFlowIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an isolated in-memory SQLite database matching the real database structure
        cls.test_engine = create_engine("sqlite:///:memory:")
        with cls.test_engine.connect() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE branches (
                        Branch_ID INTEGER PRIMARY KEY,
                        Branch_Name VARCHAR(100) NOT NULL,
                        City VARCHAR(50),
                        Region VARCHAR(50)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE customers (
                        Customer_ID INTEGER PRIMARY KEY,
                        First_Name VARCHAR(50) NOT NULL,
                        Last_Name VARCHAR(50) NOT NULL,
                        Gender VARCHAR(10),
                        Risk_Score INTEGER,
                        Annual_Income REAL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE accounts (
                        Account_ID INTEGER PRIMARY KEY,
                        Customer_ID INTEGER NOT NULL,
                        Branch_ID INTEGER NOT NULL,
                        Account_Type VARCHAR(20),
                        Current_Balance REAL,
                        FOREIGN KEY (Customer_ID) REFERENCES customers(Customer_ID),
                        FOREIGN KEY (Branch_ID) REFERENCES branches(Branch_ID)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE loans (
                        Loan_ID INTEGER PRIMARY KEY,
                        Customer_ID INTEGER NOT NULL,
                        Loan_Type VARCHAR(50),
                        Loan_Amount REAL,
                        Interest_Rate REAL,
                        FOREIGN KEY (Customer_ID) REFERENCES customers(Customer_ID)
                    )
                    """
                )
            )

            # Insert test records
            conn.execute(
                text("INSERT INTO branches VALUES (101, 'Downtown Branch', 'New York', 'East')")
            )
            conn.execute(
                text("INSERT INTO branches VALUES (102, 'Westside Branch', 'Los Angeles', 'West')")
            )
            conn.execute(
                text("INSERT INTO customers VALUES (1001, 'Alice', 'Smith', 'Female', 750, 95000)")
            )
            conn.execute(
                text("INSERT INTO customers VALUES (1002, 'Bob', 'Jones', 'Male', 620, 60000)")
            )
            conn.execute(
                text("INSERT INTO accounts VALUES (201, 1001, 101, 'Savings', 15000.50)")
            )
            conn.execute(
                text("INSERT INTO accounts VALUES (202, 1002, 102, 'Checking', 4200.00)")
            )
            conn.execute(
                text("INSERT INTO loans VALUES (301, 1001, 'Home Loan', 250000.00, 4.5)")
            )
            conn.execute(
                text("INSERT INTO loans VALUES (302, 1002, 'Auto Loan', 35000.00, 6.2)")
            )
            conn.commit()

        cls.service = LLMService(provider=MockLLMProvider())

    def test_full_pipeline_successful_query(self):
        """Tests complete query flow from schema extraction to execution and summary."""
        # 1. Inspect dynamic schema
        schema_data = inspect_database_schema(engine=self.test_engine)
        self.assertIn("branches", schema_data["table_names"])
        self.assertIn("loans", schema_data["table_names"])

        schema_context = get_schema_summary_text(schema_data)
        self.assertIn("Table `branches`", schema_context)

        # 2. Generate SQL
        user_question = "Which branch has the highest loan amount?"
        generated_sql = self.service.generate_sql(user_question, schema_context)
        self.assertTrue(generated_sql.startswith("SELECT"))

        # 3. Validate SQL
        is_valid, err = validate_sql(generated_sql)
        self.assertTrue(is_valid, f"Validation failed: {err}")

        # 4. Execute Query with metadata
        df, row_count, latency_ms = execute_query_with_metadata(
            generated_sql,
            engine=self.test_engine,
        )
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(row_count, 0)
        self.assertGreaterEqual(latency_ms, 0.0)

        # 5. Formulate Executive Summary
        summary = self.service.explain_results(
            user_question,
            generated_sql,
            df.head(5).to_string(index=False),
            row_count,
        )
        self.assertIn("Executive Summary", summary)

    def test_customers_by_branch_query(self):
        """Tests customer count by branch through the accounts pathway."""
        user_question = "Which branch has the highest number of customers?"
        sql = self.service.generate_sql(user_question, "Schema context")
        self.assertTrue(sql.startswith("SELECT"))
        is_valid, _ = validate_sql(sql)
        self.assertTrue(is_valid)

        df, row_count, _ = execute_query_with_metadata(sql, engine=self.test_engine)
        self.assertGreater(row_count, 0)
        self.assertIn("Branch_Name", df.columns)
        self.assertIn("Total_Customers", df.columns)

    def test_pipeline_blocks_malicious_query_generation(self):
        """Verifies that if an unsafe query is generated or inputted, it is blocked immediately."""
        malicious_input = "DROP TABLE accounts"
        is_valid, err = validate_sql(malicious_input)
        self.assertFalse(is_valid)
        self.assertIn("Only read-only analytical queries are supported", err)

        with self.assertRaises(SQLValidationError):
            execute_query_with_metadata(malicious_input, engine=self.test_engine)

    def test_pipeline_handles_empty_result_gracefully(self):
        """Verifies that queries returning 0 rows are handled cleanly without error."""
        empty_query = "SELECT * FROM accounts WHERE Account_ID = 999999"
        is_valid, _ = validate_sql(empty_query)
        self.assertTrue(is_valid)

        df, row_count, _ = execute_query_with_metadata(empty_query, engine=self.test_engine)
        self.assertEqual(row_count, 0)
        self.assertTrue(df.empty)

        summary = self.service.explain_results(
            "Show account 999999",
            empty_query,
            "",
            row_count,
        )
        self.assertIn("No matching records were found", summary)


if __name__ == "__main__":
    unittest.main()
