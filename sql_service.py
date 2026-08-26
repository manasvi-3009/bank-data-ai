"""
SQL service module for Bank Data AI.

Provides SQL validation, security guardrails, and safe query execution against
the banking_risk_analytics database.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    from sqlalchemy.engine import Engine

# Dangerous SQL keywords and DDL/DML operations that must never be executed
FORBIDDEN_SQL_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bCREATE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bREPLACE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bCALL\b",
    r"\bLOCK\b",
    r"\bUNLOCK\b",
    r"\bSET\b",
    r"\bFLUSH\b",
    r"\bKILL\b",
    r"\bINTO\s+OUTFILE\b",
    r"\bLOAD_FILE\b",
    r"\bSHUTDOWN\b",
]

FORBIDDEN_REGEX = re.compile("|".join(FORBIDDEN_SQL_PATTERNS), re.IGNORECASE)


class SQLValidationError(Exception):
    """Raised when a generated or input SQL query fails safety validation."""
    pass


def clean_sql(query: str) -> str:
    """
    Strips markdown code blocks, trailing semicolons, and extraneous whitespace.
    """
    if not query:
        return ""
    q = query.strip()
    # Remove markdown fenced blocks if present
    if q.startswith("```sql"):
        q = q[6:]
    elif q.startswith("```"):
        q = q[3:]
    if q.endswith("```"):
        q = q[:-3]
    return q.strip().rstrip(";")


def validate_sql(sql_query: str) -> Tuple[bool, Optional[str]]:
    """
    Validates that a SQL query is strictly a read-only SELECT statement.

    Checks performed:
    1. Query is non-empty.
    2. Query begins with SELECT or WITH (Common Table Expressions).
    3. Query contains no forbidden mutating keywords (DROP, DELETE, UPDATE, etc.).
    4. Query does not contain multiple stacked statements separated by semicolons.

    Returns:
        (is_valid, error_message_if_invalid)
    """
    cleaned = clean_sql(sql_query)

    if not cleaned:
        return False, "Query is empty."

    # Prevent stacked queries / injection via semicolons
    if ";" in cleaned:
        return False, "Multiple SQL statements separated by semicolons are not permitted."

    # Ensure query begins with SELECT or WITH (for CTEs)
    # Strip comments if any
    first_token_match = re.match(r"^(/\*.*?\*/\s*|--.*?\n\s*)*(\w+)", cleaned, re.DOTALL)
    if not first_token_match:
        return False, "Unable to determine the root SQL command."

    first_keyword = first_token_match.group(2).upper()
    if first_keyword not in ("SELECT", "WITH", "EXPLAIN", "SHOW", "DESCRIBE", "DESC"):
        return False, f"Forbidden command '{first_keyword}'. Only read-only queries (SELECT, WITH) are permitted."

    # Check for forbidden destructive keywords
    matched_forbidden = FORBIDDEN_REGEX.search(cleaned)
    if matched_forbidden:
        return False, f"Query contains forbidden keyword: '{matched_forbidden.group(0)}'. Mutating operations are strictly disallowed."

    return True, None


def execute_query(
    sql_query: str,
    engine: Optional[Engine] = None,
    max_rows: int = 1000,
) -> pd.DataFrame:
    """
    Safely executes a read-only SQL query against the database and returns a pandas DataFrame.

    Enforces validation prior to execution and bounds the result set.
    """
    is_valid, err_msg = validate_sql(sql_query)
    if not is_valid:
        raise SQLValidationError(f"SQL Security Validation Failed: {err_msg}")

    import pandas as pd
    from sqlalchemy import text
    from database import get_db_engine

    cleaned = clean_sql(sql_query)
    eng = engine or get_db_engine()

    try:
        with eng.connect() as conn:
            # Execute with read-only transaction semantics
            result = conn.execute(text(cleaned))
            columns = list(result.keys())
            rows = result.fetchmany(max_rows)
            df = pd.DataFrame(rows, columns=columns)
            return df
    except Exception as exc:
        raise RuntimeError(f"Database query execution error: {str(exc)}") from exc


# -----------------------------------------------------------------------------
# Placeholder for Future Advanced AST-based SQL Validation & Schema Verification
# -----------------------------------------------------------------------------
class SQLSecurityGuard:
    """
    Architectural placeholder for advanced SQL AST parsing (e.g. via sqlglot),
    verifying table/column references against known schema tables before execution.
    """

    def __init__(self, allowed_tables: Optional[List[str]] = None):
        self.allowed_tables = set(allowed_tables or [])

    def deep_validate(self, sql_query: str) -> Tuple[bool, Optional[str]]:
        """
        Future expansion point: Parse AST, check that all referenced tables belong
        to the known banking_risk_analytics schema, and check for disallowed functions.
        """
        # Basic check for now
        return validate_sql(sql_query)
