# Deployment

## Reference Runtime

Use a two-process container model:

- `web` runs `gunicorn app:app` and serves HTTP traffic.
- `worker` runs `python -m specforge.worker` and processes queued analysis jobs.
- `db` is a managed PostgreSQL instance in production; the compose file is a local stand-in.

## Infrastructure Layout

- Terminate TLS at a load balancer or ingress controller.
- Route public traffic only to the web process.
- Keep the worker private on the internal network.
- Store persistent state in PostgreSQL and, when exports are added, durable object storage.
- Keep environment promotion explicit: dev, staging, and production should have separate secrets and databases.

## Runtime Configuration

- Set `DATABASE_URL` to a PostgreSQL DSN.
- Set `SECRET_KEY` and `TOKEN_ENCRYPTION_SECRET` to long random values.
- Configure `MINIMAX_CLIENT_ID`, `MINIMAX_CLIENT_SECRET`, `MINIMAX_REDIRECT_URI`, or `MINIMAX_API_KEY` as required.
- Set `APP_VERSION` so health checks report the deployed release.

## Local Development

```bash
docker compose up --build
```

The web UI is available on `http://localhost:5000`.

## Production Checklist

1. Confirm the database migration path is applied before traffic is routed.
2. Confirm `/health/live` and `/health/ready` both pass from inside the cluster.
3. Confirm the worker is running and queue backlog remains below the warning threshold.
4. Confirm structured logs and metrics are shipping to the observability backend.
5. Confirm secrets are injected by the platform, not stored in the image.
