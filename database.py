"""
Database connection and schema inspection module for Bank Data AI.

Provides reusable SQLAlchemy engine management, connection diagnostics,
and dynamic schema discovery for the existing banking_risk_analytics database.
"""

from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from config import config

# Global cache for the engine instance
_engine: Optional[Engine] = None


def get_db_engine(db_url: Optional[str] = None, force_new: bool = False) -> Engine:
    """
    Creates or returns a cached SQLAlchemy Engine instance.
    Uses connection pooling and pre-ping to ensure stable connections.
    """
    global _engine
    target_url = db_url or config.database_url

    if not target_url:
        raise ValueError(
            "DATABASE_URL is not configured. Please set it in your .env file "
            "(e.g., mysql+pymysql://user:pass@localhost:3306/banking_risk_analytics)."
        )

    if _engine is None or force_new or (db_url and db_url != str(_engine.url)):
        # Pool settings suitable for web app workloads
        connect_args = {}
        if target_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        _engine = create_engine(
            target_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args=connect_args,
        )

    return _engine


def test_connection(engine: Optional[Engine] = None) -> Tuple[bool, str]:
    """
    Performs a lightweight connection check (SELECT 1).
    Returns (is_successful, status_message).
    """
    try:
        eng = engine or get_db_engine()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection established successfully."
    except ValueError as val_err:
        return False, str(val_err)
    except Exception as exc:
        return False, f"Connection failed: {str(exc)}"


def inspect_database_schema(engine: Optional[Engine] = None) -> Dict[str, Any]:
    """
    Dynamically inspects and extracts database schema metadata from the connected database.
    Does not hardcode table or column names; reads everything via SQLAlchemy inspector.

    Returns a structured dictionary:
    {
        "tables": {
            "table_name": {
                "columns": [
                    {"name": str, "type": str, "nullable": bool, "primary_key": bool, "default": str},
                    ...
                ],
                "primary_keys": [str, ...],
                "foreign_keys": [
                    {"constrained_columns": [...], "referred_table": str, "referred_columns": [...]},
                    ...
                ],
                "indexes": [...]
            }
        },
        "table_names": [str, ...]
    }
    """
    eng = engine or get_db_engine()
    inspector = inspect(eng)

    table_names = inspector.get_table_names()
    schema_info: Dict[str, Any] = {
        "tables": {},
        "table_names": table_names,
    }

    for table_name in table_names:
        columns_raw = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        primary_keys = set(pk_constraint.get("constrained_columns", []))
        foreign_keys = inspector.get_foreign_keys(table_name)
        indexes = inspector.get_indexes(table_name)

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
                }
            )

        schema_info["tables"][table_name] = {
            "columns": parsed_columns,
            "primary_keys": list(primary_keys),
            "foreign_keys": [
                {
                    "constrained_columns": fk.get("constrained_columns", []),
                    "referred_table": fk.get("referred_table", ""),
                    "referred_columns": fk.get("referred_columns", []),
                }
                for fk in foreign_keys
            ],
            "indexes": [
                {
                    "name": idx.get("name", ""),
                    "column_names": idx.get("column_names", []),
                    "unique": bool(idx.get("unique", False)),
                }
                for idx in indexes
            ],
        }

    return schema_info


def get_schema_summary_text(schema_info: Dict[str, Any]) -> str:
    """
    Formats the dynamic schema dictionary into a concise text representation
    suitable for LLM prompt context injection.
    """
    lines: List[str] = []
    for table_name, details in schema_info.get("tables", {}).items():
        col_strs = []
        for col in details.get("columns", []):
            pk_flag = " [PK]" if col["primary_key"] else ""
            col_strs.append(f"{col['name']} ({col['type']}{pk_flag})")

        fk_strs = []
        for fk in details.get("foreign_keys", []):
            cols = ", ".join(fk["constrained_columns"])
            ref_cols = ", ".join(fk["referred_columns"])
            fk_strs.append(f"FOREIGN KEY ({cols}) REFERENCES {fk['referred_table']}({ref_cols})")

        table_desc = f"Table `{table_name}`:\n  Columns: {', '.join(col_strs)}"
        if fk_strs:
            table_desc += f"\n  Relationships: {'; '.join(fk_strs)}"
        lines.append(table_desc)

    return "\n\n".join(lines)
