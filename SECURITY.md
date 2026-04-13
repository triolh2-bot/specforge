# Security Policy

## Supported Scope

SpecForge currently maintains a baseline security posture for:
- Flask application code in `specforge/`
- dependency hygiene from `requirements.txt`
- secret exposure checks in source control
- session handling and provider credential storage

## Reporting

Do not open public issues for security problems.

Report security findings privately to the project owner with:
- a short description
- affected files or endpoints
- reproduction steps
- impact assessment

## Security Baseline

The current baseline requires:
- environment-provided secrets only
- encrypted server-side storage for provider OAuth tokens
- workspace-scoped access to persisted resources
- request-size limits and per-endpoint rate limiting
- dependency audit checks in CI
- static analysis and secret scanning in CI

## Rate Limiting

Default thresholds (per 60s window) are configured via environment variables:
- `RATE_LIMIT_ANALYZE` (default 20)
- `RATE_LIMIT_AI_CHAT` (default 10)
- `RATE_LIMIT_AI_ENHANCE` (default 10)
- `RATE_LIMIT_AUTH_LOGIN` (default 10)
- `RATE_LIMIT_AUTH_CALLBACK` (default 20)
- `RATE_LIMIT_AUTH_STATUS` (default 60)
- `RATE_LIMIT_LIST_ANALYSES` (default 60)
- `RATE_LIMIT_GET_ANALYSIS` (default 120)
- `RATE_LIMIT_GET_JOB` (default 120)
- `RATE_LIMIT_EXPORT_CREATE` (default 30)

Current rate limiting is in-memory and per-process. In multi-worker deployments this effectively multiplies limits by the number of workers. For production-grade enforcement, migrate to a shared backend (e.g., Redis).

## CSRF Mitigation

State-mutating endpoints use an Origin/Referer check for same-origin requests. This is a lightweight CSRF mitigation and assumes requests are made from the same site. If you expose the app across multiple origins or need stricter protection, add per-request CSRF tokens.

## Patch Expectations

- Critical vulnerabilities: patch or mitigate within 24 hours
- High severity vulnerabilities: patch within 7 days
- Medium severity vulnerabilities: patch within 30 days
- Low severity vulnerabilities: patch during scheduled maintenance

## Operational Rules

- Never commit `.env` files or raw credentials
- Rotate `SECRET_KEY`, `TOKEN_ENCRYPTION_SECRET`, and provider credentials after suspected exposure
- Review dependency updates before release
- Treat exported PRD content as customer data
