"""
load_csv_data.py — loads CSV files from ./data/ into the matching MySQL tables.

- Tries several encodings automatically.
- Only inserts CSV columns that actually exist in the target table.
- Skips a table if it already has rows (to avoid duplicate-key errors on re-runs).
- Auto-generates a value for any required (NOT NULL, no default) column that's
  missing from the CSV, derived from the table's primary key column.

Run with: python load_csv_data.py
"""
import os
import pandas as pd
from sqlalchemy import inspect, text
from database import get_db_engine, get_discovered_tables

DATA_FOLDER = "data"
ENCODINGS_TO_TRY = ["utf-8", "utf-8-sig", "utf-16", "latin1", "cp1252"]


def read_csv_robust(filepath):
    last_error = None
    for enc in ENCODINGS_TO_TRY:
        try:
            df = pd.read_csv(filepath, encoding=enc)
            if df.shape[1] > 0:
                return df, enc
        except Exception as exc:
            last_error = exc
            continue
    raise ValueError(f"Could not parse file with any known encoding. Last error: {last_error}")


def get_table_row_count(engine, table_name):
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
        return result.scalar()


def main():
    if not os.path.isdir(DATA_FOLDER):
        print(f"Folder '{DATA_FOLDER}' not found. Create it and put your CSV files inside.")
        return

    engine = get_db_engine()
    inspector = inspect(engine)
    existing_tables = set(get_discovered_tables(engine))
    print(f"Tables found in database: {sorted(existing_tables)}\n")

    csv_files = [f for f in os.listdir(DATA_FOLDER) if f.lower().endswith(".csv")]
    if not csv_files:
        print(f"No CSV files found in '{DATA_FOLDER}'.")
        return

    for filename in csv_files:
        table_name = os.path.splitext(filename)[0].strip().lower().replace(" ", "_")
        filepath = os.path.join(DATA_FOLDER, filename)

        matched_table = next((t for t in existing_tables if t.lower() == table_name), None)
        if not matched_table:
            print(f"⚠️  SKIPPED '{filename}' — no matching table named '{table_name}' found in database.")
            continue

        existing_rows = get_table_row_count(engine, matched_table)
        if existing_rows > 0:
            print(f"⏭️  SKIPPED '{matched_table}' — already has {existing_rows} rows.")
            continue

        try:
            df, used_encoding = read_csv_robust(filepath)
        except Exception as exc:
            print(f"❌ FAILED reading '{filename}': {exc}")
            continue

        table_col_info = inspector.get_columns(matched_table)
        table_columns = {col["name"] for col in table_col_info}
        csv_columns = set(df.columns)
        matching_columns = [c for c in df.columns if c in table_columns]
        dropped_columns = csv_columns - table_columns
        missing_columns = table_columns - csv_columns

        if not matching_columns:
            print(f"❌ FAILED '{filename}' — none of the CSV columns match table '{matched_table}' columns.")
            continue

        df_filtered = df[matching_columns].copy()

        # Auto-fill required (NOT NULL, no default) columns missing from the CSV,
        # derived from the table's primary key column so values stay unique.
        pk_constraint = inspector.get_pk_constraint(matched_table)
        pk_cols = pk_constraint.get("constrained_columns", [])
        pk_col = pk_cols[0] if pk_cols else None
        auto_filled = []

        for col in table_col_info:
            col_name = col["name"]
            if col_name in missing_columns and not col.get("nullable", True) and col.get("default") is None and not col.get("autoincrement", False):
                if pk_col and pk_col in df.columns:
                    prefix = "".join([w[0] for w in col_name.split("_")]).upper()
                    df_filtered[col_name] = df[pk_col].apply(lambda v: f"{prefix}{v}")
                    auto_filled.append(col_name)
                else:
                    df_filtered[col_name] = [f"{col_name}_{i+1}" for i in range(len(df_filtered))]
                    auto_filled.append(col_name)

        try:
            df_filtered.to_sql(matched_table, con=engine, if_exists="append", index=False)
            print(f"✅ Loaded {len(df_filtered)} rows from '{filename}' (encoding: {used_encoding}) into table '{matched_table}'.")
            if dropped_columns:
                print(f"   ℹ️  Ignored CSV columns not in table: {sorted(dropped_columns)}")
            if auto_filled:
                print(f"   ℹ️  Auto-generated values for required columns missing from CSV: {sorted(auto_filled)}")
        except Exception as exc:
            print(f"❌ FAILED loading '{filename}' into '{matched_table}': {exc}")

    print("\nDone. Refresh your Streamlit app to see updated row counts.")


if __name__ == "__main__":
    main()