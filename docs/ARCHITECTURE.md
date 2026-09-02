# Bank Data AI — Architecture

## System Flow

User Question
    ?
Streamlit Chat Interface
    ?
Dynamic MySQL Schema Discovery
    ?
LLM SQL Generation
    ?
Read-Only SQL Validation
    ?
MySQL Query Execution
    ?
Result DataFrame
    ?
Natural-Language Explanation
    ?
Automatic Visualization

## Core Components

- pp.py — Streamlit user interface and session flow
- database.py — MySQL connection and dynamic schema inspection
- sql_service.py — SQL validation and query execution
- llm_service.py — LLM interaction and result explanation
- isualization.py — automatic chart selection
- 	ests/ — configuration, database, SQL, LLM, result-quality and visualization tests

## Data Source

The application uses the real MySQL database:

anking_risk_analytics

Tables:

- accounts
- branches
- credit_cards
- customers
- employees
- loans
- transactions

## Security Model

Only read-only analytical SQL is permitted. Mutation statements and multi-statement queries are rejected before execution.

Secrets are stored in .env and are excluded from version control.
