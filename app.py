"""
Bank Data AI - Streamlit Application.

Interactive analytical assistant for querying and analyzing the banking_risk_analytics database.
"""

import streamlit as st
import pandas as pd
from config import config
from database import test_connection, inspect_database_schema, get_discovered_tables, get_schema_summary_text
from sql_service import validate_sql, execute_query, SQLValidationError
from llm_service import llm_service, LLMError

# Page configuration
st.set_page_config(
    page_title="Bank Data AI | Banking Risk Analytics",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .status-card {
        padding: 1rem 1.25rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .status-connected {
        background-color: #ECFDF5;
        border: 1px solid #A7F3D0;
        color: #065F46;
    }
    .status-disconnected {
        background-color: #FEF2F2;
        border: 1px solid #FECACA;
        color: #991B1B;
    }
    .status-warning {
        background-color: #FFFBEB;
        border: 1px solid #FDE68A;
        color: #92400E;
    }
    .table-badge {
        display: inline-block;
        padding: 4px 10px;
        margin: 3px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        background: #F1F5F9;
        color: #334155;
        border: 1px solid #E2E8F0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_sidebar():
    """Renders the application sidebar with connection status and diagnostics."""
    with st.sidebar:
        st.header("🏦 System Diagnostics")

        # Database Connection Check
        if not config.is_database_configured:
            st.markdown("### Database: **Not Connected**")
            st.error("⚠️ `DATABASE_URL` is not configured.")
            st.info(
                "Configure your `.env` file with your MySQL credentials:\n\n"
                "```env\n"
                "DATABASE_URL=mysql+pymysql://root:password@localhost:3306/banking_risk_analytics\n"
                "```"
            )
        else:
            is_connected, msg = test_connection()
            if is_connected:
                st.markdown("### Database: **🟢 Connected**")
                st.caption(f"**Target:** `{config.get_masked_db_url()}`")
                st.caption("Status: Active & Verified")
            else:
                st.markdown("### Database: **🔴 Not Connected**")
                st.error(f"**Status:** {msg}")
                st.caption(f"**Configured Host:** `{config.get_masked_db_url()}`")

        st.divider()

        # LLM Engine Status
        st.subheader("🤖 LLM Engine")
        if config.is_llm_configured:
            st.success("🟢 **LLM API Key Configured**")
            st.caption(f"Model: `{config.llm_model}`")
        else:
            st.warning("🟡 **LLM API Key Missing**")
            st.caption("Set `LLM_API_KEY` in `.env` to enable natural language querying.")

        st.divider()

        # Known Banking Tables Reference
        st.subheader("📚 Expected Tables")
        expected_tables = [
            "accounts",
            "branches",
            "credit_cards",
            "customers",
            "employees",
            "loans",
            "transactions",
        ]
        for tbl in expected_tables:
            st.markdown(f"- `{tbl}`")

        st.divider()
        st.caption("Bank Data AI — Initial Foundation v0.1.0")


def render_database_status_card(is_connected: bool, connection_msg: str):
    """Displays prominent top status banner."""
    col1, col2 = st.columns([4, 1])

    with col1:
        if not config.is_database_configured:
            st.markdown(
                """
                <div class="status-card status-warning">
                    <strong>⚠️ Database: Not Connected</strong> — <code>DATABASE_URL</code> is missing from environment.
                    Please configure your <code>.env</code> file with valid MySQL credentials.
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif is_connected:
            st.markdown(
                f"""
                <div class="status-card status-connected">
                    <strong>🟢 Database: Connected</strong> — Successfully connected to <code>banking_risk_analytics</code> ({config.get_masked_db_url()})
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="status-card status-disconnected">
                    <strong>🔴 Database: Not Connected</strong> — {connection_msg}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col2:
        if st.button("🔄 Test Connection", use_container_width=True):
            st.rerun()


def render_schema_explorer(is_connected: bool):
    """Renders the discovered database schema metadata and expandable details."""
    st.subheader("📊 Dynamic Schema Discovery")

    if not is_connected:
        st.info(
            "🔒 **Schema inspection unavailable while disconnected.**\n\n"
            "Connect to the MySQL server hosting `banking_risk_analytics` to inspect real discovered tables, columns, data types, and foreign key relations."
        )
        return

    try:
        with st.spinner("Dynamically inspecting database schema via SQLAlchemy Inspector..."):
            schema_data = inspect_database_schema()

        table_names = schema_data.get("table_names", [])

        if not table_names:
            st.warning("Connected to database, but no tables were discovered in `banking_risk_analytics`.")
            return

        # Summary Metrics
        total_cols = sum(len(tbl.get("columns", [])) for tbl in schema_data.get("tables", {}).values())
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Discovered Tables", len(table_names))
        col_m2.metric("Total Discovered Columns", total_cols)

        # Discovered Table Badges
        st.markdown("**Discovered Tables:**")
        badges_html = " ".join([f'<span class="table-badge">📋 {tbl}</span>' for tbl in table_names])
        st.markdown(f"<div>{badges_html}</div>", unsafe_allow_html=True)
        st.markdown("")

        # Expandable Schema Details per table
        st.markdown("### 🔍 Expandable Schema Details")
        for table_name in table_names:
            tbl_info = schema_data["tables"].get(table_name, {})
            cols = tbl_info.get("columns", [])
            fks = tbl_info.get("foreign_keys", [])
            pks = tbl_info.get("primary_keys", [])

            expander_title = f"Table: **`{table_name}`** ({len(cols)} columns, {len(pks)} PK, {len(fks)} FK)"
            with st.expander(expander_title, expanded=False):
                if cols:
                    df_cols = pd.DataFrame(cols)
                    df_cols = df_cols.rename(
                        columns={
                            "name": "Column Name",
                            "type": "Data Type",
                            "nullable": "Nullable",
                            "primary_key": "Primary Key",
                            "default": "Default Value",
                        }
                    )
                    st.dataframe(df_cols, use_container_width=True, hide_index=True)

                if fks:
                    st.markdown("**Foreign Key Relationships:**")
                    for fk in fks:
                        from_cols = ", ".join(fk.get("constrained_columns", []))
                        to_cols = ", ".join(fk.get("referred_columns", []))
                        ref_tbl = fk.get("referred_table", "")
                        st.markdown(f"- `{from_cols}` ➔ `{ref_tbl}({to_cols})`")

    except Exception as exc:
        st.error(f"Failed to inspect database schema: {str(exc)}")


def render_chat_interface(is_connected: bool):
    """Renders the working natural-language-to-SQL chat interface."""
    st.subheader("💬 Ask Questions About Banking Data")

    if not is_connected:
        st.info("🔒 Connect to the database first to enable natural language querying.")
        return

    if not config.is_llm_configured:
        st.warning(
            "🟡 **LLM API Key Missing.** Set `LLM_API_KEY` in your `.env` file to enable "
            "natural language querying. Falling back to a limited offline mode."
        )

    # Suggested question buttons (clickable — populate and run the question)
    st.markdown("**Suggested Questions:**")
    suggestions = [
        "What is the total outstanding loan balance grouped by branch?",
        "Show top 10 accounts with the highest total transaction volume.",
        "List customers holding credit cards with balances above 80% of credit limit.",
        "What is the average transaction amount per account type?",
    ]
    col1, col2 = st.columns(2)
    clicked_question = None
    for i, suggestion in enumerate(suggestions):
        target_col = col1 if i % 2 == 0 else col2
        if target_col.button(f"💡 {suggestion}", key=f"suggestion_{i}", use_container_width=True):
            clicked_question = suggestion

    # Free-text input
    typed_question = st.chat_input(
        placeholder="Ask a question about customers, accounts, loans, or transactions..."
    )

    user_query = clicked_question or typed_question

    if user_query:
        with st.chat_message("user"):
            st.write(user_query)

        with st.chat_message("assistant"):
            # Step 1 — get schema context for the LLM
            try:
                schema_info = inspect_database_schema()
                schema_context = get_schema_summary_text(schema_info)
            except Exception as exc:
                st.error(f"Could not read database schema: {exc}")
                return

            # Step 2 — ask the LLM to generate SQL
            try:
                with st.spinner("Translating your question into SQL..."):
                    sql_query = llm_service.generate_sql(user_query, schema_context)
            except LLMError as exc:
                st.error(f"LLM error: {exc}")
                return

            st.markdown("**Generated SQL:**")
            st.code(sql_query, language="sql")

            # Step 3 — validate + execute (execute_query already validates internally)
            try:
                with st.spinner("Running query..."):
                    result_df = execute_query(sql_query)
            except SQLValidationError as exc:
                st.error(f"🚫 Query blocked for safety: {exc}")
                return
            except RuntimeError as exc:
                st.error(f"Query execution failed: {exc}")
                return

            if result_df.empty:
                st.info("The query ran successfully but returned no rows.")
                return

            st.markdown("**Result:**")
            st.dataframe(result_df, use_container_width=True, hide_index=True)

            # Auto-chart when the result looks chartable (1 label col + 1 numeric col)
            if result_df.shape[1] == 2 and result_df.shape[0] > 1:
                numeric_col = result_df.select_dtypes(include="number").columns
                if len(numeric_col) == 1:
                    label_col = [c for c in result_df.columns if c != numeric_col[0]][0]
                    st.bar_chart(result_df.set_index(label_col)[numeric_col[0]])

            # Step 4 — optional executive summary from the LLM
            if config.is_llm_configured:
                try:
                    with st.spinner("Generating summary..."):
                        preview = result_df.head(10).to_string(index=False)
                        summary = llm_service.explain_results(
                            user_query, sql_query, preview, len(result_df)
                        )
                    st.markdown("**Executive Summary:**")
                    st.info(summary)
                except LLMError:
                    pass  # summary is a nice-to-have, don't block on failure


def main():
    st.markdown('<div class="main-title">Bank Data AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Natural-language analytics and intelligence for <code>banking_risk_analytics</code> database</div>',
        unsafe_allow_html=True,
    )

    render_sidebar()

    # Determine connection status
    is_connected = False
    connection_msg = ""
    if config.is_database_configured:
        is_connected, connection_msg = test_connection()

    # Main Status Banner
    render_database_status_card(is_connected, connection_msg)

    st.markdown("---")

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        render_schema_explorer(is_connected)

    with col_right:
        render_chat_interface(is_connected)


if __name__ == "__main__":
    main()