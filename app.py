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
from visualization import render_visualization

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
        margin-bottom: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Session State Initialization & Schema Caching
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []


def get_cached_schema() -> Tuple[Dict[str, Any], str]:
    """Retrieves or caches dynamic schema metadata for session efficiency."""
    if "cached_schema_data" not in st.session_state or "cached_schema_context" not in st.session_state:
        schema_data = inspect_database_schema()
        schema_context = get_schema_summary_text(schema_data)
        st.session_state.cached_schema_data = schema_data
        st.session_state.cached_schema_context = schema_context
    return st.session_state.cached_schema_data, st.session_state.cached_schema_context


def clear_schema_cache() -> None:
    """Invalidates session schema cache."""
    st.session_state.pop("cached_schema_data", None)
    st.session_state.pop("cached_schema_context", None)


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
                '<span class="status-badge status-badge-blue">🤖 Active</span>',
                unsafe_allow_html=True,
            )
            st.caption(f"**Provider:** `{type(llm_service.provider).__name__}`")
            st.caption(f"**Model:** `{config.llm_model}`")
        else:
            st.markdown(
                '<span class="status-badge status-badge-amber">🟡 Offline Mock Mode</span>',
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
            clear_schema_cache()
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
                schema_data, _ = get_cached_schema()

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
                _, schema_context = get_cached_schema()
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
                preview_text = (
                    df.head(10).to_string(index=False)
                    if df is not None and not df.empty
                    else "Empty Result Set (0 rows)"
                )
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

    # Display Chat History with Clean Visual Hierarchy
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

            # 1. Natural-Language Executive Summary / Finding
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

            # 2. Generated Read-Only SQL (Expandable Section)
            with st.expander("🔍 View Generated Read-Only SQL", expanded=False):
                st.code(msg["sql"], language="sql")

            # 3. Formatted Result Table with Metadata Badge
            latency = msg.get("latency_ms", 0.0)
            rows = msg.get("row_count", 0)
            st.markdown(
                f'<span class="metric-pill">⏱️ {latency} ms</span>'
                f'<span class="metric-pill">📊 {rows} rows returned</span>',
                unsafe_allow_html=True,
            )

            df = msg.get("data")
            if df is not None and not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
                # 4. Intelligent Visualization (if meaningful)
                render_visualization(df)
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