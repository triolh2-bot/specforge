# SpecForge Deployment & Infrastructure Guide

## Environment Parity

| Aspect | Staging | Production |
|--------|---------|------------|
| Database | PostgreSQL 16 (single) | PostgreSQL 16 (HA optional) |
| Web replicas | 1 | 2+ |
| Worker replicas | 1 | 1+ |
| Quota enforcement | soft | strict |
| Log level | DEBUG | INFO/WARN |
| TLS | Self-signed (or staging cert) | Valid CA-signed cert |
| Domain | staging.specforge.dev | specforge.dev |
| Rate limits | Relaxed (2x prod) | Strict |
| Feature flags | All enabled | Controlled per env |

## Deployment Targets

### Docker Compose (Recommended for single-host)

```bash
# Staging
docker-compose -f docker-compose.staging.yml up -d --build

# Verify
docker-compose -f docker-compose.staging.yml ps
curl http://localhost:5001/health/ready

# Production
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Verify
curl -f https://specforge.dev/health/ready
```

### Kubernetes (Multi-host)

```yaml
# k8s/deployment.yaml
#
# NOTE: Replace ${APP_VERSION} with a concrete image tag before applying.
# Example: APP_VERSION=1.2.3 envsubst < k8s/deployment.yaml | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: specforge-web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: specforge-web
  template:
    metadata:
      labels:
        app: specforge-web
    spec:
      containers:
      - name: web
        image: specforge:${APP_VERSION}
        ports:
        - containerPort: 5000
        envFrom:
        - secretRef:
            name: specforge-secrets
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 15
        livenessProbe:
          httpGet:
            path: /health/live
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 30
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: specforge-web
spec:
  selector:
    app: specforge-web
  ports:
  - port: 80
    targetPort: 5000
  type: ClusterIP
```

## TLS Configuration

### Nginx Reverse Proxy (Recommended)

```nginx
server {
    listen 443 ssl http2;
    server_name specforge.dev;

    ssl_certificate     /etc/letsencrypt/live/specforge.dev/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/specforge.dev/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:5000/health;
    }
}

server {
    listen 80;
    server_name specforge.dev;
    return 301 https://$host$request_uri;
}
```

## Database Backup Strategy

```bash
#!/bin/bash
# scripts/backup_postgres.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
pg_dump "$DATABASE_URL" | gzip > "${BACKUP_DIR}/specforge_${DATE}.sql.gz"

# Retain only last 7 days of backups
find "${BACKUP_DIR}" -name "specforge_*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_DIR}/specforge_${DATE}.sql.gz"
```

Add to crontab: `0 2 * * * /app/scripts/backup.sh`

## Environment Variables (Production)

Required variables (set via `.env.prod` or secret manager):

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_PASSWORD` | Database password | `openssl rand -hex 32` |
| `SECRET_KEY` | Flask secret key | `openssl rand -hex 32` |
| `TOKEN_ENCRYPTION_SECRET` | Fernet encryption key | `openssl rand -hex 32` |
| `OPENROUTER_API_KEY` | OpenRouter API key | From OpenRouter |
| `OPENROUTER_MODEL` | OpenRouter model | `openai/gpt-4o-mini` |
| `OPENROUTER_SITE_URL` | HTTP-Referer for OpenRouter | `https://specforge.dev` |
| `APP_VERSION` | Application version | `git rev-parse --short HEAD` |

## Worker Configuration Reloads

The worker process reads environment variables at startup. If you change `.env` or secret values (API keys, model, quotas),
restart the worker container or process to pick up new configuration.

## Monitoring & Alerting

### Health Check Endpoints

| Endpoint | Purpose | Alert if |
|----------|---------|----------|
| `/health/live` | Process is alive | Returns non-200 |
| `/health/ready` | Dependencies healthy | Returns 503 for > 2 min |
| `/metrics` | Prometheus metrics | Scrape fails for > 5 min |

### Recommended Alerts

| Metric | Threshold | Severity |
|--------|-----------|----------|
| Request latency p99 | > 5000ms | Warning |
| Request latency p99 | > 10000ms | Critical |
| 5xx error rate | > 1% | Warning |
| 5xx error rate | > 5% | Critical |
| Queue backlog | > 100 | Warning |
| Queue backlog | > 500 | Critical |
| Failed jobs | > 25 | Warning |
| Disk usage (postgres) | > 80% | Warning |
| Disk usage (postgres) | > 95% | Critical |

## Rollback Procedure

See `docs/go-live-checklist.md` for full rollback runbook.

Quick rollback:
```bash
# Revert to previous image
docker-compose -f docker-compose.prod.yml --env-file .env.prod down
docker tag specforge:previous specforge:latest
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
```
