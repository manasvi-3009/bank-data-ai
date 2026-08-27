"""
Unit tests for database module, dynamic schema inspection, and connection handling.

Tests schema parsing, connection diagnostics, pooling, and sample fetching
using in-memory SQLite and mocks without modifying real database state.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, text

import database as db


class TestDatabaseModule(unittest.TestCase):
    def tearDown(self):
        db.dispose_engine()

    def test_get_db_engine_raises_on_missing_url(self):
        """Verifies get_db_engine raises DatabaseConfigurationError when DATABASE_URL is empty."""
        original = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATABASE_URL"] = ""
            with self.assertRaises(db.DatabaseConfigurationError):
                db.get_db_engine(db_url="", force_new=True)
        finally:
            if original is not None:
                os.environ["DATABASE_URL"] = original
            else:
                os.environ.pop("DATABASE_URL", None)

    def test_get_db_engine_caching_and_dispose(self):
        """Verifies engine is cached and dispose_engine cleans up."""
        eng1 = db.get_db_engine(db_url="sqlite:///:memory:", force_new=True)
        eng2 = db.get_db_engine()
        self.assertIs(eng1, eng2)

        db.dispose_engine()
        self.assertIsNone(db._engine)

    def test_test_connection_success(self):
        """Verifies test_connection returns True when database executes ping query."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        is_ok, msg = db.test_connection(engine=mock_engine)
        self.assertTrue(is_ok)
        self.assertIn("successfully", msg)

    def test_test_connection_failure_access_denied_1045(self):
        """Verifies clear error message on MySQL 1045 access denied."""
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("1045 (28000): Access denied for user 'root'@'localhost'")

        is_ok, msg = db.test_connection(engine=mock_engine)
        self.assertFalse(is_ok)
        self.assertIn("Access denied", msg)

    def test_test_connection_failure_host_unreachable_2003(self):
        """Verifies clear error message on MySQL 2003 host unreachable."""
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("2003 (HY000): Can't connect to MySQL server on 'localhost'")

        is_ok, msg = db.test_connection(engine=mock_engine)
        self.assertFalse(is_ok)
        self.assertIn("Cannot reach MySQL host", msg)

    def test_test_connection_failure_unknown_db_1049(self):
        """Verifies clear error message on MySQL 1049 unknown database."""
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("1049 (42000): Unknown database 'banking_risk_analytics'")

        is_ok, msg = db.test_connection(engine=mock_engine)
        self.assertFalse(is_ok)
        self.assertIn("Database 'banking_risk_analytics' not found", msg)

    def test_test_connection_failure_server_gone_away_2006(self):
        """Verifies clear error message on MySQL 2006 server gone away."""
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("2006: MySQL server has gone away")

        is_ok, msg = db.test_connection(engine=mock_engine)
        self.assertFalse(is_ok)
        self.assertIn("MySQL server has gone away", msg)

    def test_test_connection_failure_timeout(self):
        """Verifies clear error message on connection timeout."""
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("OperationalError: (pymysql.err.OperationalError) timed out")

        is_ok, msg = db.test_connection(engine=mock_engine)
        self.assertFalse(is_ok)
        self.assertIn("timed out", msg)

    def test_get_connection_diagnostics_success(self):
        """Verifies get_connection_diagnostics returns structured diagnostics with latency."""
        engine = create_engine("sqlite:///:memory:")
        diag = db.get_connection_diagnostics(engine=engine)
        self.assertTrue(diag["is_connected"])
        self.assertEqual(diag["dialect"], "sqlite")
        self.assertIsNotNone(diag["latency_ms"])
        self.assertIn("latency", diag["status_message"])

    def test_get_connection_diagnostics_unconfigured(self):
        """Verifies get_connection_diagnostics handles unconfigured state cleanly."""
        original = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATABASE_URL"] = ""
            diag = db.get_connection_diagnostics(engine=None)
            self.assertFalse(diag["is_connected"])
            self.assertIn("not configured", diag["status_message"])
        finally:
            if original is not None:
                os.environ["DATABASE_URL"] = original
            else:
                os.environ.pop("DATABASE_URL", None)

    @patch("database.inspect")
    def test_inspect_database_schema_dynamically_with_mock(self, mock_inspect):
        """
        Verifies dynamic schema inspection extracts tables, columns, types,
        primary keys, foreign keys, unique constraints, and indexes via inspector.
        """
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector

        mock_inspector.get_table_names.return_value = ["table_a", "table_b"]

        mock_inspector.get_columns.side_effect = lambda table_name: (
            [
                {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": 1, "default": None},
                {"name": "name", "type": "VARCHAR(255)", "nullable": True, "primary_key": 0, "default": None},
            ]
            if table_name == "table_a"
            else [
                {"name": "item_id", "type": "INTEGER", "nullable": False, "primary_key": 1, "default": None},
                {"name": "ref_id", "type": "INTEGER", "nullable": True, "primary_key": 0, "default": None},
            ]
        )

        mock_inspector.get_pk_constraint.side_effect = lambda table_name: (
            {"constrained_columns": ["id"]}
            if table_name == "table_a"
            else {"constrained_columns": ["item_id"]}
        )

        mock_inspector.get_foreign_keys.side_effect = lambda table_name: (
            []
            if table_name == "table_a"
            else [
                {
                    "name": "fk_item_ref",
                    "constrained_columns": ["ref_id"],
                    "referred_table": "table_a",
                    "referred_columns": ["id"],
                }
            ]
        )

        mock_inspector.get_indexes.side_effect = lambda table_name: (
            [{"name": "idx_name", "column_names": ["name"], "unique": False}]
            if table_name == "table_a"
            else []
        )

        mock_inspector.get_unique_constraints.side_effect = lambda table_name: []

        dummy_engine = MagicMock()
        schema_info = db.inspect_database_schema(engine=dummy_engine)

        mock_inspect.assert_called_once_with(dummy_engine)
        self.assertEqual(schema_info["table_names"], ["table_a", "table_b"])

        tbl_a = schema_info["tables"]["table_a"]
        self.assertEqual(len(tbl_a["columns"]), 2)
        self.assertTrue(tbl_a["columns"][0]["primary_key"])
        self.assertEqual(tbl_a["primary_keys"], ["id"])
        self.assertEqual(len(tbl_a["indexes"]), 1)

        tbl_b = schema_info["tables"]["table_b"]
        self.assertEqual(len(tbl_b["foreign_keys"]), 1)
        self.assertEqual(tbl_b["foreign_keys"][0]["referred_table"], "table_a")

    def test_inspect_database_schema_in_memory_sqlite(self):
        """Verifies end-to-end schema extraction on a relational in-memory SQLite database."""
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE sample_parent (
                        id INTEGER PRIMARY KEY,
                        code VARCHAR(20) NOT NULL
                    );
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE sample_child (
                        child_id INTEGER PRIMARY KEY,
                        parent_id INTEGER,
                        amount REAL,
                        FOREIGN KEY (parent_id) REFERENCES sample_parent(id)
                    );
                    """
                )
            )
            conn.commit()

        schema = db.inspect_database_schema(engine=engine)
        self.assertIn("sample_parent", schema["table_names"])
        self.assertIn("sample_child", schema["table_names"])

        parent_info = schema["tables"]["sample_parent"]
        self.assertEqual(parent_info["primary_keys"], ["id"])
        self.assertEqual(len(parent_info["columns"]), 2)

    def test_get_table_schema_with_none_safeties(self):
        """Verifies get_table_schema handles None responses gracefully without throwing errors."""
        mock_inspector = MagicMock()
        mock_inspector.get_columns.return_value = None
        mock_inspector.get_pk_constraint.return_value = None
        mock_inspector.get_foreign_keys.return_value = None
        mock_inspector.get_indexes.return_value = None
        mock_inspector.get_unique_constraints.side_effect = Exception("Not supported")

        res = db.get_table_schema("empty_table", inspector=mock_inspector)
        self.assertEqual(res["columns"], [])
        self.assertEqual(res["primary_keys"], [])
        self.assertEqual(res["foreign_keys"], [])
        self.assertEqual(res["indexes"], [])
        self.assertEqual(res["unique_constraints"], [])

    def test_get_schema_summary_text_formatting(self):
        """Verifies that schema summary text is formatted cleanly for prompt context."""
        generic_schema = {
            "table_names": ["entity_one"],
            "tables": {
                "entity_one": {
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True, "nullable": False},
                        {"name": "label", "type": "VARCHAR(50)", "primary_key": False, "nullable": True},
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
        self.assertIn("id (INTEGER [PK] NOT NULL)", summary)
        self.assertIn("label (VARCHAR(50))", summary)
        self.assertIn("FOREIGN KEY (parent_id) REFERENCES entity_zero(id)", summary)

    def test_get_schema_summary_text_empty(self):
        """Verifies get_schema_summary_text handles empty schema dictionary."""
        self.assertEqual(db.get_schema_summary_text({}), "No schema metadata available.")

    def test_get_table_sample_success(self):
        """Verifies get_table_sample safely fetches bounded rows from an existing table."""
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)"))
            conn.execute(text("INSERT INTO items VALUES (1, 'Widget A'), (2, 'Widget B'), (3, 'Widget C')"))
            conn.commit()

        samples = db.get_table_sample("items", limit=2, engine=engine)
        self.assertEqual(len(samples), 2)
        self.assertEqual(samples[0]["name"], "Widget A")

    def test_get_table_sample_invalid_table_raises(self):
        """Verifies get_table_sample rejects un-discovered table names."""
        engine = create_engine("sqlite:///:memory:")
        with self.assertRaises(ValueError):
            db.get_table_sample("non_existent_table", engine=engine)

    def test_custom_exception_hierarchy(self):
        """Verifies custom database exception inheritance."""
        self.assertTrue(issubclass(db.DatabaseConfigurationError, db.DatabaseError))
        self.assertTrue(issubclass(db.DatabaseConnectionError, db.DatabaseError))
        self.assertTrue(issubclass(db.SchemaInspectionError, db.DatabaseError))


if __name__ == "__main__":
    unittest.main()
