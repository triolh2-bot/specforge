CREATE TABLE IF NOT EXISTS analysis_jobs (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    request_id VARCHAR(64),
    analysis_id VARCHAR(36),
    requirements_text TEXT NOT NULL,
    ai_enhance_requested BOOLEAN NOT NULL DEFAULT FALSE,
    ai_provider VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    result_json TEXT
)
