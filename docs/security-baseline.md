# SpecForge Security Baseline

## Objectives

This document defines the minimum security controls required before production rollout.

## Threat Model Summary

Primary risks in the current product:
- OAuth token theft
- cross-workspace data access
- prompt and input abuse through public analysis endpoints
- secret leakage in source control
- vulnerable Python dependencies
- insufficient auditability during incidents

## Required Controls

### Application Controls

- Keep session cookies `HttpOnly`, `SameSite=Lax`, and `Secure` in TLS environments
- Store provider OAuth tokens only in encrypted server-side persistence
- Scope all persisted records to a workspace boundary
- Enforce request-size limits and endpoint rate limits
- Validate all JSON request bodies and reject malformed content types

### Dependency Controls

- Run `pip-audit -r requirements.txt` on every pull request and main-branch push
- Update vulnerable dependencies according to the patch SLA in [SECURITY.md](/home/kali/.openclaw/workspace/specforge-mvp/SECURITY.md)

### Static Analysis Controls

- Run Bandit against `specforge/` and `app.py`
- Keep false-positive suppressions minimal and documented

### Secret Handling Controls

- Run `detect-secrets` against the whole repo
- Never commit `.env`
- Use environment-injected secrets for runtime configuration

### Data Handling Controls

- Treat requirement text, generated PRDs, and OAuth credentials as sensitive customer data
- Restrict production database access to operational owners only
- Keep local SQLite only for development; production should use a managed database

## Local Security Check

Run:

```bash
./scripts/security_check.sh
```

Required tooling is listed in `requirements-security.txt`.

## CI Enforcement

The CI workflow in `.github/workflows/security.yml` runs:
- Bandit
- pip-audit
- detect-secrets

## Residual Gaps

This baseline does not yet provide:
- centralized SIEM integration
- formal penetration testing
- WAF or bot-management infrastructure
- automated key rotation
- role-based authorization beyond workspace ownership
