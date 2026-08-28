"""
Bank Data AI - Streamlit Application.

Interactive analytical assistant for querying and analyzing the banking_risk_analytics database.
"""

import streamlit as st
import pandas as pd
from config import config
from database import test_connection, inspect_database_schema, get_discovered_tables
from sql_service import validate_sql

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


def render_chat_placeholder():
    """Renders the chat interface placeholder for upcoming NL-to-SQL functionality."""
    st.subheader("💬 Ask Questions About Banking Data")

    st.markdown(
        """
        <div style="background-color: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
            <p style="margin: 0; color: #475569;">
                <strong>NL-to-SQL Pipeline Ready for Activation:</strong> Once full LLM integration is enabled, you can ask questions in plain English.
                The system will generate safe, read-only SQL, query <code>banking_risk_analytics</code>, and display interactive charts and tables.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Example question pills
    st.markdown("**Suggested Questions (Upcoming):**")
    col1, col2 = st.columns(2)
    with col1:
        st.info("💡 *'What is the total outstanding loan balance grouped by branch?'*")
        st.info("💡 *'Show top 10 accounts with the highest total transaction volume this month.'*")
    with col2:
        st.info("💡 *'List customers holding credit cards with balances above 80% credit limit.'*")
        st.info("💡 *'What is the average transaction amount per account type?'*")

    # Chat Input Placeholder
    user_query = st.chat_input(
        placeholder="Ask a question about customers, accounts, loans, or transactions (NL-to-SQL pipeline placeholder)...",
        disabled=False,
    )

    if user_query:
        with st.chat_message("user"):
            st.write(user_query)

        with st.chat_message("assistant"):
            st.info(
                f"Received question: **\"{user_query}\"**\n\n"
                "⚙️ *NL-to-SQL translation pipeline is staged for the next phase. "
                "The system will translate this into safe, validated SQL and execute it against `banking_risk_analytics`.*"
            )


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
        render_chat_placeholder()


if __name__ == "__main__":
    main()
