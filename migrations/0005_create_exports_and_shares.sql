-- Migration 0005: Create export_records and share_links tables
-- Uses CURRENT_TIMESTAMP for cross-database compatibility (SQLite + PostgreSQL).

CREATE TABLE IF NOT EXISTS export_records (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    analysis_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    export_format TEXT NOT NULL,
    content TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_length INTEGER NOT NULL DEFAULT 0,
    share_token TEXT UNIQUE,
    share_expires_at TIMESTAMP,
    download_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_export_workspace ON export_records(workspace_id);
CREATE INDEX IF NOT EXISTS idx_export_analysis ON export_records(analysis_id);
CREATE INDEX IF NOT EXISTS idx_export_share_token ON export_records(share_token);

CREATE TABLE IF NOT EXISTS share_links (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    analysis_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    token TEXT NOT NULL UNIQUE,
    access_level TEXT NOT NULL DEFAULT 'view',
    created_by_role TEXT NOT NULL DEFAULT 'owner',
    view_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_share_workspace ON share_links(workspace_id);
CREATE INDEX IF NOT EXISTS idx_share_analysis ON share_links(analysis_id);
CREATE INDEX IF NOT EXISTS idx_share_token ON share_links(token);
