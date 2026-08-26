# Bank Data AI 🏦

> **Portfolio-Grade "Chat with Bank Data" Analytical Assistant**  
> Enables natural-language questions over an existing MySQL `banking_risk_analytics` database, generates safe read-only SQL queries, and surfaces executive-ready data tables and visual analytics.

---

## 1. Project Purpose

Financial institutions maintain complex relational data across branches, customer accounts, credit lines, loans, and high-frequency transactions. Business analysts and risk managers frequently require ad-hoc analytical queries that require deep SQL knowledge.

**Bank Data AI** bridges this gap:
- Translates natural language questions into dialect-accurate, read-only MySQL queries.
- Dynamically discovers the relational database schema without hardcoding schemas.
- Enforces strict security guardrails against destructive operations and data exfiltration.
- Executes verified queries and presents tabular and visual analytics through an interactive Streamlit UI.

---

## 2. Existing Database: `banking_risk_analytics`

This project is built directly on top of the existing **`banking_risk_analytics`** MySQL database.
No synthetic or mock banking data is created or modified.

### 3. Known Schema Tables
The target database contains the following 7 core banking tables:
- **`accounts`**: Account balances, account types (Checking, Savings, Money Market), opening dates, and customer linkage.
- **`branches`**: Branch locations, regional identifiers, and branch managers.
- **`credit_cards`**: Card limits, current balances, APR, and card status.
- **`customers`**: Demographics, KYC information, credit scores, and risk classifications.
- **`employees`**: Bank staff, roles, departments, and assigned branch branches.
- **`loans`**: Loan amounts, terms, interest rates, status (Active, Delinquent, Paid), and collateral.
- **`transactions`**: High-frequency transaction ledgers (deposits, withdrawals, transfers, merchant payments, timestamps).

---

## 4. Architecture

```
bank-data-ai/
├── app.py                  # Streamlit application UI (Diagnostics, Schema Explorer, Chat)
├── config.py               # Safe environment configuration & credential masking
├── database.py             # SQLAlchemy engine factory & dynamic schema inspector
├── sql_service.py          # SQL security guardrails & safe query executor
├── llm_service.py          # LLM provider abstraction & prompt coordinator
├── requirements.txt        # Python dependency manifest
├── .env.example            # Template for environment configuration
├── .gitignore              # Ignores .env, virtual environments, caches
├── README.md               # Project documentation and setup guide
└── tests/                  # Automated test suite
    ├── test_config.py      # Tests for configuration and masking
    ├── test_database.py    # Tests for dynamic schema discovery and engine
    └── test_sql_service.py # Tests for read-only validation and security rules
```

### Component Breakdown
1. **Config Layer (`config.py`)**: Safely parses `DATABASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. Never leaks plaintext credentials in strings or UI components.
2. **Database Engine & Inspection (`database.py`)**: Uses SQLAlchemy connection pooling (`pool_pre_ping=True`) and the `inspect` API to dynamically read table schemas, column types, constraints, and relationships at runtime.
3. **Security & SQL Layer (`sql_service.py`)**: Enforces read-only validation, blocks all DDL/DML mutation keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, etc.), rejects stacked semicolon injection, and bounds result sets.
4. **LLM Abstraction (`llm_service.py`)**: Provides an extensible interface for natural language to SQL translation and analytical summary generation.
5. **Presentation Layer (`app.py`)**: Streamlit-based analytical console featuring real-time connection health checks, interactive schema exploration, and chat prompt workflows.

---

## 5. Installation

### Prerequisites
- Python 3.11+
- MySQL Server (with `banking_risk_analytics` loaded)
- Git

### Clone & Setup Virtual Environment
```bash
# Clone the repository
git clone <repo-url> bank-data-ai
cd bank-data-ai

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (cmd):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 6. Environment Setup

Copy `.env.example` to create your local `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your actual MySQL credentials and LLM settings:

```env
# Database Connection (MySQL)
DATABASE_URL=mysql+pymysql://root:your_mysql_password@localhost:3306/banking_risk_analytics

# LLM Configuration
LLM_API_KEY=your_llm_api_key_here
LLM_MODEL=gpt-4o-mini
```

> **Security Note:** The `.env` file is excluded from Git via `.gitignore`. Never commit credentials to version control.

---

## 7. How to Connect Local MySQL

1. Verify that your MySQL server is running:
   ```bash
   # Windows PowerShell / Services
   Get-Service -Name "MySQL*"
   ```

2. Confirm that the `banking_risk_analytics` database exists:
   ```sql
   SHOW DATABASES LIKE 'banking_risk_analytics';
   ```

3. Configure user permissions (read-only user recommended for production):
   ```sql
   CREATE USER IF NOT EXISTS 'bank_analyst'@'localhost' IDENTIFIED BY 'StrongPassword123!';
   GRANT SELECT ON banking_risk_analytics.* TO 'bank_analyst'@'localhost';
   FLUSH PRIVILEGES;
   ```

4. Update your `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL=mysql+pymysql://bank_analyst:StrongPassword123!@localhost:3306/banking_risk_analytics
   ```

---

## 8. Security Considerations

- **Strict Read-Only Enforcement**: Queries are validated using `sql_service.validate_sql()` before execution. All mutating commands (`DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`, `REPLACE`, `EXEC`) are blocked.
- **SQL Injection Prevention**: Semicolon-separated stacked queries are blocked. Queries are executed through SQLAlchemy parameter-safe wrappers.
- **Credential Isolation**: Database passwords and API keys are loaded via environment variables and masked in the UI and logging layers (`get_masked_db_url()`).
- **Result Set Limiting**: Default query results are capped (e.g., `LIMIT 1000`) to prevent memory exhaustion and Denial of Service.

---

## 9. Planned NL-to-SQL Pipeline

The upcoming NL-to-SQL pipeline consists of four orchestrated stages:

1. **Schema Context Injection**: Dynamically extract the table and column definitions from `database.inspect_database_schema()` to build the LLM system prompt.
2. **SQL Generation**: The LLM translates the user's natural language request into a single MySQL query tailored to the schema.
3. **Security Validation**: `sql_service.validate_sql()` parses and verifies the query before it reaches the database.
4. **Execution & Insight Synthesis**: The query executes against `banking_risk_analytics`, results are loaded into pandas DataFrames, and the LLM produces a concise financial summary alongside interactive charts/tables in Streamlit.

---

## 10. Running the Application & Tests

### Run Streamlit App
```bash
streamlit run app.py
```

### Run Unit Tests
```bash
pytest tests/ -v
```
