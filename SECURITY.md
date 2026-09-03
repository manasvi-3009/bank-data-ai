# Security

## Read-Only Database Access

Bank Data AI is designed for analytical workloads only.

The application allows read-only SQL queries and rejects database mutation operations.

Blocked operations include:

- INSERT
- UPDATE
- DELETE
- DROP
- ALTER
- TRUNCATE
- CREATE
- GRANT
- REVOKE
- CALL
- SET
- USE

Multi-statement SQL is also rejected.

## Secrets

Database credentials and LLM API keys are stored in environment variables.

Secrets must never be committed to GitHub.

The local `.env` file is excluded through `.gitignore`.

## Database Safety

The application does not intentionally modify the real `banking_risk_analytics` database.

Testing that requires database mutation must use mocks or an isolated test database.

## Query Generation

LLM-generated SQL is treated as untrusted input and must pass validation before execution.

## Production Considerations

For production deployment, consider:

- dedicated read-only database credentials
- query timeout limits
- audit logging
- rate limiting
- role-based access control
- query cost controls