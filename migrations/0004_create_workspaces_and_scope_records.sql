CREATE TABLE IF NOT EXISTS workspaces (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    name VARCHAR(128) NOT NULL
);

INSERT OR IGNORE INTO workspaces (id, name) VALUES ('legacy-workspace', 'Legacy Workspace');

ALTER TABLE analysis_records ADD COLUMN workspace_id VARCHAR(36) NOT NULL DEFAULT 'legacy-workspace';
ALTER TABLE analysis_jobs ADD COLUMN workspace_id VARCHAR(36) NOT NULL DEFAULT 'legacy-workspace';
ALTER TABLE auth_session_credentials ADD COLUMN workspace_id VARCHAR(36) NOT NULL DEFAULT 'legacy-workspace';
ALTER TABLE auth_session_credentials ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'owner';
