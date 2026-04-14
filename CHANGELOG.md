# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-04-14

### Added
- Railway deployment configuration (`railway.json` and `docker-compose.prod.yml` optimizations).
- Redis-backed rate limiting implementation using Lua scripts for atomic window tracking.
- PostgreSQL backup script (`scripts/backup_postgres.sh`) with automated retention.
- PayPal billing integration tests and webhook testing mechanisms.
- Comprehensive security checks and pre-commit hooks integration.

### Changed
- Refactored `_check_first_analysis` logic to accurately track `SESSION_FIRST_ANALYSIS` product analytics.
- Hardened the `/metrics` endpoint to strictly require a `METRICS_SECRET` Bearer token.
- Enhanced observability logging with structured JSON logs formatted correctly across API endpoints.
- Updated database configurations to gracefully handle SQLite in dev and PostgreSQL in production.

### Fixed
- Fixed UTF-8 encoding artifacts in `index.html` loading components.
- Remedied ID duplication issues and Javascript null references on empty history states in template UI.
- Fixed Bandit security warnings regarding SHA1 usage in PRD generation logic.
- Resolved integration test context errors related to identical origins in the test client.

### Removed
- Removed MiniMax AI Provider entirely from system configuration and adapter layers.
