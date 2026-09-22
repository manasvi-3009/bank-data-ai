# 🏦 Bank Data AI

> **Natural-Language-to-SQL Analytics Assistant for Commercial Banking Data**  
> Transform plain English financial inquiries into secure, read-only MySQL queries with dynamic schema discovery, automated security guardrails, interactive charts, and AI-generated executive summaries.

----

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Gemini API](https://img.shields.io/badge/Google%20Gemini-API-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)](https://ai.google.dev/)

---

## 📌 What This Does

**Bank Data AI** is an intelligent conversational analytics platform designed for exploring relational banking databases without requiring manual SQL authoring. 

Non-technical financial analysts, risk officers, and branch managers can ask complex business questions in plain English. The platform dynamically inspects the database schema, constructs dialect-accurate MySQL 8.0+ queries via Google Gemini, passes the SQL through a strict multi-layer read-only validation firewall, executes the query against live MySQL tables, and delivers:
1. **Interactive Tabular Results** with latency and record count metrics.
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
1. Dynamic Schema Context Injection
   └── SQLAlchemy dynamically extracts live table structures, columns, and foreign key relations
       │
       ▼
2. LLM SQL Generation
   └── Gemini converts question to dialect-accurate MySQL 8.0+ SQL utilizing explicit join pathways
       │
       ▼
3. Strict Safety & Read-Only Validation Firewall
   └── Multi-stage regex validator strictly blocks non-SELECT/WITH statements, mutations, and stacked injection
       │
       ▼
4. Database Execution & Latency Profiling
   └── Safe query executes on MySQL connection pool; results fetched and formatted into a pandas DataFrame
       │
       ▼
5. Results, Adaptive Visual Analytics & Executive Summary
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

---

## 🚀 Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/manasvi-3009/bank-data-ai.git
cd bank-data-ai
```

### 2. Create and Activate a Virtual Environment
```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate
```

### 3. Install Requirements
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` with your MySQL database connection and Google Gemini API key:
```ini
DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/banking_risk_analytics
LLM_API_KEY=AIzaSy...your_gemini_api_key...
LLM_MODEL=gemini-2.5-flash
```

### 5. Seed the Banking Database (Run Once)
Load the 7 core CSV banking tables into MySQL:
```bash
python load_csv_data.py
```

### 6. Launch the Streamlit Application
```bash
streamlit run app.py
```
The application will open in your default browser at `http://localhost:8501`.

---

## 💡 Example Questions & Capabilities

Here are three real examples demonstrated in the platform:

### 1. Branch Loan Exposure Analysis
> *"What is the total outstanding loan balance grouped by branch?"*
* **What It Demonstrates**: Dynamic multi-table relational join navigation (`branches` ➔ `accounts` ➔ `loans`), aggregate computation (`SUM(l.Loan_Amount)`), `LEFT JOIN` handling to ensure branches without accounts are not dropped, and descending volume sorting.
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
* **What It Demonstrates**: Computed ratio calculations, customer demographic joins (`customers` ➔ `credit_cards`), dynamic threshold filtering (`Outstanding_Balance > Credit_Limit * 0.80`), and risk ranking by credit utilization percentage.
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
* **What It Demonstrates**: High-volume ledger aggregation (`accounts` ➔ `transactions`), categorical grouping (`Savings`, `Current`, `Salary`), and mean transaction size computation.
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

Analytical AI systems querying operational or analytical databases must prevent unauthorized data modifications, administrative tampering, and injection exploits.

**Bank Data AI enforces a zero-trust SQL validation layer before any query reaches the database:**

1. **Root-Command Restriction**: Queries must strictly begin with an authorized read-only keyword (`SELECT` or `WITH`).
2. **Forbidden Keyword Firewall**: A tokenized regex scanner immediately rejects statements containing mutating DDL/DML or administrative keywords:
   `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`, `CALL`, `EXEC`, `EXECUTE`, `LOCK`, `UNLOCK`, `SET`, `USE`, `FLUSH`, `KILL`, `SHUTDOWN`, `INTO OUTFILE`, `INTO DUMPFILE`, `LOAD_FILE`, `BENCHMARK`, `SLEEP`.
3. **Comment-Stripping & Stacked Statement Prevention**:
   - Comments (`/* ... */`, `-- ...`, `# ...`) are stripped before inspection to prevent comment-cloaking evasion techniques.
   - String literals are masked, and unquoted semicolons are blocked to reject multiple stacked SQL statements.
4. **Credential Isolation**:
   - Database credentials and API keys are read from environment variables and never displayed in plain text.
   - All connection strings shown in logs and UI diagnostics have passwords masked (e.g., `mysql+pymysql://root:******@localhost:3306/banking_risk_analytics`).
5. **Sanitized User Errors**:
   - Database execution errors are sanitized into friendly messages without leaking internal server topologies or credentials.

---

## 📊 Companion Project: Dual-Lens Analytics

This project utilizes the exact same synthetic banking dataset (`banking_risk_analytics`) as my **Enterprise Banking Risk Analytics** Power BI project, showcasing how the same underlying enterprise financial data can be explored through two distinct analytical paradigms:

* **In Power BI (Traditional BI & Visual Modeling)**: Pre-aggregated star schema data models, complex DAX financial metrics, branch performance heatmaps, and scheduled compliance reports.
* **In Bank Data AI (Conversational AI & Dynamic SQL)**: Ad-hoc exploratory queries, on-demand NL-to-SQL synthesis, dynamic schema inspection, and real-time AI executive briefings.

Together, these two implementations showcase an end-to-end perspective on enterprise analytics — from structured BI modeling to generative AI data copilots.

---

## 🔮 Future Enhancements

The following roadmap features are planned for future releases:

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
