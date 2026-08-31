# Bank Data AI 🏦

> **Natural-Language Analytics for a Real Banking Database**  
> An enterprise-grade analytical assistant that enables users to query a live MySQL banking database using natural language, executes strictly validated read-only SQL queries, and generates executive business insights and automated visual analytics.

---

## 1. Problem
Exploring enterprise relational databases typically requires deep SQL proficiency and intimate familiarity with database schemas, table joins, and financial domain metrics. Business stakeholders, branch managers, and financial risk analysts often face delays waiting for specialized technical teams to write ad-hoc SQL queries for everyday reporting and compliance questions.

---

## 2. Solution
**Bank Data AI** bridges the gap between non-technical stakeholders and complex relational databases:
- Translates natural language questions into dialect-accurate, high-performance MySQL 8.0+ queries.
- Dynamically discovers live database schemas, constraints, and relationships at runtime via SQLAlchemy metadata inspection—without hardcoding schemas.
- Enforces strict read-only security guardrails that reject data mutation (DDL/DML) and multi-statement injection attempts.
- Synthesizes tabular results, automated charts (bar, line, scatter, KPI metrics), and natural-language executive summaries tailored for financial decision-makers.

---

## 3. Key Features

- **Natural-Language Analytics**: Ask questions in plain English across branches, customers, loans, transactions, credit cards, and employee payroll.
- **Dynamic Schema Discovery**: Automatically discovers table names, column data types, nullability, primary keys, and foreign keys directly from MySQL via SQLAlchemy Inspector.
- **Strict Read-Only SQL Security Layer**: Multi-layer AST and regex-based validation blocking all destructive commands (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`, `CALL`, `SET`, `USE`), stacked queries, and comment-obfuscation bypasses.
- **Direct MySQL Integration**: Production-ready SQLAlchemy connection pooling, pre-ping health checks, connection timeouts, and masked credential logs.
- **Grounded Executive Explanations**: Concise, factual natural-language summaries formulated strictly from query results without hallucinations or fabricated data.
- **Intelligent Automatic Visualizations**: Dynamic heuristic chart engine selecting KPI metric cards, categorical bar charts, date-based trend lines, and scatter plots based on returned DataFrame dimensions.
- **Session-Preserved Chat Console**: Streamlit chat interface with stepped progress indicators (`Inspecting schema...`, `Generating SQL...`, `Validating query...`, `Running query...`, `Preparing answer...`) and interactive schema exploration.
- **Comprehensive Test Suite**: 100% passing automated test suite covering configuration, connection diagnostics, schema discovery, SQL security guardrails, LLM provider abstraction, and end-to-end query execution.

---

## 4. Architecture Pipeline

```
User Natural-Language Question
           │
           ▼
  Streamlit Interface (app.py)
           │
           ▼
  Dynamic Schema Inspector (database.py)
  └── Retrieves tables, columns, types, PKs, and FKs via SQLAlchemy
           │
           ▼
  LLM Generation Layer (llm_service.py)
  └── Schema-grounded prompt engineering + MySQL 8.0 dialect formatting
           │
           ▼
  SQL Security & Validation Layer (sql_service.py)
  └── Verifies read-only root command (SELECT / WITH)
  └── Strips comments & validates unquoted tokens
  └── Blocks DDL/DML, multi-statements, & injection patterns
           │
           ▼
  Database Execution Engine (database.py)
  └── Executes validated query via SQLAlchemy connection pool
           │
           ▼
  Result Processing & Presentation (app.py)
  ├── Formatted Pandas DataFrame with row count & latency metadata
  ├── Intelligent Auto-Visualization (Bar / Line / Scatter / Metrics)
  └── Natural-Language Executive Summary (llm_service.py)
```

---

## 5. Tech Stack

- **Core Logic & Backend**: Python 3.11+
- **Frontend / Dashboard**: Streamlit (Modern Financial Theme)
- **Database**: MySQL 8.0+ (`banking_risk_analytics`)
- **Database Access Layer**: SQLAlchemy 2.0+, PyMySQL, Cryptography
- **Data Manipulation & Analytics**: Pandas
- **Visualization**: Streamlit Native Visualizations / Altair
- **AI / LLM Integration**: Google Gemini API, OpenAI API, Anthropic Claude API, and Offline Mock fallback provider
- **Testing & Quality Assurance**: Pytest, Unittest

---

## 6. Database: `banking_risk_analytics`

The application operates directly on the real **`banking_risk_analytics`** MySQL database containing seven core banking tables:

| Table | Description | Key Columns |
| :--- | :--- | :--- |
| **`accounts`** | Customer deposit and current accounts | `Account_ID`, `Customer_ID`, `Branch_ID`, `Account_Type`, `Current_Balance`, `Account_Status` |
| **`branches`** | Bank physical branch locations and regions | `Branch_ID`, `Branch_Name`, `Branch_Code`, `City`, `State`, `Region`, `Manager_Name` |
| **`credit_cards`**| Credit card lines and utilization | `Card_ID`, `Customer_ID`, `Card_Type`, `Credit_Limit`, `Outstanding_Balance`, `Card_Status` |
| **`customers`** | Customer demographics, risk, and KYC | `Customer_ID`, `First_Name`, `Last_Name`, `Annual_Income`, `Risk_Score`, `Customer_Segment`, `KYC_Status` |
| **`employees`** | Branch personnel, roles, and payroll | `Employee_ID`, `Branch_ID`, `First_Name`, `Last_Name`, `Job_Title`, `Department`, `Salary` |
| **`loans`** | Commercial and consumer loan portfolios | `Loan_ID`, `Customer_ID`, `Loan_Type`, `Loan_Amount`, `Interest_Rate`, `Loan_Term_Months`, `Loan_Status` |
| **`transactions`** | High-frequency transaction ledger | `Transaction_ID`, `Account_ID`, `Transaction_Date`, `Transaction_Type`, `Amount`, `Is_Fraud`, `Fraud_Reason` |

> [!NOTE]
> All application database access is strictly **read-only**. The real database is never mutated or altered by this application.

---

## 7. Setup & Installation

### Prerequisites
- Python 3.11 or higher
- MySQL Server (running on port 3306 with `banking_risk_analytics` loaded)
- Git

### 1. Clone the Repository
```bash
git clone <repository-url> bank-data-ai
cd bank-data-ai
```

### 2. Create and Activate Virtual Environment
```bash
# Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS:
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 8. Environment Variables Configuration

Copy `.env.example` to create your local `.env` configuration file:

```bash
cp .env.example .env
```

Configure your environment settings in `.env`:

```env
# ==============================================================================
# Database Connection (MySQL)
# Standard SQLAlchemy MySQL URL format:
# mysql+pymysql://<db_user>:<db_password>@<db_host>:<db_port>/<database_name>
# ==============================================================================
DATABASE_URL=mysql+pymysql://root:your_mysql_password@localhost:3306/banking_risk_analytics

# ==============================================================================
# LLM API Configuration
# Supports Google Gemini, OpenAI, Claude, or any OpenAI-compatible API
# ==============================================================================
LLM_API_KEY=your_llm_api_key_here
LLM_MODEL=gemini-2.5-flash

# Optional: Custom base URL (for local vLLM, Ollama, Groq, or OpenRouter)
# LLM_BASE_URL=https://api.openai.com/v1
```

> [!IMPORTANT]
> The `.env` file is excluded from Git tracking via `.gitignore`. Never commit actual API keys or database passwords.

---

## 9. Example Analytical Questions

Try asking any of the following natural-language questions in the chat console:

- **Branch Analytics**: *"Which branch has the highest total loan amount?"*
- **Account Balances**: *"What is the average account balance grouped by account type?"*
- **Credit Risk**: *"Which customers have the highest credit card utilization rate?"*
- **Fraud Detection**: *"Show all transactions flagged as fraud with their reasons and amounts."*
- **Transaction Volumes**: *"What is the total transaction volume by transaction type?"*
- **Payroll Analytics**: *"What is the average employee salary by department?"*
- **Customer Risk Distribution**: *"List the top 10 customers with the lowest risk scores and their annual incomes."*

---

## 10. Security Implementation

1. **Strict Read-Only Enforcement**: Every SQL statement is validated by `sql_service.validate_sql()` prior to execution. Any statement containing mutating keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`, `CALL`, `SET`, `USE`, `LOCK`, `UNLOCK`, `EXEC`, `EXECUTE`, `FLUSH`, `KILL`, `SHUTDOWN`, `LOAD_FILE`, `INTO OUTFILE`) is immediately blocked.
2. **Comment-Stripping & Injection Defense**: Comments (`/* ... */`, `-- ...`, `# ...`) are stripped before parsing to prevent comment-based obfuscation bypasses. Stacked queries containing unquoted semicolons are rejected.
3. **Secret Isolation & Masking**: Plaintext database passwords and API keys are parsed securely via `config.py` and masked in logs, diagnostics, and UI cards (`mysql://user:******@localhost:3306/banking_risk_analytics`).
4. **Sanitized Error Messaging**: SQL syntax errors and network issues are converted into clean user-facing guidance without leaking internal stack traces or database connection URIs.
5. **Result Set Bounding**: Queries are bounded by default result caps to prevent server memory exhaustion.

---

## 11. Testing

Run the automated unit and integration test suite using `pytest`:

```bash
python -m pytest tests/ -v
```

All 43 unit and integration tests validate:
- Configuration parsing and secret masking (`tests/test_config.py`)
- Database connection diagnostics and dynamic schema discovery (`tests/test_database.py`)
- SQL read-only validation, comment stripping, and security rules (`tests/test_sql_service.py`)
- LLM service provider abstraction, fallback responses, and prompt constraints (`tests/test_llm_service.py`)
- End-to-end integration query flow, empty result handling, and error states (`tests/test_query_flow.py`)

---

## 12. Running the Application

Launch the Streamlit analytics application:

```bash
streamlit run app.py
```

Open your web browser at `http://localhost:8501`.

---

## 13. Optional Data Ingestion Tool

If setting up a fresh local MySQL instance, the optional standalone script `load_csv_data.py` can be used to populate the tables from `./data/*.csv`:

```bash
python load_csv_data.py
```

*Note: This script is an optional development utility and is not used in the primary query path.*

---

## 14. Current Limitations

- **Complex Domain Calculations**: Highly subjective financial modeling requiring multi-step probabilistic risk simulations requires specialized prompt engineering.
- **Dialect Optimization**: Tailored specifically for MySQL 8.0+ databases.
- **Large Result Sets**: Visualizations are optimized for analytical aggregations (up to 1,000 rows) rather than raw million-row dump exports.

---

## 15. Future Roadmap

- **Semantic Query Caching**: Cache common natural-language queries and SQL mappings in Redis to reduce LLM latency and API costs.
- **Role-Based Access Control (RBAC)**: Support multiple analyst roles with column-level masking for sensitive PII (e.g. customer phone/email).
- **Audit Logging & Analytics**: Store full query logs, user intent classifications, and query execution times in an administrative audit ledger.
- **Multi-Database Support**: Extend dialect abstractions to PostgreSQL, Snowflake, and BigQuery.
