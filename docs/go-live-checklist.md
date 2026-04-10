# SpecForge Go-Live Checklist & Incident Readiness

## Pre-Launch Validation

### Infrastructure
- [x] Docker image builds and pushes via CI
- [x] docker-compose.yml declares web, worker, postgres
- [x] Health endpoints (`/health/live`, `/health/ready`) operational
- [ ] TLS certificates provisioned for production domain
- [ ] DNS records configured (A/CNAME)
- [ ] Database backups scheduled (pg_dump daily + WAL archiving)
- [ ] Staging environment mirrors production config

### Security
- [x] Secrets in environment variables (not source control)
- [x] OAuth tokens encrypted at rest (Fernet)
- [x] Rate limiting on all public endpoints
- [x] Content-length enforcement
- [x] Session cookies hardened (HttpOnly, SameSite=Lax)
- [ ] Penetration test completed
- [ ] Dependency scan clean (bandit, pip-audit, detect-secrets)

### Data & Privacy
- [x] Terms of Service published
- [x] Privacy Policy published
- [x] Acceptable Use Policy published
- [x] Data export endpoint functional
- [x] Data deletion endpoint functional with confirmation

### Monitoring
- [x] Structured JSON logging enabled
- [x] Metrics endpoint (`/metrics`) operational
- [x] Job lifecycle logging
- [x] Product analytics event tracking
- [ ] Alerting thresholds configured (latency p99 > 5s, error rate > 1%, queue backlog > 100)

### Feature Flags
| Flag | Default | Description | Kill Switch |
|------|---------|-------------|-------------|
| `ai_enhancement` | `true` | Enable AI-powered PRD enhancement | Set env `AI_ENHANCEMENT_ENABLED=false` |
| `minimax_oauth` | `false` | Enable MiniMax OAuth flow | Set env `MINIMAX_OAUTH_ENABLED=false` |
| `export_sharing` | `true` | Enable shareable export links | Set env `EXPORT_SHARING_ENABLED=false` |
| `analytics_tracking` | `true` | Enable product analytics | Set env `ANALYTICS_ENABLED=false` |
| `quota_enforcement` | `true` | Enforce billing plan quotas | Set env `QUOTA_ENFORCEMENT=soft` |

## Rollback Procedure

### 1. Quick Rollback (Docker)
```bash
# Stop current deployment
docker-compose down

# Pull previous image tag
docker pull specforge:$(git rev-parse HEAD~1)

# Restart with previous version
docker-compose up -d

# Verify health
curl -f http://localhost:5000/health/live
curl -f http://localhost:5000/health/ready
```

### 2. Database Rollback
```bash
# Identify last known-good migration
psql -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 5;"

# Rollback specific migration if needed
psql -f migrations/rollback_XXXX.sql
```

### 3. Feature Flag Kill Switches
If a new feature causes issues, disable via environment variable:
```bash
export AI_ENHANCEMENT_ENABLED=false
export EXPORT_SHARING_ENABLED=false
```

## Incident Response Runbook

### Scenario 1: AI Provider Outage
**Symptoms:** All AI-enhanced analyses return 503 or fallback mode.
1. Check `GET /health/ready` — verify `providers` check status
2. Check logs for `MiniMax API call failed` errors
3. If provider is down:
   - Set `AI_ENHANCEMENT_ENABLED=false` to disable AI enhancement
   - Users will receive rule-based fallback automatically
   - Monitor error rate drops
4. When provider recovers:
   - Re-enable `AI_ENHANCEMENT_ENABLED=true`
   - Verify AI enhancement works with test analysis

### Scenario 2: Database Connection Failure
**Symptoms:** `/health/ready` returns 503, all database-dependent endpoints fail.
1. Check postgres container status: `docker-compose ps postgres`
2. Check postgres logs: `docker-compose logs postgres`
3. If postgres is down:
   - Restart: `docker-compose restart postgres`
   - Check data volume: `docker volume ls`
4. If data corruption suspected:
   - Restore from backup: `pg_restore -d specforge latest.dump`
   - Run migrations: `docker-compose restart web`

### Scenario 3: Queue Backlog Critical
**Symptoms:** `/health/ready` returns 503 with `queue:warning` or `queue:critical`.
1. Check backlog: `GET /health/ready` — inspect `checks[].details.queued`
2. Scale workers: `docker-compose up -d --scale worker=3`
3. Monitor queue drain: watch `/health/ready` until `queued < warning_threshold`
4. If backlog doesn't drain:
   - Check worker logs: `docker-compose logs worker`
   - Restart workers: `docker-compose restart worker`

### Scenario 4: Rate Limit Spike
**Symptoms:** Sudden increase in 429 responses, user complaints about throttling.
1. Check metrics: `GET /metrics` — inspect `rate_limit_exceeded_total`
2. If legitimate traffic surge:
   - Increase rate limits via env vars: `RATE_LIMIT_ANALYZE=50`
3. If abuse detected:
   - Review logs for offending IPs/sessions
   - Consider IP-level blocking at WAF/proxy layer

### Scenario 5: Data Breach or Unauthorized Access
**Symptoms:** Suspicious access patterns, leaked credentials.
1. **IMMEDIATE:** Rotate all secrets:
   ```bash
   export SECRET_KEY=$(openssl rand -hex 32)
   export TOKEN_ENCRYPTION_SECRET=$(openssl rand -hex 32)
   docker-compose restart web
   ```
2. Revoke all active sessions (truncate `auth_session_credentials`)
3. Notify affected users per privacy policy
4. Conduct forensic analysis of access logs

## Post-Launch Monitoring

### Key Metrics to Watch (first 7 days)
| Metric | Threshold | Alert Action |
|--------|-----------|-------------|
| Request latency p99 | < 3000ms | Investigate slow endpoints |
| Error rate (5xx) | < 1% | Check logs, restart if needed |
| Queue depth | < 50 | Scale workers |
| Analysis success rate | > 95% | Check provider health |
| Export success rate | > 99% | Verify disk space |
| Active workspaces | Monitor growth | Normal |

### Daily Checks (first week)
- [ ] Review error logs for new patterns
- [ ] Check queue backlog at peak hours
- [ ] Verify backup completion
- [ ] Monitor user feedback and support tickets
- [ ] Check provider API status pages

## Launch Communication Plan

### Internal
- Engineering on-call rotation assigned
- Slack channel `#specforge-launch` created
- PagerDuty escalation policy configured

### External
- Status page: status.specforge.dev
- Incident communication template prepared
- Post-launch survey for early users

---

**Last updated:** 2026-04-10
**Owner:** Engineering Lead
**Next review:** 2026-04-17 (1 week post-launch)
