# SpecForge CI/CD

## Required Checks

Require these workflows to pass before merge:
- `CI / lint`
- `CI / test`
- `CI / build`
- `Security / security`

Branch protection should require those checks on `main` and block direct pushes outside emergency procedures.

## What CI Validates

- Python syntax over `app.py`, `specforge/`, and `tests/`
- full backend test suite
- security scanning from `security.yml`
- container image build and artifact export

## Release Flow

1. Merge to `main` only after green CI and security checks.
2. Let `release.yml` create an immutable tag after the `CI` workflow succeeds on `main`.
3. Promote the container artifact built in CI from staging to production.

## Rollback Guidance

- Roll back by redeploying the prior release tag and its matching container artifact.
- Confirm `/health/live` and `/health/ready` recover before restoring full traffic.
- If the deploy included schema changes, roll forward with a hotfix unless the migration is explicitly reversible.
