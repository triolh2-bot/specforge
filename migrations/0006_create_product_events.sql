-- Migration 0006: Create product_events table for usage analytics

CREATE TABLE IF NOT EXISTS product_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT,
    analysis_id TEXT,
    request_id TEXT,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    properties_json TEXT,
    occurred_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_event_workspace ON product_events(workspace_id);
CREATE INDEX IF NOT EXISTS idx_event_analysis ON product_events(analysis_id);
CREATE INDEX IF NOT EXISTS idx_event_category ON product_events(category);
CREATE INDEX IF NOT EXISTS idx_event_name ON product_events(name);
CREATE INDEX IF NOT EXISTS idx_event_occurred ON product_events(occurred_at);
