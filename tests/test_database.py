"""
Unit tests for database module, dynamic schema inspection, and connection handling.

Tests schema parsing and connection diagnostics using mocks without inventing
banking columns or creating tables.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

import database as db


class TestDatabaseModule(unittest.TestCase):
    def test_get_db_engine_raises_on_missing_url(self):
        """Verifies get_db_engine raises ValueError when DATABASE_URL is empty."""
        original = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATABASE_URL"] = ""
            with self.assertRaises(ValueError):
                db.get_db_engine(db_url="", force_new=True)
        finally:
            if original is not None:
                os.environ["DATABASE_URL"] = original
            else:
                os.environ.pop("DATABASE_URL", None)

    @patch("database.inspect")
    def test_inspect_database_schema_dynamically_with_mock(self, mock_inspect):
        """
        Verifies dynamic schema inspection extracts tables, columns, types,
        primary keys, foreign keys, and indexes via the SQLAlchemy inspector API.
        Uses generic abstract metadata with no fake banking schema definitions.
        """
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector

        # Define generic mock table names
        mock_inspector.get_table_names.return_value = ["generic_table_a", "generic_table_b"]

        # Mock metadata for generic_table_a
        mock_inspector.get_columns.side_effect = lambda table_name: (
            [
                {"name": "col_id", "type": "INTEGER", "nullable": False, "primary_key": 1, "default": None},
                {"name": "col_val", "type": "VARCHAR(255)", "nullable": True, "primary_key": 0, "default": None},
            ]
            if table_name == "generic_table_a"
            else [
                {"name": "col_ref_id", "type": "INTEGER", "nullable": False, "primary_key": 1, "default": None},
                {"name": "col_fk", "type": "INTEGER", "nullable": True, "primary_key": 0, "default": None},
            ]
        )

        mock_inspector.get_pk_constraint.side_effect = lambda table_name: (
            {"constrained_columns": ["col_id"]}
            if table_name == "generic_table_a"
            else {"constrained_columns": ["col_ref_id"]}
        )

        mock_inspector.get_foreign_keys.side_effect = lambda table_name: (
            []
            if table_name == "generic_table_a"
            else [
                {
                    "constrained_columns": ["col_fk"],
                    "referred_table": "generic_table_a",
                    "referred_columns": ["col_id"],
                }
            ]
        )

        mock_inspector.get_indexes.side_effect = lambda table_name: (
            [{"name": "idx_col_val", "column_names": ["col_val"], "unique": False}]
            if table_name == "generic_table_a"
            else []
        )

        dummy_engine = MagicMock()
        schema_info = db.inspect_database_schema(engine=dummy_engine)

        mock_inspect.assert_called_once_with(dummy_engine)
        self.assertEqual(schema_info["table_names"], ["generic_table_a", "generic_table_b"])

        # Check generic_table_a parsing
        tbl_a = schema_info["tables"]["generic_table_a"]
        self.assertEqual(len(tbl_a["columns"]), 2)
        self.assertTrue(tbl_a["columns"][0]["primary_key"])
        self.assertEqual(tbl_a["primary_keys"], ["col_id"])
        self.assertEqual(len(tbl_a["indexes"]), 1)

        # Check generic_table_b foreign key parsing
        tbl_b = schema_info["tables"]["generic_table_b"]
        self.assertEqual(len(tbl_b["foreign_keys"]), 1)
        self.assertEqual(tbl_b["foreign_keys"][0]["referred_table"], "generic_table_a")

    def test_get_schema_summary_text_formatting(self):
        """Verifies that schema summary text is formatted correctly for prompt context."""
        generic_schema = {
            "table_names": ["entity_one"],
            "tables": {
                "entity_one": {
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True},
                        {"name": "label", "type": "VARCHAR(50)", "primary_key": False},
                    ],
                    "foreign_keys": [
                        {
                            "constrained_columns": ["parent_id"],
                            "referred_table": "entity_zero",
                            "referred_columns": ["id"],
                        }
                    ],
                }
            },
        }

        summary = db.get_schema_summary_text(generic_schema)
        self.assertIn("Table `entity_one`", summary)
        self.assertIn("id (INTEGER [PK])", summary)
        self.assertIn("label (VARCHAR(50))", summary)
        self.assertIn("FOREIGN KEY (parent_id) REFERENCES entity_zero(id)", summary)

    def test_test_connection_success(self):
        """Verifies test_connection returns True when database executes ping query."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        is_ok, msg = db.test_connection(engine=mock_engine)
        self.assertTrue(is_ok)
        self.assertIn("successfully", msg)

    def test_test_connection_failure(self):
        """Verifies test_connection returns False and error message when connection fails."""
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Can't connect to MySQL server")

        is_ok, msg = db.test_connection(engine=mock_engine)
        self.assertFalse(is_ok)
    @patch("database.inspect")
    def test_get_discovered_tables(self, mock_inspect):
        """Verifies get_discovered_tables retrieves table names via inspector."""
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.get_table_names.return_value = ["table_1", "table_2"]

        dummy_engine = MagicMock()
        tables = db.get_discovered_tables(engine=dummy_engine)
        self.assertEqual(tables, ["table_1", "table_2"])

    @patch("database.inspect")
    def test_get_table_schema(self, mock_inspect):
        """Verifies get_table_schema extracts column and key metadata for a specific table."""
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.get_columns.return_value = [
            {"name": "field_id", "type": "BIGINT", "nullable": False, "primary_key": 1, "default": None}
        ]
        mock_inspector.get_pk_constraint.return_value = {"constrained_columns": ["field_id"]}
        mock_inspector.get_foreign_keys.return_value = []
        mock_inspector.get_indexes.return_value = []

        dummy_engine = MagicMock()
        table_meta = db.get_table_schema("table_1", engine=dummy_engine)
        self.assertEqual(len(table_meta["columns"]), 1)
        self.assertEqual(table_meta["primary_keys"], ["field_id"])


if __name__ == "__main__":
    unittest.main()
