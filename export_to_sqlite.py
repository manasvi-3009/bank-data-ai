"""
export_to_sqlite.py — copies all tables (structure + data) from your local MySQL
database into a single SQLite file: data/bank_data.db

That one file is committed to GitHub so the public demo can run without any
hosted database. Your MySQL data is only read, never modified.

Run (local MySQL must be running and DATABASE_URL set in .env):
    python export_to_sqlite.py
"""
import os
import sys
from datetime import date, datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from database import get_db_engine, get_discovered_tables

OUTPUT_FILE = os.path.join("data", "bank_data.db")


def sqlite_type(mysql_type) -> str:
    """Maps a reflected MySQL column type to a simple SQLite type."""
    t = str(mysql_type).upper()
    if "INT" in t or "BOOL" in t:
        return "INTEGER"
    if any(k in t for k in ("DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL")):
        return "REAL"
    return "TEXT"  # VARCHAR, CHAR, TEXT, DATE, DATETIME, TIMESTAMP, ...


def build_create_table(inspector, table: str) -> str:
    """Builds a CREATE TABLE statement that keeps primary keys and foreign keys."""
    columns = inspector.get_columns(table)
    pk_cols = inspector.get_pk_constraint(table).get("constrained_columns") or []
    parts = []

    for col in columns:
        line = f'"{col["name"]}" {sqlite_type(col["type"])}'
        if not col.get("nullable", True):
            line += " NOT NULL"
        parts.append(line)

    if pk_cols:
        parts.append("PRIMARY KEY (" + ", ".join(f'"{c}"' for c in pk_cols) + ")")

    for fk in inspector.get_foreign_keys(table):
        local = ", ".join(f'"{c}"' for c in fk["constrained_columns"])
        remote = ", ".join(f'"{c}"' for c in fk["referred_columns"])
        parts.append(f'FOREIGN KEY ({local}) REFERENCES "{fk["referred_table"]}" ({remote})')

    return f'CREATE TABLE "{table}" (\n  ' + ",\n  ".join(parts) + "\n)"


def iso_value(v):
    """Converts a date/datetime object to an ISO text value (or None)."""
    if v is None or (not isinstance(v, (date, datetime)) and pd.isna(v)):
        return None
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    return v


def normalise_dates(df: pd.DataFrame) -> pd.DataFrame:
    """SQLite has no date type, so store dates as clean ISO text (YYYY-MM-DD)."""
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_datetime64_any_dtype(s):
            non_null = s.dropna()
            midnight_only = bool((non_null.dt.normalize() == non_null).all())
            fmt = "%Y-%m-%d" if midnight_only else "%Y-%m-%d %H:%M:%S"
            df[col] = s.dt.strftime(fmt).astype(object).where(s.notna(), None)
        elif pd.api.types.is_timedelta64_dtype(s):
            df[col] = s.astype(str).where(s.notna(), None)
        elif s.dtype == object and s.notna().any():
            first = s.dropna().iloc[0]
            if isinstance(first, (date, datetime)):
                df[col] = s.map(iso_value)
    return df


def main():
    os.makedirs("data", exist_ok=True)
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    mysql_engine = get_db_engine()
    mysql_inspector = inspect(mysql_engine)
    sqlite_engine = create_engine(f"sqlite:///{OUTPUT_FILE}")

    tables = get_discovered_tables(mysql_engine)
    print(f"Found {len(tables)} tables in MySQL: {tables}\n")

    for table in tables:
        with sqlite_engine.begin() as conn:
            conn.exec_driver_sql(build_create_table(mysql_inspector, table))
        df = normalise_dates(pd.read_sql_table(table, con=mysql_engine))
        df.to_sql(table, con=sqlite_engine, if_exists="append", index=False)
        print(f"✅ {table}: {len(df)} rows copied")

    print("\nVerification (MySQL rows vs SQLite rows):")
    all_ok = True
    with mysql_engine.connect() as m_conn, sqlite_engine.connect() as s_conn:
        for table in tables:
            m_count = m_conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
            s_count = s_conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            ok = m_count == s_count
            all_ok = all_ok and ok
            print(f"  {'✅' if ok else '❌'} {table}: MySQL={m_count}  SQLite={s_count}")

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    if all_ok:
        print(f"\nDone. '{OUTPUT_FILE}' is ready ({size_kb:.0f} KB). Commit this file to GitHub.")
    else:
        print("\nSome row counts do not match. Do not use this file yet; send me this output.")


if __name__ == "__main__":
    main()
