"""
Unit tests for SQL validation and security guardrails in Bank Data AI.

Tests query cleaning, read-only validation, and security blocking of mutating
statements without connecting to or assuming schema columns.
"""

import unittest
from sql_service import validate_sql, clean_sql


class TestSQLService(unittest.TestCase):
    def test_clean_sql_strips_markdown_and_semicolons(self):
        raw_markdown = "```sql\nSELECT * FROM sample_table;\n```"
        self.assertEqual(clean_sql(raw_markdown), "SELECT * FROM sample_table")
        raw_upper = "```SQL\nSELECT * FROM sample_table;\n```"
        self.assertEqual(clean_sql(raw_upper), "SELECT * FROM sample_table")

    def test_validate_sql_valid_select(self):
        valid_query = "SELECT * FROM sample_table WHERE value > 100"
        is_valid, err = validate_sql(valid_query)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_validate_sql_valid_cte(self):
        valid_cte = """
        WITH cte_summary AS (
            SELECT group_id, SUM(value) as total_val
            FROM sample_table
            GROUP BY group_id
        )
        SELECT * FROM cte_summary WHERE total_val > 50000
        """
        is_valid, err = validate_sql(valid_cte)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_validate_sql_blocks_mutating_statements(self):
        mutating_queries = [
            "DROP TABLE sample_table;",
            "DELETE FROM sample_table WHERE id = 1",
            "UPDATE sample_table SET value = 999 WHERE id = 1",
            "INSERT INTO sample_table (value) VALUES (500)",
            "ALTER TABLE sample_table ADD COLUMN test_col VARCHAR(10)",
            "TRUNCATE TABLE sample_table",
            "CREATE TABLE sample_table_copy (id INT)",
            "GRANT ALL PRIVILEGES ON *.* TO 'unauthorized_user'@'%'",
            "REVOKE ALL PRIVILEGES ON *.* FROM 'user'@'%'",
            "REPLACE INTO sample_table (id, value) VALUES (1, 10)",
            "EXECUTE stored_procedure",
            "CALL procedure_name()",
        ]
        for query in mutating_queries:
            with self.subTest(query=query):
                is_valid, err = validate_sql(query)
                self.assertFalse(is_valid)
                self.assertIsNotNone(err)
                self.assertTrue("Forbidden" in err or "mutating" in err.lower())

    def test_validate_sql_blocks_multiple_statements(self):
        stacked_query = "SELECT * FROM sample_table; DROP TABLE sample_table;"
        is_valid, err = validate_sql(stacked_query)
        self.assertFalse(is_valid)
        self.assertIn("semicolons", err)

    def test_validate_sql_empty_query(self):
        is_valid, err = validate_sql("")
        self.assertFalse(is_valid)
        self.assertIn("empty", err)


if __name__ == "__main__":
    unittest.main()
