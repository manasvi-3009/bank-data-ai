"""
Unit tests for SQL validation, security guardrails, and safe execution in Bank Data AI.

Tests query cleaning, read-only validation, comment stripping, and security blocking of mutating
statements and obfuscation attempts without modifying real database state.
"""

from __future__ import annotations
import unittest
from sqlalchemy import create_engine, text
from sql_service import (
    validate_sql,
    clean_sql,
    execute_query,
    execute_query_with_metadata,
    SQLValidationError,
    SQLExecutionError,
)


class TestSQLService(unittest.TestCase):
    def test_clean_sql_strips_markdown_and_semicolons(self):
        raw_markdown = "```sql\nSELECT * FROM sample_table;\n```"
        self.assertEqual(clean_sql(raw_markdown), "SELECT * FROM sample_table")
        raw_upper = "```SQL\nSELECT * FROM sample_table;\n```"
        self.assertEqual(clean_sql(raw_upper), "SELECT * FROM sample_table")
        raw_plain = "```\nSELECT * FROM sample_table\n```"
        self.assertEqual(clean_sql(raw_plain), "SELECT * FROM sample_table")

    def test_validate_sql_valid_select(self):
        valid_queries = [
            "SELECT * FROM accounts WHERE Current_Balance > 1000",
            "SELECT Branch_Name, COUNT(*) FROM branches GROUP BY Branch_Name",
            "SELECT c.Customer_ID, c.First_Name, a.Current_Balance FROM customers c JOIN accounts a ON c.Customer_ID = a.Customer_ID",
            "SELECT DISTINCT Account_Type FROM accounts",
        ]
        for q in valid_queries:
            with self.subTest(query=q):
                is_valid, err = validate_sql(q)
                self.assertTrue(is_valid)
                self.assertIsNone(err)

    def test_validate_sql_valid_cte(self):
        valid_cte = """
        WITH branch_loans AS (
            SELECT Branch_ID, SUM(Loan_Amount) AS total_loans
            FROM loans
            GROUP BY Branch_ID
        )
        SELECT * FROM branch_loans WHERE total_loans > 500000
        """
        is_valid, err = validate_sql(valid_cte)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_validate_sql_blocks_mutating_statements(self):
        mutating_queries = [
            "DROP TABLE accounts;",
            "DROP DATABASE banking_risk_analytics",
            "DELETE FROM customers WHERE Customer_ID = 1",
            "UPDATE accounts SET Current_Balance = 999999 WHERE Account_ID = 1",
            "INSERT INTO transactions (Amount) VALUES (50000)",
            "ALTER TABLE customers ADD COLUMN test_col VARCHAR(10)",
            "TRUNCATE TABLE loans",
            "CREATE TABLE temp_table (id INT)",
            "GRANT ALL PRIVILEGES ON *.* TO 'unauthorized'@'%'",
            "REVOKE SELECT ON *.* FROM 'analyst'@'%'",
            "REPLACE INTO accounts (Account_ID, Current_Balance) VALUES (1, 10)",
            "EXECUTE stored_proc",
            "CALL sp_transfer_funds(1, 2, 500)",
            "LOCK TABLES accounts WRITE",
            "UNLOCK TABLES",
            "SET GLOBAL max_connections = 1000",
            "USE mysql",
            "FLUSH PRIVILEGES",
            "KILL 1234",
            "SHUTDOWN",
            "SELECT * FROM accounts INTO OUTFILE '/tmp/dump.txt'",
            "SELECT LOAD_FILE('/etc/passwd')",
        ]
        for query in mutating_queries:
            with self.subTest(query=query):
                is_valid, err = validate_sql(query)
                self.assertFalse(is_valid)
                self.assertIsNotNone(err)
                self.assertIn("Only read-only analytical queries are supported", err)

    def test_validate_sql_blocks_multiple_statements(self):
        stacked_queries = [
            "SELECT * FROM accounts; DROP TABLE accounts;",
            "SELECT * FROM loans; DELETE FROM loans WHERE 1=1;",
            "SELECT 1; SELECT 2;",
        ]
        for query in stacked_queries:
            with self.subTest(query=query):
                is_valid, err = validate_sql(query)
                self.assertFalse(is_valid)
                self.assertIn("Multiple SQL statements", err)

    def test_validate_sql_blocks_comment_obfuscation(self):
        obfuscated_queries = [
            "/* bypass comment */ DROP TABLE accounts",
            "-- comment \n DELETE FROM customers",
            "# inline comment \n ALTER TABLE branches DROP COLUMN City",
            "SELECT * FROM accounts; /* comment */ DROP TABLE accounts",
        ]
        for query in obfuscated_queries:
            with self.subTest(query=query):
                is_valid, err = validate_sql(query)
                self.assertFalse(is_valid)
                self.assertIn("Only read-only analytical queries are supported", err)

    def test_validate_sql_empty_query(self):
        is_valid, err = validate_sql("")
        self.assertFalse(is_valid)
        self.assertIn("empty", err)

        is_valid2, err2 = validate_sql("   ")
        self.assertFalse(is_valid2)
        self.assertIn("empty", err2)

        is_valid3, err3 = validate_sql("/* only comments */")
        self.assertFalse(is_valid3)
        self.assertIn("comments or whitespace", err3)

    def test_execute_query_success_sqlite(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE test_data (id INT, label TEXT, val REAL)"))
            conn.execute(text("INSERT INTO test_data VALUES (1, 'Alpha', 100.5), (2, 'Beta', 200.0)"))
            conn.commit()

        df = execute_query("SELECT * FROM test_data ORDER BY id", engine=engine)
        self.assertEqual(len(df), 2)
        self.assertEqual(df["label"].tolist(), ["Alpha", "Beta"])

    def test_execute_query_with_metadata(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE metrics (name TEXT, score INT)"))
            conn.execute(text("INSERT INTO metrics VALUES ('A', 90), ('B', 80)"))
            conn.commit()

        df, row_count, elapsed_ms = execute_query_with_metadata("SELECT * FROM metrics", engine=engine)
        self.assertEqual(row_count, 2)
        self.assertEqual(len(df), 2)
        self.assertGreaterEqual(elapsed_ms, 0.0)

    def test_execute_query_rejects_unsafe_before_execution(self):
        engine = create_engine("sqlite:///:memory:")
        with self.assertRaises(SQLValidationError):
            execute_query("DROP TABLE important_table", engine=engine)

    def test_execute_query_handles_syntax_error(self):
        engine = create_engine("sqlite:///:memory:")
        with self.assertRaises(SQLExecutionError):
            execute_query("SELECT FROM WHERE INVALID SQL", engine=engine)


if __name__ == "__main__":
    unittest.main()
