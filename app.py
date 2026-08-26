"""
Bank Data AI - Streamlit Application.

Interactive analytical assistant for querying and analyzing the banking_risk_analytics database.
"""

import streamlit as st
import pandas as pd
from config import config
from database import test_connection, inspect_database_schema
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
        padding: 1rem;
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
    .metric-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        background: #EEF2F6;
        color: #334155;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_sidebar():
    """Renders the application sidebar with connection status and settings."""
    with st.sidebar:
        st.header("🏦 System Diagnostics")

        # Database Configuration Check
        if not config.is_database_configured:
            st.error("⚠️ **DATABASE_URL Not Configured**")
            st.info(
                "To connect to your MySQL database, create a `.env` file in the project root:\n\n"
                "```bash\n"
                "DATABASE_URL=mysql+pymysql://<user>:<password>@localhost:3306/banking_risk_analytics\n"
                "```"
            )
        else:
            is_connected, msg = test_connection()
            if is_connected:
                st.success("🟢 **MySQL Database Connected**")
                st.caption(f"**Target:** `{config.get_masked_db_url()}`")
            else:
                st.error("🔴 **Connection Failed**")
                st.caption(f"Error: {msg}")
                st.warning("Please check your MySQL server status and credentials in `.env`.")

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

        # Project Info
        st.subheader("📚 Known Tables")
        known_tables = [
            "accounts",
            "branches",
            "credit_cards",
            "customers",
            "employees",
            "loans",
            "transactions",
        ]
        for tbl in known_tables:
            st.markdown(f"- `{tbl}`")

        st.divider()
        st.caption("Bank Data AI — Initial Foundation v0.1.0")


def render_database_status(is_connected: bool, connection_msg: str):
    """Displays connection overview badge."""
    col1, col2 = st.columns([3, 1])

    with col1:
        if not config.is_database_configured:
            st.markdown(
                """
                <div class="status-card status-warning">
                    <strong>⚠️ Database connection pending:</strong> <code>DATABASE_URL</code> is not set in environment.
                    Please copy <code>.env.example</code> to <code>.env</code> and provide your MySQL credentials.
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif is_connected:
            st.markdown(
                f"""
                <div class="status-card status-connected">
                    <strong>🟢 Connected to MySQL:</strong> <code>banking_risk_analytics</code> ({config.get_masked_db_url()})
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="status-card status-disconnected">
                    <strong>🔴 Database connection error:</strong> {connection_msg}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col2:
        if st.button("🔄 Refresh Connection", use_container_width=True):
            st.rerun()


def render_schema_explorer(is_connected: bool):
    """Renders the discovered database schema metadata."""
    st.subheader("📊 Dynamic Schema Discovery")

    if not is_connected:
        st.info("Connect to the `banking_risk_analytics` database to view discovered tables, columns, and relationships.")
        return

    try:
        with st.spinner("Inspecting database schema..."):
            schema_data = inspect_database_schema()

        table_names = schema_data.get("table_names", [])

        if not table_names:
            st.warning("Connected to database, but no tables were discovered.")
            return

        st.caption(f"Discovered **{len(table_names)} tables** dynamically from MySQL:")

        # Display tabs for each discovered table
        tabs = st.tabs([f"📋 {tbl}" for tbl in table_names])

        for idx, table_name in enumerate(table_names):
            with tabs[idx]:
                tbl_info = schema_data["tables"].get(table_name, {})
                cols = tbl_info.get("columns", [])

                if cols:
                    df_cols = pd.DataFrame(cols)
                    # Rename columns for clarity in UI
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

                # Show foreign keys if present
                fks = tbl_info.get("foreign_keys", [])
                if fks:
                    st.markdown("**Foreign Key Constraints:**")
                    for fk in fks:
                        from_cols = ", ".join(fk["constrained_columns"])
                        to_cols = ", ".join(fk["referred_columns"])
                        st.markdown(f"- `{from_cols}` ➔ `{fk['referred_table']}({to_cols})`")

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

    # Main Sections
    render_database_status(is_connected, connection_msg)

    st.markdown("---")

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        render_schema_explorer(is_connected)

    with col_right:
        render_chat_placeholder()


if __name__ == "__main__":
    main()
