"""
Database connection, diagnostics, and schema inspection module for Bank Data AI.

Provides reusable SQLAlchemy engine management, connection diagnostics,
and dynamic runtime schema discovery for the banking_risk_analytics database.
"""

from __future__ import annotations
import time
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from config import config

# Global cache for the engine instance
_engine: Optional[Engine] = None


class DatabaseError(Exception):
    """Base exception for database operations in Bank Data AI."""
    pass


class DatabaseConfigurationError(DatabaseError):
    """Raised when database configuration or connection URL is invalid or missing."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when connecting to the database fails."""
    pass


class SchemaInspectionError(DatabaseError):
    """Raised when dynamic schema inspection encounters an error."""
    pass


def get_db_engine(db_url: Optional[str] = None, force_new: bool = False) -> Engine:
    """
    Creates or returns a cached SQLAlchemy Engine instance.
    Uses connection pooling, pre-ping, and connection timeouts to ensure stability.
    """
    global _engine
    target_url = db_url or config.database_url

    if not target_url:
        raise DatabaseConfigurationError(
            "DATABASE_URL is not configured. Please set it in your .env file "
            "(e.g., mysql+pymysql://user:pass@localhost:3306/banking_risk_analytics)."
        )

    if _engine is None or force_new or (db_url and db_url != str(_engine.url)):
        connect_args: Dict[str, Any] = {}

        if target_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            _engine = create_engine(
                target_url,
                connect_args=connect_args,
            )
        else:
            # MySQL / PyMySQL specific connection arguments
            connect_args["connect_timeout"] = 5
            _engine = create_engine(
                target_url,
                pool_pre_ping=True,
                pool_recycle=1800,
                pool_size=5,
                max_overflow=10,
                pool_timeout=15,
                connect_args=connect_args,
            )

    return _engine


def dispose_engine() -> None:
    """Disposes and cleans up the active SQLAlchemy engine and its connection pool."""
    global _engine
    if _engine is not None:
        try:
            _engine.dispose()
        finally:
            _engine = None


def test_connection(engine: Optional[Engine] = None) -> Tuple[bool, str]:
    """
    Performs a lightweight connection health check (SELECT 1).
    Returns (is_successful, user_friendly_status_message).
    """
    try:
        eng = engine or get_db_engine()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection established successfully."
    except DatabaseConfigurationError as cfg_err:
        return False, str(cfg_err)
    except ValueError as val_err:
        return False, str(val_err)
    except Exception as exc:
        err_msg = str(exc)
        # Provide user-friendly troubleshooting context without leaking secrets
        if "1045" in err_msg or "Access denied" in err_msg:
            return False, "Access denied. Please check your MySQL username and password in .env."
        elif "2003" in err_msg or "getaddrinfo failed" in err_msg or "Connection refused" in err_msg:
            return (
                False,
                "Cannot reach MySQL host. Ensure your host is set to 'localhost' or '127.0.0.1' "
                "(e.g. mysql+pymysql://root:password@localhost:3306/banking_risk_analytics) "
                "and that MySQL Server is running on port 3306."
            )
        elif "1049" in err_msg or "Unknown database" in err_msg:
            return False, "Database 'banking_risk_analytics' not found on this MySQL instance."
        elif "2006" in err_msg or "MySQL server has gone away" in err_msg:
            return False, "MySQL server has gone away. Connection timed out or server restarted."
        elif "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
            return False, "Database connection timed out. Please check network and server load."
        return False, f"Connection error: {err_msg}"


def get_connection_diagnostics(engine: Optional[Engine] = None) -> Dict[str, Any]:
    """
    Retrieves rich diagnostic metadata about the current database connection,
    including latency, dialect, masked URL, and pool status.
    """
    masked_url = config.get_masked_db_url()
    diagnostics: Dict[str, Any] = {
        "is_configured": config.is_database_configured,
        "masked_url": masked_url,
        "is_connected": False,
        "status_message": "",
        "latency_ms": None,
        "dialect": None,
    }

    if not config.is_database_configured and engine is None:
        diagnostics["status_message"] = "DATABASE_URL is not configured in .env."
        return diagnostics

    try:
        eng = engine or get_db_engine()
        diagnostics["dialect"] = eng.dialect.name
        start_time = time.perf_counter()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        diagnostics["is_connected"] = True
        diagnostics["latency_ms"] = elapsed_ms
        diagnostics["status_message"] = f"Connected ({elapsed_ms}ms latency)."
    except Exception as exc:
        is_ok, msg = test_connection(engine=eng if "eng" in locals() else None)
        diagnostics["is_connected"] = False
        diagnostics["status_message"] = msg

    return diagnostics


def get_discovered_tables(engine: Optional[Engine] = None) -> List[str]:
    """
    Dynamically fetches the sorted list of table names in the connected database.
    """
    try:
        eng = engine or get_db_engine()
        inspector = inspect(eng)
        table_names = inspector.get_table_names() or []
        return sorted(table_names)
    except Exception as exc:
        raise SchemaInspectionError(f"Failed to discover tables: {str(exc)}") from exc


def get_table_schema(
    table_name: str,
    engine: Optional[Engine] = None,
    inspector: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Dynamically retrieves column definitions, primary keys, foreign keys,
    unique constraints, and indexes for a specific table.
    """
    try:
        insp = inspector or inspect(engine or get_db_engine())

        columns_raw = insp.get_columns(table_name) or []
        pk_constraint = insp.get_pk_constraint(table_name) or {}
        primary_keys = set(pk_constraint.get("constrained_columns", []) or [])
        foreign_keys = insp.get_foreign_keys(table_name) or []
        indexes = insp.get_indexes(table_name) or []

        try:
            unique_constraints = insp.get_unique_constraints(table_name) or []
        except Exception:
            unique_constraints = []

        parsed_columns: List[Dict[str, Any]] = []
        for col in columns_raw:
            col_name = col.get("name", "")
            col_type = str(col.get("type", "UNKNOWN"))
            parsed_columns.append(
                {
                    "name": col_name,
                    "type": col_type,
                    "nullable": bool(col.get("nullable", True)),
                    "primary_key": col_name in primary_keys or bool(col.get("primary_key", 0)),
                    "default": str(col.get("default", "")) if col.get("default") is not None else None,
                    "autoincrement": bool(col.get("autoincrement", False)),
                    "comment": str(col.get("comment", "")) if col.get("comment") else None,
                }
            )

        return {
            "columns": parsed_columns,
            "primary_keys": list(primary_keys),
            "foreign_keys": [
                {
                    "name": fk.get("name", ""),
                    "constrained_columns": fk.get("constrained_columns", []) or [],
                    "referred_table": fk.get("referred_table", "") or "",
                    "referred_columns": fk.get("referred_columns", []) or [],
                }
                for fk in foreign_keys
            ],
            "indexes": [
                {
                    "name": idx.get("name", ""),
                    "column_names": idx.get("column_names", []) or [],
                    "unique": bool(idx.get("unique", False)),
                }
                for idx in indexes
            ],
            "unique_constraints": [
                {
                    "name": uc.get("name", ""),
                    "column_names": uc.get("column_names", []) or [],
                }
                for uc in unique_constraints
            ],
        }
    except Exception as exc:
        raise SchemaInspectionError(f"Failed to inspect table '{table_name}': {str(exc)}") from exc


def inspect_database_schema(engine: Optional[Engine] = None) -> Dict[str, Any]:
    """
    Dynamically inspects and extracts database schema metadata for all discovered tables.
    Does not hardcode table or column names; reads everything via SQLAlchemy inspector.

    Returns a structured dictionary:
    {
        "tables": {
            "table_name": {
                "columns": [...],
                "primary_keys": [...],
                "foreign_keys": [...],
                "indexes": [...],
                "unique_constraints": [...]
            }
        },
        "table_names": [str, ...]
    }
    """
    try:
        eng = engine or get_db_engine()
        insp = inspect(eng)
        table_names = sorted(insp.get_table_names() or [])
        schema_info: Dict[str, Any] = {
            "tables": {},
            "table_names": table_names,
        }

        for table_name in table_names:
            schema_info["tables"][table_name] = get_table_schema(table_name, inspector=insp)

        return schema_info
    except SchemaInspectionError:
        raise
    except Exception as exc:
        raise SchemaInspectionError(f"Database schema inspection error: {str(exc)}") from exc


def get_schema_summary_text(schema_info: Dict[str, Any]) -> str:
    """
    Formats the dynamic schema dictionary into a concise, structured representation
    suitable for LLM prompt context injection.
    """
    lines: List[str] = []
    tables = schema_info.get("tables", {})

    if not tables:
        return "No schema metadata available."

    for table_name in sorted(tables.keys()):
        details = tables[table_name]
        col_strs: List[str] = []
        for col in details.get("columns", []):
            pk_flag = " [PK]" if col.get("primary_key") else ""
            nullable_flag = " NOT NULL" if not col.get("nullable", True) else ""
            col_strs.append(f"{col['name']} ({col['type']}{pk_flag}{nullable_flag})")

        fk_strs: List[str] = []
        for fk in details.get("foreign_keys", []):
            cols = ", ".join(fk.get("constrained_columns", []))
            ref_cols = ", ".join(fk.get("referred_columns", []))
            ref_tbl = fk.get("referred_table", "")
            if cols and ref_tbl:
                fk_strs.append(f"FOREIGN KEY ({cols}) REFERENCES {ref_tbl}({ref_cols})")

        table_desc = f"Table `{table_name}`:\n  Columns: {', '.join(col_strs)}"
        if fk_strs:
            table_desc += f"\n  Relationships: {'; '.join(fk_strs)}"
        lines.append(table_desc)

    return "\n\n".join(lines)


def get_table_sample(
    table_name: str,
    limit: int = 3,
    engine: Optional[Engine] = None,
) -> List[Dict[str, Any]]:
    """
    Safely retrieves a small sample of rows from a specified table.
    Bounded by limit (max 10) to prevent memory overload.
    """
    safe_limit = max(1, min(limit, 10))
    eng = engine or get_db_engine()

    # Validate table_name against discovered tables to prevent injection
    discovered = get_discovered_tables(eng)
    if table_name not in discovered:
        raise ValueError(f"Table '{table_name}' does not exist in the connected database.")

    query = text(f"SELECT * FROM `{table_name}` LIMIT :lim")
    with eng.connect() as conn:
        result = conn.execute(query, {"lim": safe_limit})
        keys = list(result.keys())
        rows = [dict(zip(keys, row)) for row in result.fetchall()]
        return rows
