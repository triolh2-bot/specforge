-- Migration 0007: Create quota_usage and workspace_subscriptions tables
-- Uses CURRENT_TIMESTAMP for cross-database compatibility (SQLite + PostgreSQL).

CREATE TABLE IF NOT EXISTS quota_usage (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    amount INTEGER NOT NULL DEFAULT 1,
    used_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quota_workspace ON quota_usage(workspace_id);
CREATE INDEX IF NOT EXISTS idx_quota_metric ON quota_usage(metric);
CREATE INDEX IF NOT EXISTS idx_quota_used_at ON quota_usage(used_at);

CREATE TABLE IF NOT EXISTS workspace_subscriptions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL UNIQUE,
    plan TEXT NOT NULL DEFAULT 'free',
    status TEXT NOT NULL DEFAULT 'active',
    provider TEXT,
    provider_subscription_id TEXT,
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    canceled_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sub_workspace ON workspace_subscriptions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_sub_plan ON workspace_subscriptions(plan);
CREATE INDEX IF NOT EXISTS idx_sub_status ON workspace_subscriptions(status);
