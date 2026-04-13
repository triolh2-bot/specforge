CREATE TABLE IF NOT EXISTS analysis_records (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    request_id VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'completed',
    requirements_text TEXT NOT NULL,
    ai_enhance_requested BOOLEAN NOT NULL DEFAULT FALSE,
    ai_provider VARCHAR(64),
    domain VARCHAR(64) NOT NULL,
    rms INTEGER NOT NULL,
    implied_users_json TEXT NOT NULL,
    missing_features_json TEXT NOT NULL,
    clarification_questions_json TEXT NOT NULL,
    conflicts_json TEXT NOT NULL,
    prd_json TEXT NOT NULL,
    ai_enhanced_json TEXT
)
