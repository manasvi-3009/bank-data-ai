"""
SQL service module for Bank Data AI.

Provides strict SQL validation, read-only security guardrails, and safe query execution
against the banking_risk_analytics database.
"""

from __future__ import annotations
import re
import time
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    from sqlalchemy.engine import Engine

# Mutating DDL, DML, administration, and privilege keywords strictly forbidden in analytical queries
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
    r"\bUSE\b",
    r"\bFLUSH\b",
    r"\bKILL\b",
    r"\bSHUTDOWN\b",
    r"\bINTO\s+OUTFILE\b",
    r"\bINTO\s+DUMPFILE\b",
    r"\bLOAD_FILE\b",
    r"\bBENCHMARK\b",
    r"\bSLEEP\b",
]

FORBIDDEN_REGEX = re.compile("|".join(FORBIDDEN_SQL_PATTERNS), re.IGNORECASE)

READ_ONLY_ROOT_COMMANDS = {"SELECT", "WITH", "EXPLAIN", "DESCRIBE", "DESC"}


class SQLValidationError(Exception):
    """Raised when a generated or input SQL query fails safety validation."""
    pass


class SQLExecutionError(Exception):
    """Raised when an error occurs during SQL query execution on the database."""
    pass


def clean_sql(query: str) -> str:
    """
    Strips markdown code fences, trailing semicolons, and extraneous whitespace.
    """
    if not query:
        return ""
    q = query.strip()
    # Remove markdown fenced blocks if present (case-insensitive)
    if q.lower().startswith("```sql"):
        q = q[6:]
    elif q.startswith("```"):
        q = q[3:]
    if q.endswith("```"):
        q = q[:-3]
    return q.strip().rstrip(";")


def _strip_comments_and_literals(sql: str) -> Tuple[str, List[str]]:
    """
    Strips comments and replaces quoted string literals with placeholders
    to safely check for unquoted semicolons and forbidden keyword tokens.
    """
    # 1. Strip C-style block comments: /* ... */
    no_block_comments = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    # 2. Strip line comments: -- ... and # ...
    no_line_comments = re.sub(r"--[^\r\n]*", " ", no_block_comments)
    no_comments = re.sub(r"#[^\r\n]*", " ", no_line_comments)

    # 3. Extract and mask string literals (single and double quotes)
    string_literals: List[str] = []

    def _mask_literal(match: re.Match[str]) -> str:
        string_literals.append(match.group(0))
        return f"__STR_LITERAL_{len(string_literals) - 1}__"

    # Match single-quoted strings (with escaped quotes) or double-quoted strings
    masked_sql = re.sub(r"'(?:''|\\'|[^'])*'|\"(?:\"\"|\\\"|[^\"])*\"", _mask_literal, no_comments)
    return masked_sql.strip(), string_literals


def validate_sql(sql_query: str) -> Tuple[bool, Optional[str]]:
    """
    Validates that a SQL query is strictly a read-only statement (SELECT or WITH).

    Checks performed:
    1. Query is non-empty.
    2. Comments and string literals are safely parsed.
    3. Multiple stacked statements separated by semicolons are strictly rejected.
    4. Root command begins with an authorized read-only keyword (SELECT or WITH).
    5. Query contains no forbidden mutating, DDL, DML, or administrative keywords.

    Returns:
        (is_valid, error_message_if_invalid)
    """
    cleaned = clean_sql(sql_query)

    if not cleaned:
        return False, "Query is empty."

    masked_sql, _ = _strip_comments_and_literals(cleaned)

    if not masked_sql:
        return False, "Query contains only comments or whitespace."

    # Prevent stacked queries / injection via semicolons outside string literals
    if ";" in masked_sql:
        return False, "Only read-only analytical queries are supported. Multiple SQL statements are not permitted."

    # Identify the first SQL keyword
    first_token_match = re.match(r"^(\w+)", masked_sql)
    if not first_token_match:
        return False, "Only read-only analytical queries are supported. Unable to determine the root SQL command."

    first_keyword = first_token_match.group(1).upper()
    if first_keyword not in READ_ONLY_ROOT_COMMANDS:
        return (
            False,
            f"Only read-only analytical queries are supported. Forbidden command: '{first_keyword}'."
        )

    # Check for forbidden destructive/mutating keywords in the unquoted query body
    matched_forbidden = FORBIDDEN_REGEX.search(masked_sql)
    if matched_forbidden:
        return (
            False,
            f"Only read-only analytical queries are supported. Mutating keyword '{matched_forbidden.group(0).upper()}' is strictly prohibited."
        )

    return True, None


def execute_query(
    sql_query: str,
    engine: Optional[Engine] = None,
    max_rows: int = 1000,
) -> pd.DataFrame:
    """
    Safely executes a read-only SQL query against the database and returns a pandas DataFrame.

    Enforces security validation prior to execution, bounds result size,
    and returns friendly errors without exposing raw stack traces or credentials.
    """
    is_valid, err_msg = validate_sql(sql_query)
    if not is_valid:
        raise SQLValidationError(err_msg or "Only read-only analytical queries are supported.")

    import pandas as pd
    from sqlalchemy import text
    from database import get_db_engine

    cleaned = clean_sql(sql_query)
    eng = engine or get_db_engine()

    try:
        with eng.connect() as conn:
            result = conn.execute(text(cleaned))
            columns = list(result.keys())
            rows = result.fetchmany(max_rows)
            df = pd.DataFrame(rows, columns=columns)
            return df
    except Exception as exc:
        err_str = str(exc)
        # Sanitize and produce clean user-facing error messages
        if "Table" in err_str and "doesn't exist" in err_str:
            match = re.search(r"Table '([^']+)' doesn't exist", err_str)
            tbl_name = match.group(1) if match else "specified"
            raise SQLExecutionError(f"Table '{tbl_name}' does not exist in the database.") from exc
        elif "Unknown column" in err_str:
            match = re.search(r"Unknown column '([^']+)'", err_str)
            col_name = match.group(1) if match else "specified"
            raise SQLExecutionError(f"Column '{col_name}' does not exist in the queried table.") from exc
        elif "syntax" in err_str.lower():
            raise SQLExecutionError("SQL syntax error encountered while executing the generated query.") from exc
        elif "timed out" in err_str.lower() or "timeout" in err_str.lower():
            raise SQLExecutionError("The query execution timed out. Please refine your query filters.") from exc
        else:
            # Clean generic execution error without leaking raw connection strings
            sanitized_err = re.sub(r"mysql\+pymysql://[^@]+@", "mysql+pymysql://***:***@", err_str)
            raise SQLExecutionError(f"Query execution failed: {sanitized_err}") from exc


def execute_query_with_metadata(
    sql_query: str,
    engine: Optional[Engine] = None,
    max_rows: int = 1000,
) -> Tuple[pd.DataFrame, int, float]:
    """
    Executes a read-only query and returns (DataFrame, row_count, execution_time_ms).
    """
    start_time = time.perf_counter()
    df = execute_query(sql_query, engine=engine, max_rows=max_rows)
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return df, len(df), elapsed_ms
