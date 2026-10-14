"""
Database connection, diagnostics, and schema inspection module for Bank Data AI.

Provides reusable SQLAlchemy engine management, connection diagnostics,
and dynamic runtime schema discovery for the banking_risk_analytics database.
"""

from __future__ import annotations
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
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


def normalize_db_url(raw_url: str) -> Tuple[str, Dict[str, Any]]:
    """
    Normalizes database URL and configures connection arguments for PyMySQL / TLS.
    - Converts `mysql://` to `mysql+pymysql://` for SQLAlchemy compatibility.
    - Strips unsupported query parameters (e.g., `ssl-mode=REQUIRED`) so PyMySQL
      does not raise an unexpected argument error.
    - Automatically enables secure TLS/SSL connection for remote MySQL servers (e.g. Aiven)
      or when `ssl-mode` is requested.
    """
    if not raw_url:
        return "", {}

    url_str = raw_url.strip()
    if url_str.startswith("mysql://"):
        url_str = "mysql+pymysql://" + url_str[len("mysql://"):]

    connect_args: Dict[str, Any] = {}

    if url_str.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return url_str, connect_args

    try:
        url_obj = make_url(url_str)
    except Exception:
        return url_str, connect_args

    query_dict = dict(url_obj.query)

    # Clean out ssl-mode / ssl_mode from query string so PyMySQL dialect doesn't choke
    ssl_mode_val = query_dict.pop("ssl-mode", None) or query_dict.pop("ssl_mode", None)
    ssl_ca_val = query_dict.pop("ssl_ca", None) or query_dict.pop("ssl-ca", None)

    cleaned_url = url_obj._replace(query=query_dict).render_as_string(hide_password=False)

    host = url_obj.host or ""
    is_remote = host.lower() not in ("localhost", "127.0.0.1", "::1", "")

    connect_args["connect_timeout"] = 10

    # Configure SSL for remote hosts (e.g., Aiven, cloud MySQL) or when requested
    if is_remote or ssl_mode_val or "aivencloud" in host.lower():
        ssl_dict: Dict[str, Any] = {}
        if ssl_mode_val:
            ssl_dict["ssl_mode"] = ssl_mode_val
        connect_args["ssl"] = ssl_dict

    if ssl_ca_val:
        connect_args["ssl_ca"] = ssl_ca_val

    return cleaned_url, connect_args


def get_db_engine(db_url: Optional[str] = None, force_new: bool = False) -> Engine:
    """
    Creates or returns a cached SQLAlchemy Engine instance.
    Uses connection pooling, pre-ping, and connection timeouts to ensure stability.
    """
    global _engine
    target_raw = config.database_url if db_url is None else db_url

    if not target_raw:
        raise DatabaseConfigurationError(
            "DATABASE_URL is not configured and data/bank_data.db was not found. "
            "Please configure DATABASE_URL in your environment or provide data/bank_data.db."
        )

    target_url, extra_connect_args = normalize_db_url(target_raw)

    if _engine is None or force_new or (db_url and db_url != str(_engine.url)):
        connect_args: Dict[str, Any] = dict(extra_connect_args)

        if target_url.startswith("sqlite"):
            _engine = create_engine(
                target_url,
                connect_args=connect_args,
            )
        else:
            # MySQL / PyMySQL specific connection arguments
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
    host = "localhost"
    port = 3306
    db_name = config.database_name
    is_local = True

    try:
        eng = engine or get_db_engine()
        if eng.dialect.name == "sqlite":
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "Database connection established successfully (SQLite)."

        url_obj = getattr(eng, "url", None)
        if url_obj is not None and hasattr(url_obj, "host") and isinstance(url_obj.host, str):
            host = url_obj.host
            port = url_obj.port or 3306
            db_name = url_obj.database or config.database_name
            is_local = host.lower() in ("localhost", "127.0.0.1", "::1")

        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection established successfully."
    except DatabaseConfigurationError as cfg_err:
        return False, str(cfg_err)
    except ValueError as val_err:
        return False, str(val_err)
    except Exception as exc:
        err_msg = str(exc)
        # 1. Unknown MySQL server host (Error 2005 / DNS resolution failure)
        if "2005" in err_msg or ("unknown" in err_msg.lower() and "server host" in err_msg.lower()):
            if is_local:
                return (
                    False,
                    "Unable to connect to the banking database: Unknown MySQL server host. "
                    "Ensure host is 'localhost' or '127.0.0.1'."
                )
            return (
                False,
                f"Unable to connect to the banking database: Unknown MySQL server host '{host}' (Error 2005). "
                "DNS lookup failed. Please verify the hostname in your database provider dashboard "
                "(e.g., Aiven Console), ensure the service is active/running, and verify the URI has no typos or protocol prefixes."
            )
        # 2. Connection refused / Host unreachable (Error 2003 / getaddrinfo)
        elif "2003" in err_msg or "getaddrinfo failed" in err_msg.lower() or "connection refused" in err_msg.lower():
            if is_local:
                return (
                    False,
                    f"Unable to connect to the banking database. Check MySQL Server and configuration "
                    f"(ensure host is 'localhost' or '127.0.0.1' on port {port})."
                )
            return (
                False,
                f"Unable to connect to the banking database. Unable to reach MySQL server at {host}:{port} (Error 2003). "
                "Verify the remote host, port, and network firewall / IP access list."
            )
        # 3. Access denied / Auth failure (Error 1045)
        elif "1045" in err_msg or "access denied" in err_msg.lower():
            return False, f"Access denied. Please check your MySQL username and password for {host}."
        # 4. Unknown database (Error 1049)
        elif "1049" in err_msg or "unknown database" in err_msg.lower():
            return False, f"Database '{db_name}' not found on MySQL instance at {host}."
        # 5. SSL / TLS required transport (Error 3159)
        elif "3159" in err_msg or "secure transport" in err_msg.lower():
            return False, f"SSL/TLS connection error: The MySQL server at {host} requires secure transport. SSL has been enabled."
        # 6. MySQL server gone away (Error 2006)
        elif "2006" in err_msg or "gone away" in err_msg.lower():
            return False, "MySQL server has gone away. Connection timed out or server restarted."
        # 7. Timed out
        elif "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
            return False, f"Database connection to {host}:{port} timed out. Please check network and server load."

        # Generic error with password masked
        safe_msg = re.sub(r":[^:@]+@", ":******@", err_msg)
        return False, f"Unable to connect to the banking database: {safe_msg}"


def get_connection_diagnostics(engine: Optional[Engine] = None) -> Dict[str, Any]:
    """
    Retrieves rich diagnostic metadata about the current database connection,
    including latency, dialect, masked URL, database name, and pool status.
    """
    masked_url = config.get_masked_db_url()
    diagnostics: Dict[str, Any] = {
        "is_configured": config.is_database_configured,
        "database_name": config.database_name,
        "backend": config.database_backend,
        "masked_url": masked_url,
        "is_connected": False,
        "status_message": "",
        "latency_ms": None,
        "dialect": None,
        "table_count": 0,
    }

    if not config.is_database_configured and engine is None:
        diagnostics["status_message"] = "Database is not configured (missing DATABASE_URL and data/bank_data.db)."
        return diagnostics

    try:
        eng = engine or get_db_engine()
        diagnostics["dialect"] = eng.dialect.name
        diagnostics["backend"] = "SQLite" if eng.dialect.name == "sqlite" else "MySQL"
        start_time = time.perf_counter()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        diagnostics["is_connected"] = True
        diagnostics["latency_ms"] = elapsed_ms
        backend_name = diagnostics["backend"]
        diagnostics["status_message"] = f"Connected ({backend_name}, {elapsed_ms}ms latency)."

        try:
            inspector = inspect(eng)
            tables = inspector.get_table_names() or []
            diagnostics["table_count"] = len(tables)
        except Exception:
            diagnostics["table_count"] = 0
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
    Formats the dynamic schema dictionary into a structured representation
    with relational join pathways suitable for LLM prompt context injection.
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
            table_desc += f"\n  Explicit FKs: {'; '.join(fk_strs)}"
        lines.append(table_desc)

    # Add definitive, real-world relational join pathways to guide query construction
    relational_notes = (
        "### DEFINITIVE RELATIONAL JOIN PATHWAYS FOR `banking_risk_analytics`:\n"
        "1. Branch <-> Accounts: `branches.Branch_ID = accounts.Branch_ID` (100% populated in accounts)\n"
        "2. Branch <-> Customers: `branches b JOIN accounts a ON b.Branch_ID = a.Branch_ID JOIN customers c ON a.Customer_ID = c.Customer_ID`\n"
        "   - CRITICAL: `customers.Branch_ID` is NULL for all customer records. NEVER join `customers` directly to `branches` on `customers.Branch_ID`. ALWAYS link through `accounts`!\n"
        "3. Branch <-> Loans: `branches b JOIN accounts a ON b.Branch_ID = a.Branch_ID JOIN loans l ON a.Customer_ID = l.Customer_ID`\n"
        "   - Use `SUM(l.Loan_Amount)` for total loan balance / loan exposure by branch.\n"
        "4. Branch <-> Credit Cards: `branches b JOIN accounts a ON b.Branch_ID = a.Branch_ID JOIN credit_cards cc ON a.Customer_ID = cc.Customer_ID`\n"
        "   - Use `SUM(cc.Outstanding_Balance)` for total credit card balance by branch.\n"
        "5. Branch <-> Employees: `branches.Branch_ID = employees.Branch_ID` (Direct FK)\n"
        "   - Use `SUM(e.Salary)` for payroll by branch.\n"
        "6. Accounts <-> Transactions: `accounts.Account_ID = transactions.Account_ID` (Direct link)\n"
        "   - Use `SUM(t.Amount)` for transaction volume by account or branch.\n"
        "7. Customers <-> Loans: `customers.Customer_ID = loans.Customer_ID` (Direct link)\n"
        "8. Customers <-> Credit Cards: `customers.Customer_ID = credit_cards.Customer_ID` (Direct link)\n\n"
        "### ANALYTICAL JOIN GUIDELINES:\n"
        "- When aggregating master entities (e.g. branches), prefer `LEFT JOIN` (e.g. `branches b LEFT JOIN accounts a ON b.Branch_ID = a.Branch_ID LEFT JOIN loans l ON a.Customer_ID = l.Customer_ID`).\n"
        "- Use `COUNT(DISTINCT l.Loan_ID)` or `COUNT(DISTINCT a.Customer_ID)` to prevent duplicate count inflation in multi-table joins.\n"
        "- Metric columns: Loan balance = `loans.Loan_Amount`, Credit card balance = `credit_cards.Outstanding_Balance`, Transaction volume = `transactions.Amount`, Salary = `employees.Salary`, Customer income = `customers.Annual_Income`.\n"
        "- Column values & filters: In `transactions`, `Is_Fraud` is stored as 'Yes' or 'No' (always filter with `UPPER(Is_Fraud) IN ('YES', '1', 'TRUE')` or `Is_Fraud = 'Yes'`). Loan statuses are 'Active', 'Default', 'Closed'. Account statuses are 'Active', 'Inactive'."
    )

    return "\n\n".join(lines) + "\n\n" + relational_notes


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
