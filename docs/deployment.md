# SpecForge Deployment Guide

## Process Model

Use one container image and run it in two roles:
- `web`: `gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 app:app`
- `worker`: `python -m specforge.worker`

Both roles share the same image and connect to the same Postgres database.

## Local Provisioning

1. Copy `.env.example` to `.env` and replace the placeholder secrets.
2. Start the stack with `docker compose up --build`.
3. Wait for `postgres` and `web` health checks to pass.
4. Open `http://localhost:5000`.

## Services

- `postgres` provides persistent storage for analyses, jobs, auth credentials, and workspaces.
- `web` serves HTTP traffic and runs readiness/liveness probes.
- `worker` drains queued AI analysis jobs out of band from the web process.

## Staging and Production

Use the same image in both environments and vary only:
- `DATABASE_URL`
- secrets such as `SECRET_KEY` and `TOKEN_ENCRYPTION_SECRET`
- public MiniMax credentials
- ingress and TLS configuration outside the container

## Promotion Rules

- Build once and promote the same image digest from staging to production.
- Do not use SQLite outside local development.
- Keep at least one worker process deployed anywhere the web tier can enqueue jobs.
