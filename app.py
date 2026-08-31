"""
Bank Data AI - Streamlit Application.

Portfolio-Grade Natural-Language Banking Analytics Console.
Enables natural-language questions over MySQL banking_risk_analytics database,
generates safe read-only SQL, executes queries, and presents executive summaries & visual analytics.
"""

from __future__ import annotations
import time
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import streamlit as st

from config import config
from database import (
    test_connection,
    inspect_database_schema,
    get_discovered_tables,
    get_schema_summary_text,
    get_connection_diagnostics,
    get_table_sample,
    DatabaseError,
    DatabaseConfigurationError,
)
from sql_service import (
    validate_sql,
    execute_query_with_metadata,
    SQLValidationError,
    SQLExecutionError,
)
from llm_service import llm_service, LLMError, LLMConfigurationError

# -----------------------------------------------------------------------------
# Streamlit Page Setup & Custom Modern Financial CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Bank Data AI | Natural-Language Banking Analytics",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Modern Financial Analytics Styling */
    .brand-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 0.2rem;
    }
    .brand-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #1E3A8A 0%, #0284C7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .brand-subtitle {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
        font-weight: 400;
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        gap: 6px;
    }
    .status-badge-green {
        background-color: #ECFDF5;
        color: #065F46;
        border: 1px solid #A7F3D0;
    }
    .status-badge-red {
        background-color: #FEF2F2;
        color: #991B1B;
        border: 1px solid #FECACA;
    }
    .status-badge-blue {
        background-color: #EFF6FF;
        color: #1E40AF;
        border: 1px solid #BFDBFE;
    }
    .status-badge-amber {
        background-color: #FFFBEB;
        color: #92400E;
        border: 1px solid #FDE68A;
    }
    .table-chip {
        display: inline-block;
        padding: 4px 10px;
        margin: 3px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        background: #F8FAFC;
        color: #334155;
        border: 1px solid #E2E8F0;
        font-family: monospace;
    }
    .summary-card {
        padding: 1.1rem 1.3rem;
        border-radius: 10px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #0284C7;
        margin-bottom: 1rem;
        color: #1E293B;
    }
    .metric-pill {
        display: inline-block;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        background: #E2E8F0;
        color: #475569;
        margin-right: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []


# -----------------------------------------------------------------------------
# Intelligent Visualization Heuristic Engine
# -----------------------------------------------------------------------------
def render_intelligent_visualization(df: pd.DataFrame) -> None:
    """
    Analyzes DataFrame structure and automatically renders the most appropriate chart:
    - 1 Row with 1-4 numeric values -> Metric KPIs
    - 1 Categorical column + 1 Numeric column -> Bar Chart
    - 1 Temporal/Date column + 1 Numeric column -> Line/Area Chart
    - 2 Numeric columns (multi-row) -> Scatter Chart
    - Non-visualizable or complex tables -> Tabular display only
    """
    if df is None or df.empty:
        return

    num_rows, num_cols = df.shape

    # 1. Metric Card case: Single row with small set of numeric metrics
    if num_rows == 1:
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        valid_numeric_cols = [c for c in numeric_cols if df[c].notna().any()]
        if 1 <= len(valid_numeric_cols) <= 4:
            st.markdown("**📈 Key Metric Overview**")
            cols = st.columns(len(valid_numeric_cols))
            for i, col_name in enumerate(valid_numeric_cols):
                val = df[col_name].iloc[0]
                if pd.notna(val):
                    formatted_val = (
                        f"{val:,.2f}"
                        if isinstance(val, (float, int)) and not float(val).is_integer()
                        else f"{val:,}" if isinstance(val, int) else str(val)
                    )
                else:
                    formatted_val = "N/A"
                label = col_name.replace("_", " ").title()
                cols[i].metric(label=label, value=formatted_val)
            return

    # Identify column data types
    date_cols = [
        c
        for c in df.columns
        if "date" in c.lower()
        or "time" in c.lower()
        or pd.api.types.is_datetime64_any_dtype(df[c])
    ]
    numeric_cols = [c for c in df.select_dtypes(include=["number"]).columns.tolist() if df[c].notna().any()]
    categorical_cols = [c for c in df.columns if c not in numeric_cols and c not in date_cols]

    # 2. Time-series / Date Trend case: Date column + Numeric column
    if date_cols and numeric_cols and num_rows > 1:
        date_col = date_cols[0]
        num_col = numeric_cols[0]
        chart_df = df[[date_col, num_col]].dropna().sort_values(by=date_col)
        if not chart_df.empty:
            st.markdown(f"**📈 Trend Analysis ({num_col.replace('_', ' ')} over {date_col.replace('_', ' ')})**")
            st.line_chart(chart_df.set_index(date_col))
            return

    # 3. Categorical Comparison: 1 Categorical + 1 Numeric column
    if categorical_cols and numeric_cols and 1 < num_rows <= 30:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        chart_df = df[[cat_col, num_col]].dropna().sort_values(by=num_col, ascending=False).set_index(cat_col)
        if not chart_df.empty:
            st.markdown(f"**📊 Category Breakdown ({num_col.replace('_', ' ')} by {cat_col.replace('_', ' ')})**")
            st.bar_chart(chart_df)
            return

    # 4. Scatter Plot: 2 Numeric columns with multiple rows
    if len(numeric_cols) >= 2 and num_rows > 5 and not categorical_cols:
        x_col = numeric_cols[0]
        y_col = numeric_cols[1]
        chart_df = df[[x_col, y_col]].dropna()
        if len(chart_df) > 3:
            st.markdown(f"**🔍 Correlation Plot ({y_col.replace('_', ' ')} vs {x_col.replace('_', ' ')})**")
            st.scatter_chart(chart_df, x=x_col, y=y_col)
            return


# -----------------------------------------------------------------------------
# Sidebar: System Diagnostics & Connection State
# -----------------------------------------------------------------------------
def render_sidebar() -> Tuple[bool, Dict[str, Any]]:
    """Renders the application sidebar containing diagnostics, database status, and LLM state."""
    with st.sidebar:
        st.markdown("### 🏦 System Diagnostics")

        diagnostics = get_connection_diagnostics()
        is_connected = diagnostics.get("is_connected", False)

        # Database Status Card
        st.markdown("**Database Connection:**")
        if not config.is_database_configured:
            st.markdown(
                '<span class="status-badge status-badge-red">🔴 Not Configured</span>',
                unsafe_allow_html=True,
            )
            st.caption("`DATABASE_URL` is missing from environment.")
        elif is_connected:
            latency = diagnostics.get("latency_ms", "—")
            st.markdown(
                f'<span class="status-badge status-badge-green">🟢 Connected ({latency}ms)</span>',
                unsafe_allow_html=True,
            )
            st.caption(f"**Database:** `{diagnostics.get('database_name')}`")
            st.caption(f"**Host:** `{config.get_masked_db_url()}`")
        else:
            st.markdown(
                '<span class="status-badge status-badge-red">🔴 Disconnected</span>',
                unsafe_allow_html=True,
            )
            st.caption(f"**Status:** {diagnostics.get('status_message')}")

        st.divider()

        # LLM Engine Status
        st.markdown("**AI / LLM Engine:**")
        if config.is_llm_configured:
            st.markdown(
                f'<span class="status-badge status-badge-blue">🤖 Active</span>',
                unsafe_allow_html=True,
            )
            st.caption(f"**Provider:** `{type(llm_service.provider).__name__}`")
            st.caption(f"**Model:** `{config.llm_model}`")
        else:
            st.markdown(
                f'<span class="status-badge status-badge-amber">🟡 Offline Mock Mode</span>',
                unsafe_allow_html=True,
            )
            st.caption("Configured with schema-grounded fallback responses.")

        st.divider()

        # Security & Guardrails Status
        st.markdown("**Security Guardrails:**")
        st.markdown(
            '<span class="status-badge status-badge-green">🛡️ Read-Only SQL</span>',
            unsafe_allow_html=True,
        )
        st.caption("Mutations (INSERT/UPDATE/DELETE/DROP/ALTER/etc.) are blocked.")

        st.divider()

        # Schema & Table Summary
        table_count = diagnostics.get("table_count", 0)
        st.markdown(f"**Discovered Tables ({table_count}):**")
        if is_connected:
            try:
                tables = get_discovered_tables()
                for tbl in tables:
                    st.markdown(f"- `{tbl}`")
            except Exception:
                st.caption("Unable to load table list.")
        else:
            st.caption("Connect database to view discovered tables.")

        st.divider()

        # Quick Actions
        if st.button("🔄 Refresh System Status", use_container_width=True):
            st.rerun()

        if st.session_state.messages:
            if st.button("🗑️ Clear Chat History", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

        st.caption("Bank Data AI — Production v1.0.0")

    return is_connected, diagnostics


# -----------------------------------------------------------------------------
# Dynamic Schema Explorer Component
# -----------------------------------------------------------------------------
def render_schema_explorer(is_connected: bool) -> None:
    """Renders dynamic database schema metadata, column definitions, and foreign keys."""
    with st.expander("📚 Dynamic Database Schema Explorer", expanded=False):
        if not is_connected:
            st.info(
                "🔒 **Database disconnected.** Connect MySQL hosting `banking_risk_analytics` "
                "to inspect real tables, columns, and foreign key relations dynamically."
            )
            return

        try:
            with st.spinner("Dynamically inspecting database schema..."):
                schema_data = inspect_database_schema()

            table_names = schema_data.get("table_names", [])
            if not table_names:
                st.warning("Connected to database, but no tables were discovered in `banking_risk_analytics`.")
                return

            # Summary Metrics
            total_cols = sum(len(tbl.get("columns", [])) for tbl in schema_data.get("tables", {}).values())
            m1, m2, m3 = st.columns(3)
            m1.metric("Discovered Tables", len(table_names))
            m2.metric("Total Schema Columns", total_cols)
            m3.metric("Access Mode", "Strict Read-Only")

            st.markdown("**Discovered Banking Tables:**")
            chips = " ".join([f'<span class="table-chip">📋 {t}</span>' for t in table_names])
            st.markdown(chips, unsafe_allow_html=True)
            st.markdown("")

            selected_table = st.selectbox("Select table to inspect structure:", options=table_names)
            if selected_table:
                tbl_info = schema_data["tables"].get(selected_table, {})
                cols = tbl_info.get("columns", [])
                fks = tbl_info.get("foreign_keys", [])
                pks = tbl_info.get("primary_keys", [])

                col_details_col, sample_col = st.columns([3, 2])

                with col_details_col:
                    st.markdown(f"**Structure for `{selected_table}`:**")
                    if cols:
                        df_cols = pd.DataFrame(cols)
                        display_cols = df_cols[["name", "type", "nullable", "primary_key"]].rename(
                            columns={
                                "name": "Column Name",
                                "type": "Data Type",
                                "nullable": "Nullable",
                                "primary_key": "PK",
                            }
                        )
                        st.dataframe(display_cols, use_container_width=True, hide_index=True)

                    if fks:
                        st.markdown("**Foreign Key Constraints:**")
                        for fk in fks:
                            constrained = ", ".join(fk.get("constrained_columns", []))
                            ref_tbl = fk.get("referred_table", "")
                            ref_cols = ", ".join(fk.get("referred_columns", []))
                            st.caption(f"🔗 `{constrained}` ➔ `{ref_tbl}({ref_cols})`")

                with sample_col:
                    st.markdown(f"**Sample Data Preview (`{selected_table}`):**")
                    try:
                        sample_rows = get_table_sample(selected_table, limit=3)
                        if sample_rows:
                            df_sample = pd.DataFrame(sample_rows)
                            st.dataframe(df_sample, use_container_width=True, hide_index=True)
                        else:
                            st.caption("No sample rows present.")
                    except Exception as exc:
                        st.caption(f"Sample preview unavailable: {exc}")

        except Exception as exc:
            st.error(f"Failed to inspect database schema dynamically: {str(exc)}")


# -----------------------------------------------------------------------------
# Suggested Questions Component
# -----------------------------------------------------------------------------
def render_suggested_questions(is_connected: bool) -> Optional[str]:
    """Displays curated, schema-grounded example questions."""
    st.markdown("**💡 Suggested Questions (Click to Analyze):**")

    suggestions = [
        "Which branch has the highest number of customers?",
        "What is the total loan amount and loan count by branch region?",
        "Which customers have the highest credit card utilization rate?",
        "Show all transactions flagged as fraud with their reasons.",
        "What is the total transaction volume by transaction type?",
        "What is the average and total employee salary by branch?",
    ]

    cols = st.columns(3)
    clicked_question = None

    for i, suggestion in enumerate(suggestions):
        col = cols[i % 3]
        if col.button(suggestion, key=f"sugg_btn_{i}", use_container_width=True, disabled=not is_connected):
            clicked_question = suggestion

    return clicked_question


# -----------------------------------------------------------------------------
# Query Execution Pipeline
# -----------------------------------------------------------------------------
def process_user_question(question: str) -> None:
    """Executes the full NL-to-SQL pipeline with stepped status messages and session recording."""
    status_placeholder = st.empty()

    # Step 1: Inspect Schema Context
    schema_context = ""
    with status_placeholder.container():
        with st.spinner("🔍 Inspecting database schema dynamically..."):
            try:
                schema_data = inspect_database_schema()
                schema_context = get_schema_summary_text(schema_data)
            except Exception as exc:
                st.session_state.messages.append({
                    "question": question,
                    "error": f"Unable to inspect database schema: {exc}",
                })
                status_placeholder.empty()
                return

    # Step 2: Generate SQL via LLM
    generated_sql = ""
    with status_placeholder.container():
        with st.spinner("🤖 Translating question into read-only SQL..."):
            try:
                generated_sql = llm_service.generate_sql(question, schema_context)
            except LLMConfigurationError:
                st.session_state.messages.append({
                    "question": question,
                    "error": "The AI service is unavailable. Check the configured API key/model.",
                })
                status_placeholder.empty()
                return
            except LLMError as exc:
                st.session_state.messages.append({
                    "question": question,
                    "error": f"The AI service is unavailable: {exc}",
                })
                status_placeholder.empty()
                return
            except Exception:
                st.session_state.messages.append({
                    "question": question,
                    "error": "I couldn't generate a valid analytical query for that request.",
                })
                status_placeholder.empty()
                return

    # Step 3: Validate SQL Security
    with status_placeholder.container():
        with st.spinner("🛡️ Validating SQL security & read-only constraints..."):
            is_valid, validation_err = validate_sql(generated_sql)
            if not is_valid:
                st.session_state.messages.append({
                    "question": question,
                    "sql": generated_sql,
                    "error": f"🚫 Security Validation: {validation_err or 'Only read-only analytical queries are supported.'}",
                })
                status_placeholder.empty()
                return

    # Step 4: Execute Query
    df: Optional[pd.DataFrame] = None
    row_count = 0
    exec_time_ms = 0.0
    with status_placeholder.container():
        with st.spinner("⚡ Executing query on banking database..."):
            try:
                df, row_count, exec_time_ms = execute_query_with_metadata(generated_sql)
            except SQLValidationError as exc:
                st.session_state.messages.append({
                    "question": question,
                    "sql": generated_sql,
                    "error": f"🚫 Security Validation: {exc}",
                })
                status_placeholder.empty()
                return
            except SQLExecutionError as exc:
                st.session_state.messages.append({
                    "question": question,
                    "sql": generated_sql,
                    "error": f"Database query error: {exc}",
                })
                status_placeholder.empty()
                return
            except Exception:
                st.session_state.messages.append({
                    "question": question,
                    "sql": generated_sql,
                    "error": "Unable to connect to the banking database. Check MySQL Server and configuration.",
                })
                status_placeholder.empty()
                return

    # Step 5: Formulate Executive Summary
    summary_text = ""
    with status_placeholder.container():
        with st.spinner("📝 Preparing executive analytics summary..."):
            try:
                preview_text = df.head(10).to_string(index=False) if df is not None and not df.empty else "Empty Result Set (0 rows)"
                summary_text = llm_service.explain_results(
                    question,
                    generated_sql,
                    preview_text,
                    row_count,
                )
            except Exception:
                summary_text = f"Query executed successfully in {exec_time_ms}ms, returning {row_count} records."

    # Clear intermediate spinners
    status_placeholder.empty()

    # Append complete result record to session state
    st.session_state.messages.append({
        "question": question,
        "sql": generated_sql,
        "data": df,
        "row_count": row_count,
        "latency_ms": exec_time_ms,
        "summary": summary_text,
    })


# -----------------------------------------------------------------------------
# Main Application Layout
# -----------------------------------------------------------------------------
def main():
    # Render Sidebar Diagnostics
    is_connected, diagnostics = render_sidebar()

    # Header & Subtitle
    st.markdown(
        """
        <div class="brand-header">
            <h1 class="brand-title">Bank Data AI</h1>
        </div>
        <div class="brand-subtitle">Ask questions about your banking data in natural language.</div>
        """,
        unsafe_allow_html=True,
    )

    # Top Status Alert Card
    if not config.is_database_configured:
        st.warning(
            "⚠️ **Database is not configured.** Please configure `DATABASE_URL` in `.env` "
            "(e.g., `mysql+pymysql://root:password@localhost:3306/banking_risk_analytics`)."
        )
    elif not is_connected:
        st.error(
            f"🔴 **Database connection offline:** {diagnostics.get('status_message', 'Unable to reach MySQL server')}. "
            "Please ensure MySQL is running on port 3306."
        )

    # Collapsible Dynamic Schema Explorer
    render_schema_explorer(is_connected)

    st.markdown("---")

    # Suggested Questions Bar
    clicked_question = render_suggested_questions(is_connected)

    st.markdown("### 💬 Analytical Conversation")

    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message("user"):
            st.write(msg["question"])

        with st.chat_message("assistant"):
            if "error" in msg and msg["error"]:
                st.error(msg["error"])
                if "sql" in msg and msg["sql"]:
                    with st.expander("🔍 View Attempted SQL", expanded=False):
                        st.code(msg["sql"], language="sql")
                continue

            # Natural-Language Executive Summary
            summary = msg.get("summary", "")
            if summary:
                st.markdown(
                    f"""
                    <div class="summary-card">
                        <strong>📌 Executive Finding:</strong><br/>
                        {summary}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Metadata Badge & Generated SQL
            latency = msg.get("latency_ms", 0.0)
            rows = msg.get("row_count", 0)
            st.markdown(
                f'<span class="metric-pill">⏱️ {latency} ms</span>'
                f'<span class="metric-pill">📊 {rows} rows</span>',
                unsafe_allow_html=True,
            )

            with st.expander("🔍 View Generated Read-Only SQL", expanded=False):
                st.code(msg["sql"], language="sql")

            # Result Data Table
            df = msg.get("data")
            if df is not None and not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
                # Automatic Visualization
                render_intelligent_visualization(df)
            elif df is not None and df.empty:
                st.info("ℹ️ No matching records were found.")

    # Free-text Chat Input
    user_input = st.chat_input(
        placeholder="Ask a question about branches, loans, accounts, transactions, customers, or cards...",
        disabled=not is_connected,
    )

    # Trigger processing if question received
    question_to_run = clicked_question or user_input
    if question_to_run:
        process_user_question(question_to_run)
        st.rerun()


if __name__ == "__main__":
    main()