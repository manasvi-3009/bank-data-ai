# 🏦 Bank Data AI

> **Natural-Language Analytics for a Relational Banking Database**  
> An enterprise-grade AI assistant that translates plain English financial questions into secure, read-only MySQL queries, executes them against a relational banking database, and delivers structured tabular data, automatic charts, and executive insights.

---

## 📌 Overview

Exploring relational databases typically requires deep SQL proficiency, knowledge of table joins, and familiarity with business logic. **Bank Data AI** bridges the gap between decision-makers and relational data by providing a conversational analytics interface.

Users can ask everyday questions such as:
- *"Which branch has the highest number of customers?"*
- *"What is the total outstanding loan balance grouped by branch?"*
- *"Which customers have the highest credit card utilization rate?"*
- *"Show all transactions flagged as fraud with their reasons."*

The system dynamically inspects the database schema, constructs dialect-accurate MySQL 8.0+ queries, enforces strict read-only security guardrails, executes the query, and formats the findings with executive summaries and automatic visualizations.

> **Note on Data**: This is a portfolio demonstration project operating on a **synthetic banking dataset** designed to mirror realistic commercial banking operations, risk profiles, and transaction volumes.

----
## 🛠️ Tech Stack

- **Application & UI**: Python 3.11+, Streamlit (Modern Financial Theme)
- **Database**: MySQL 8.0+ (`banking_risk_analytics`)
- **Database Layer**: SQLAlchemy 2.0+, PyMySQL, Cryptography
- **Data & Visualizations**: Pandas, Altair, Streamlit Native Visualizations
- **AI / LLM Engine**: Google Gemini API (`gemini-2.5-flash`), OpenAI API, Anthropic Claude API, and Schema-Grounded Offline Fallback Provider
- **Testing & Quality Assurance**: Pytest, Unittest (53 tests, 100% pass rate)

---

## 🔄 How the NL-to-SQL Pipeline Works

```
User Question
      │
      ▼
1. Dynamic Schema Discovery (database.py)
   └── SQLAlchemy dynamically extracts table definitions, column types, and foreign keys
      │
      ▼
2. LLM Context Construction & SQL Generation (llm_service.py)
   └── Builds MySQL 8.0+ dialect prompt with explicit join pathways and constraints
      │
      ▼
3. Strict Read-Only Security Validation (sql_service.py)
   └── Rejects mutating statements (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, etc.)
   └── Strips comments and blocks multi-statement / stacked query injection
      │
      ▼
4. Database Execution (database.py)
   └── Executes safe read-only query over pooled MySQL connections with latency tracking
      │
      ▼
5. Result Formatting & Intelligent Visualization (visualization.py & app.py)
   └── Categorical comparisons ➔ Bar Charts
   └── Time-series trends ➔ Line Charts
   └── Correlations ➔ Scatter Plots
   └── Distributions ➔ Histograms
   └── Single-row aggregates ➔ Metric KPIs
      │
      ▼
6. AI Executive Summary Formulation (llm_service.py)
   └── Factual, non-hallucinating narrative answering the user's initial question
```

---

## 🗄️ Database Architecture: `banking_risk_analytics`

The database consists of **seven core banking tables**:

| Table | Description | Primary Key | Key Relational Pathways |
| :--- | :--- | :--- | :--- |
| **`branches`** | Bank physical branch locations and regions | `Branch_ID` | Links to `accounts.Branch_ID` and `employees.Branch_ID` |
| **`accounts`** | Customer deposit and savings accounts | `Account_ID` | Links to `branches.Branch_ID`, `customers.Customer_ID`, `transactions.Account_ID` |
| **`customers`** | Customer demographics, income, risk scores, KYC | `Customer_ID` | Links to `accounts.Customer_ID`, `loans.Customer_ID`, `credit_cards.Customer_ID` |
| **`loans`** | Consumer and commercial loan portfolio | `Loan_ID` | Links to `customers.Customer_ID` (and to `branches` via `accounts`) |
| **`credit_cards`** | Credit card lines, limits, and balances | `Card_ID` | Links to `customers.Customer_ID` |
| **`transactions`** | High-frequency transaction ledger & fraud flags | `Transaction_ID` | Links to `accounts.Account_ID` |
| **`employees`** | Branch personnel, roles, and payroll | `Employee_ID` | Links to `branches.Branch_ID` |

---

## 🛡️ Security & Safety Model

1. **Strict Read-Only Enforcement**: Only `SELECT` and `WITH` (Common Table Expressions) statements are allowed. Any statement containing mutating operations (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`, `CALL`, `SET`, `USE`, etc.) is immediately rejected.
2. **Comment-Stripping & Injection Protection**: SQL comments (`/* ... */`, `-- ...`, `# ...`) are stripped before parsing to prevent comment-based evasion. Multi-statement execution via stacked semicolons is strictly prohibited.
3. **Secret Masking**: Database passwords and API keys are parsed securely from environment variables and masked in all logs, diagnostics, and UI screens.
4. **Sanitized User Errors**: Database syntax and network errors are converted into clear, user-facing error notifications without exposing raw connection strings or stack traces.

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.11+
- MySQL Server 8.0+ running on port `3306`
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/bank-data-ai.git
cd bank-data-ai
```

### 2. Set Up Virtual Environment
```bash
# On Windows:
python -m venv venv
.\venv\Scripts\Activate.ps1

# On macOS / Linux:
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to create your local `.env` file:
```bash
cp .env.example .env
```
Configure your credentials in `.env`:
```env
# Database Connection (MySQL)
DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/banking_risk_analytics

# LLM API Configuration (Google Gemini, OpenAI, Claude, or compatible)
LLM_API_KEY=your_gemini_api_key_here
LLM_MODEL=gemini-2.5-flash
```

### 5. Optional: Ingest Synthetic Data
If setting up a fresh MySQL database, create the `banking_risk_analytics` schema in MySQL and run the data loader to populate tables from `./data/*.csv`:
```bash
python load_csv_data.py
```

### 6. Run the Application
Launch the Streamlit console:
```bash
streamlit run app.py
```
The application will open in your browser at `http://localhost:8501`.

---

## 🧪 Automated Testing

The project includes an automated test suite with 100% pass rate:

```bash
python -m pytest tests/ -v
```

**Test Coverage**:
- `test_config.py` — Credential masking and environment parsing
- `test_database.py` — Connection pooling, health diagnostics, and dynamic schema inspection
- `test_sql_service.py` — Read-only security enforcement, comment stripping, and injection rejection
- `test_llm_service.py` — Prompt formatting, provider abstractions, and fallback logic
- `test_query_flow.py` — End-to-end integration query flow with isolated test database
- `test_result_quality.py` — Verification of NULL vs. 0-row empty result handling
- `test_visualization.py` — Heuristic chart selection logic (Bar, Line, Scatter, Histogram, Metrics)

---

## 💡 Example Queries

- **Branch Analytics**: *"Which branch has the highest number of customers?"*
- **Loan Balances**: *"What is the total outstanding loan balance grouped by branch?"*
- **Credit Card Utilization**: *"Which customers have the highest credit card utilization rate?"*
- **Fraud Detection**: *"Show all transactions flagged as fraud with their reasons."*
- **Transaction Volumes**: *"What is the total transaction volume by transaction type?"*
- **Branch Payroll**: *"What is the average and total employee salary by branch?"*
