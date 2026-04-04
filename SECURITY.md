# Security Policy

## Supported Scope

SpecForge currently maintains a baseline security posture for:
- Flask application code in `specforge/`
- dependency hygiene from `requirements.txt`
- secret exposure checks in source control
- session and token handling for MiniMax OAuth

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
