CREATE TABLE IF NOT EXISTS auth_session_credentials (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    auth_session_id VARCHAR(64) NOT NULL UNIQUE,
    provider VARCHAR(32) NOT NULL DEFAULT 'openrouter',
    encrypted_access_token TEXT,
    encrypted_refresh_token TEXT,
    token_expires_at TIMESTAMP
)
;
CREATE INDEX IF NOT EXISTS idx_auth_session_credentials_auth_session_id ON auth_session_credentials (auth_session_id)
