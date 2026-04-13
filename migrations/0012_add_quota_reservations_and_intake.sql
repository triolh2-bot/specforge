ALTER TABLE analysis_records
ADD COLUMN intake_json TEXT;

ALTER TABLE analysis_jobs
ADD COLUMN intake_json TEXT;

ALTER TABLE analysis_jobs
ADD COLUMN quota_reservations_json TEXT;

CREATE TABLE IF NOT EXISTS quota_reservations (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(36) NOT NULL,
    metric VARCHAR(64) NOT NULL,
    reservation_key VARCHAR(64) NOT NULL,
    amount INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(16) NOT NULL DEFAULT 'reserved',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    consumed_at TIMESTAMP NULL,
    released_at TIMESTAMP NULL,
    CONSTRAINT uq_quota_reservations_key UNIQUE (reservation_key)
);
