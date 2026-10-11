# 🏦 Bank Data AI view

> **Natural-Language-to-SQL Analytics Assistant for Commercial Banking Data**  
> Transform plain English financial inquiries into secure, read-only MySQL queries with dynamic schema discovery, automated security guardrails, interactive charts, and AI-generated executive summaries.

-----

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Gemini API](https://img.shields.io/badge/Google%20Gemini-API-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![Render](https://img.shields.io/badge/Deploy%20to-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com/)

-------

## 📌 What This Does 

**Bank Data AI** is an intelligent conversational analytics platform designed for exploring relational banking databases without requiring manual SQL authoring. 

Non-technical financial analysts, risk officers, and branch managers can ask complex business questions in plain English. The platform dynamically inspects the database schema, constructs dialect-accurate MySQL 8.0+ queries via Google Gemini, passes the SQL through a strict multi-layer read-only validation firewall, executes the query against live MySQL tables, and delivers:
1. **Interactive Tabular Results** with execution latency and record count metrics.
2. **Adaptive Dynamic Visualizations** (metrics cards, category bar charts, time-series lines, scatter plots, and distribution histograms).
3. **AI Executive Summaries** that distill the query output into actionable business takeaways and risk highlights.

---

## 🖼️ Dashboard Preview 

![Schema Discovery](screenshots/overview.png)

![Query Result](screenshots/query-result.png)

---

## 🔄 Architecture & How It Works

The platform uses a stepped, deterministic execution pipeline to guarantee safety, correctness, and speed:

```
[ User Question ]
       │
       ▼
1. Dynamic Schema Context Injection (database.py)
   └── SQLAlchemy dynamically extracts live table structures, columns, and foreign key relations
       │
       ▼
2. LLM SQL Generation (llm_service.py)
   └── Gemini converts question to dialect-accurate MySQL 8.0+ SQL utilizing explicit join pathways
       │
       ▼
3. Strict Safety & Read-Only Validation Firewall (sql_service.py)
   └── Multi-stage regex validator strictly blocks non-SELECT/WITH statements, mutations, and stacked injection
       │
       ▼
4. Database Execution & Latency Profiling (database.py / sql_service.py)
   └── Safe query executes on MySQL connection pool; results fetched and formatted into a pandas DataFrame
       │
       ▼
5. Results, Adaptive Visual Analytics & Executive Summary (visualization.py & app.py)
   └── Streamlit renders the data table, auto-selects appropriate chart types, and presents an AI business narrative
```

1. **User Question**: The user enters a question in the chat input or selects one of the pre-built suggested banking questions.
2. **Schema Context Injection**: The application dynamically inspects the connected MySQL schema (`banking_risk_analytics`) using SQLAlchemy metadata inspection, passing real table definitions, column types, and relational join constraints to the prompt.
3. **LLM Generates SQL**: Google Gemini evaluates the prompt and generates a single read-only SQL query adhering to relational foreign keys.
4. **Safety Validation Blocks Non-SELECT**: An AST and token validation engine verifies the root command is strictly read-only (`SELECT` or `WITH`), removes comments to prevent bypasses, and terminates execution if any mutating or administrative command is detected.
5. **Query Runs**: The validated query executes against the pooled MySQL database with latency tracking and sanitized error handling.
6. **Results + AI Summary Shown**: The resulting dataset is displayed in an interactive table, accompanied by auto-selected chart visualizations and an AI-formulated executive summary answering the question in business context.

---

## 🛠️ Tech Stack 

| Layer | Technology | Description |
| :--- | :--- | :--- |
| **Frontend / UI** | [Streamlit](https://streamlit.io/) | Modern financial dashboard with conversational interface and diagnostics sidebar |
| **Backend & Pipeline** | [Python 3.11+](https://www.python.org/) | Core application logic, connection pooling, and pipeline orchestration |
| **Database** | [MySQL 8.0+](https://www.mysql.com/) | Relational database hosting the 7 core banking tables (`banking_risk_analytics`) |
| **Database ORM / Driver** | [SQLAlchemy 2.0+](https://www.sqlalchemy.org/) & [PyMySQL](https://pymysql.readthedocs.io/) | Dynamic runtime schema discovery, metadata inspection, and secure connection pooling |
| **AI / LLM Engine** | [Google Gemini API](https://ai.google.dev/) (`gemini-2.5-flash`) | Natural-language-to-SQL translation and analytical executive summary generation |
| **Data Manipulation** | [Pandas](https://pandas.pydata.org/) | Data cleaning, type inference, and tabular formatting |
| **Visualizations** | [Altair](https://altair-viz.github.io/) & Streamlit Native Charts | Rule-based chart selection heuristics (bar, line, scatter, histogram, KPI metric) |
| **Deployment** | [Render](https://render.com/) | Cloud hosting via Render Web Service (`render.yaml` blueprint) |

---

## ⚙️ Environment Variables Reference

| Variable | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | **Yes** | — | SQLAlchemy MySQL URL. Formats supported: `mysql+pymysql://user:pass@host:port/banking_risk_analytics` or standard cloud URI `mysql://user:pass@host:port/banking_risk_analytics`. |
| `LLM_API_KEY` | **Yes** | — | API key for the AI engine (e.g., Google Gemini `AIzaSy...` or OpenAI `sk-...`). |
| `LLM_MODEL` | No | `gemini-2.5-flash` | The model identifier used for SQL generation and executive summaries. |
| `LLM_BASE_URL` | No | `https://api.openai.com/v1` | Base endpoint URL for OpenAI-compatible providers. |

> **Connecting to Aiven MySQL vs Local MySQL:**
> - **Local MySQL**: `mysql+pymysql://root:your_password@localhost:3306/banking_risk_analytics`
> - **Aiven MySQL**: Copy the Service URI from the Aiven Console (e.g., `mysql://avnadmin:password@mysql-xxxxx.aivencloud.com:12345/banking_risk_analytics?ssl-mode=REQUIRED`). The platform automatically normalizes the scheme to `mysql+pymysql://`, cleans query parameters, and activates TLS/SSL transport.

---

## 🚀 Local Setup & Installation (Windows, macOS, Linux)

### 1. Clone the Repository
```bash
git clone https://github.com/manasvi-3009/bank-data-ai.git
cd bank-data-ai
```

### 2. Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` with your active database credentials and Gemini API key:
```ini
DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/banking_risk_analytics
LLM_API_KEY=AIzaSy...your_gemini_api_key...
LLM_MODEL=gemini-2.5-flash
```

### 5. Seed the Local Banking Database (Run Once for Local Dev)
Seed the 7 relational CSV banking tables into your local MySQL instance:
```bash
python load_csv_data.py
```

### 6. Launch the Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🌐 Deploying to Render

This repository includes a native [render.yaml](render.yaml) blueprint configured for Render Web Services.

### Option A: Deploy via Render Blueprint (Recommended)
1. Fork or push this repository to GitHub: `https://github.com/manasvi-3009/bank-data-ai`.
2. Log in to [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** ➔ **Blueprint**.
4. Connect the repository `manasvi-3009/bank-data-ai` and select the `main` branch.
5. Render detects `render.yaml`. Under **Environment Variables**, provide your secret values:
   - `DATABASE_URL`: Your remote MySQL URI (e.g., from Aiven).
   - `LLM_API_KEY`: Your Google Gemini API key.
   - `LLM_MODEL`: `gemini-2.5-flash`.
6. Click **Apply**. Render will automatically build and deploy the service.

### Option B: Deploy Manually as a Web Service
1. In Render, select **New +** ➔ **Web Service**.
2. Connect `https://github.com/manasvi-3009/bank-data-ai`.
3. Set the following service configuration:
   - **Runtime**: `Python 3`
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`
4. Under **Environment Variables**, add:
   - `PYTHON_VERSION` = `3.11.9`
   - `DATABASE_URL` = `<your_remote_mysql_url>`
   - `LLM_API_KEY` = `<your_gemini_api_key>`
   - `LLM_MODEL` = `gemini-2.5-flash`
5. Click **Create Web Service**.

### 🔧 Remote Aiven MySQL Configuration & Troubleshooting
If connecting Render to an Aiven MySQL database:
1. **Ensure Aiven Service is RUNNING**: Verify in the Aiven Console that the service state is green (`RUNNING`).
2. **Database Existence**: Ensure `banking_risk_analytics` has been created on your Aiven instance and populated with the schema.
3. **Resolving Error 2005 (Unknown MySQL server host)**:
   - Error 2005 indicates DNS lookup failure.
   - Copy the exact **Service URI** directly from the Aiven Console overview tab. Do not alter the hostname or omit the port number.
   - Ensure there are no spaces or protocol prefixes in the host portion.
4. **TLS/SSL Handshake**: Aiven requires TLS/SSL by default. The application automatically configures PyMySQL SSL context for all remote connections.

---

## 🧪 Automated Testing & CI

The repository contains a comprehensive automated test suite (56 unit and integration tests) covering configuration, database pooling, SQL safety validation, query pipelines, and visualization heuristics. Tests use isolated in-memory SQLite instances and mocks, ensuring they execute without requiring external databases or private API keys.

To run tests locally:
```bash
python -m pytest tests/ -q
```

### GitHub Actions CI
Every commit and pull request to `main` is automatically validated via [.github/workflows/ci.yml](.github/workflows/ci.yml) on Ubuntu with Python 3.11.

---

## 💡 Example Questions & Capabilities

### 1. Branch Loan Exposure Analysis
> *"What is the total outstanding loan balance grouped by branch?"*
* **Demonstrates**: Multi-table relational joins (`branches` ➔ `accounts` ➔ `loans`), aggregate computation (`SUM(l.Loan_Amount)`), `LEFT JOIN` handling to preserve branches with zero loans, and descending sorting.
* **Generated Query**:
```sql
SELECT 
    b.Branch_ID,
    b.Branch_Name,
    COALESCE(SUM(l.Loan_Amount), 0) AS Total_Outstanding_Loan_Balance
FROM branches b
LEFT JOIN accounts a ON b.Branch_ID = a.Branch_ID
LEFT JOIN loans l ON a.Customer_ID = l.Customer_ID
GROUP BY b.Branch_ID, b.Branch_Name
ORDER BY Total_Outstanding_Loan_Balance DESC
```

### 2. Credit Risk & High Utilization Screening
> *"List customers holding credit cards with balances above 80% of credit limit."*
* **Demonstrates**: Computed ratio formulas, demographic entity joins (`customers` ➔ `credit_cards`), dynamic threshold filters (`Outstanding_Balance > Credit_Limit * 0.80`), and risk ranking.
* **Generated Query**:
```sql
SELECT 
    c.Customer_ID,
    c.First_Name,
    c.Last_Name,
    c.Email,
    c.Phone,
    cc.Card_ID,
    cc.Card_Type,
    cc.Credit_Limit,
    cc.Outstanding_Balance,
    ROUND((cc.Outstanding_Balance / cc.Credit_Limit) * 100, 2) AS Utilization_Percentage
FROM customers c
JOIN credit_cards cc ON c.Customer_ID = cc.Customer_ID
WHERE cc.Credit_Limit > 0 
  AND cc.Outstanding_Balance > (cc.Credit_Limit * 0.80)
ORDER BY Utilization_Percentage DESC
```

### 3. Account Type Transaction Ledger Profiling
> *"What is the average transaction amount per account type?"*
* **Demonstrates**: High-frequency transaction ledger aggregation (`accounts` ➔ `transactions`), grouping by account category, and mean transaction calculation.
* **Generated Query**:
```sql
SELECT 
    a.Account_Type,
    ROUND(AVG(t.Amount), 2) AS Average_Transaction_Amount
FROM accounts a
JOIN transactions t ON a.Account_ID = t.Account_ID
GROUP BY a.Account_Type
ORDER BY Average_Transaction_Amount DESC
```

---

## 🛡️ Security Note: Strict SQL Validation Layer

Analytical AI platforms querying databases must enforce zero-trust security guardrails:

1. **Root-Command Allowlist**: Queries must strictly begin with `SELECT` or `WITH`.
2. **Forbidden Keyword Firewall**: A multi-pattern regex scanner immediately blocks mutating DDL/DML and administrative keywords:
   `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`, `CALL`, `EXEC`, `EXECUTE`, `LOCK`, `UNLOCK`, `SET`, `USE`, `FLUSH`, `KILL`, `SHUTDOWN`, `INTO OUTFILE`, `INTO DUMPFILE`, `LOAD_FILE`, `BENCHMARK`, `SLEEP`.
3. **Comment Stripping & Injection Protection**:
   - Comments (`/* ... */`, `-- ...`, `# ...`) are stripped before parsing to prevent cloaking.
   - String literals are masked, and unquoted semicolons are rejected to block multiple stacked statements.
4. **Credential Isolation**:
   - Secrets are loaded from environment variables and never logged or exposed in plaintext.
   - Connection URLs shown in logs and UI diagnostics always have passwords masked (`mysql+pymysql://root:******@host:port/db`).
   - `.env`, `.sql` dumps, and Streamlit secrets are strictly excluded in `.gitignore`.
5. **Sanitized User Errors**: Database runtime exceptions are sanitized into friendly user notifications without leaking internal connection strings or stack traces.

---

## 📊 Companion Project: Dual-Lens Analytics

This project utilizes the exact same synthetic banking dataset (`banking_risk_analytics`) as my **Enterprise Banking Risk Analytics** Power BI project, illustrating how the same enterprise data foundation can be analyzed across two distinct paradigms:

* **In Power BI (Visual Modeling & BI)**: Pre-aggregated star schema data models, complex DAX financial metrics, branch performance heatmaps, and scheduled compliance reports.
* **In Bank Data AI (Conversational AI & Agentic SQL)**: Ad-hoc exploratory questions, dynamic schema discovery, automated SQL generation, and real-time executive summaries.

Together, both projects demonstrate an end-to-end data engineering and analytics competency — from structured BI modeling to generative AI copilots.

---

## ⚠️ Deployment Limitations

- **Render Free Tier Spin-Down**: Free Render web services spin down after 15 minutes of inactivity. The initial request may take ~50 seconds to cold start.
- **Strict Read-Only Enforcement**: The system strictly supports analytical read operations. Modifying data or schema mutations are blocked by design.
- **Single-Turn Execution**: Each query is currently generated independently from live schema metadata. Multi-turn follow-ups are planned for the next release.

---

## 🔮 Future Enhancements

- [ ] **Conversational Memory**: Multi-turn dialog context retention to support contextual follow-ups (e.g., *"Filter the previous result to show only the Park Street branch"*).
- [ ] **Expanded Visualizations**: Interactive heatmaps, geospatial branch maps, and Sankey transaction flows.
- [ ] **Multi-Dialect Support**: Configurable query generation targeting PostgreSQL, Snowflake, and BigQuery.
- [ ] **Automated Query Plan Optimization**: Visualizing MySQL `EXPLAIN ANALYZE` execution plans with AI recommendations for index optimization.
- [ ] **One-Click Executive Briefing Export**: Download result datasets and executive summaries as branded PDF memos or CSV files.

---

## 👤 Author

**Manasvi Vats**  
- **GitHub**: [@manasvi-3009](https://github.com/manasvi-3009)  
- **LinkedIn**: [linkedin.com/in/manasvi-vats](https://www.linkedin.com/in/manasvi-vats)  
- **Repository**: [bank-data-ai](https://github.com/manasvi-3009/bank-data-ai)
