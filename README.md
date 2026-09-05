# 🏦 Bank Data AI

> **Ask questions. Get answers. Query your banking data in natural language.**

**Bank Data AI** is an AI-powered analytics assistant that allows users to interact with a real relational banking database using natural language instead of manually writing SQL.

The application combines **LLM-powered SQL generation, dynamic database schema discovery, SQL safety validation, MySQL execution, result analysis, and automatic visualization** into a single Streamlit application.

Instead of requiring a user to know SQL syntax, the system translates questions such as:

> "Which branch has the highest number of customers?"

into a safe analytical SQL query, executes it against the banking database, and presents the result in an understandable format.

---

# 📌 Table of Contents

- [Overview](#-overview)
- [Problem Statement](#-problem-statement)
- [Solution](#-solution)
- [Why This Project](#-why-this-project)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [End-to-End Workflow](#-end-to-end-workflow)
- [Natural Language to SQL Pipeline](#-natural-language-to-sql-pipeline)
- [SQL Security Model](#-sql-security-model)
- [Database](#-database)
- [Database Schema Discovery](#-database-schema-discovery)
- [Query Execution](#-query-execution)
- [Result Analysis](#-result-analysis)
- [Automatic Visualization](#-automatic-visualization)
- [Error Handling](#-error-handling)
- [Chat Experience](#-chat-experience)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [Running the Application](#-running-the-application)
- [Example Questions](#-example-questions)
- [Testing](#-testing)
- [GitHub Actions](#-github-actions)
- [Security](#-security)
- [Design Decisions](#-design-decisions)
- [Current Capabilities](#-current-capabilities)
- [Limitations](#-limitations)
- [Future Improvements](#-future-improvements)
- [Project Highlights](#-project-highlights)
- [Repository](#-repository)
- [Author](#-author)

---

# 🔎 Overview

Traditional analytics workflows often require users to understand SQL before they can explore relational data.

Bank Data AI reduces this barrier by allowing users to ask questions in ordinary language.

The application connects to the real MySQL database:

`banking_risk_analytics`

and dynamically discovers its schema before generating analytical queries.

The high-level experience is:

```text
User Question
      ↓
Schema Discovery
      ↓
LLM Context Construction
      ↓
Natural Language → SQL
      ↓
SQL Safety Validation
      ↓
Read-Only MySQL Execution
      ↓
Query Result
      ↓
Natural-Language Explanation
      ↓
Visualization (when appropriate)