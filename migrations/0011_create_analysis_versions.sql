ALTER TABLE analysis_records
ADD COLUMN current_version_number INTEGER DEFAULT 1;

ALTER TABLE analysis_records
ADD COLUMN approved_version_number INTEGER;

CREATE TABLE IF NOT EXISTS analysis_versions (
    id VARCHAR(36) PRIMARY KEY,
    analysis_id VARCHAR(36) NOT NULL,
    workspace_id VARCHAR(36) NOT NULL,
    version_number INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    product_brief_json TEXT NOT NULL,
    clarification_questions_json TEXT NOT NULL,
    prd_document_json TEXT NOT NULL,
    generation_run_json TEXT NOT NULL,
    legacy_prd_json TEXT NOT NULL,
    section_diffs_json TEXT,
    approval_state VARCHAR(16) NOT NULL DEFAULT 'draft',
    approved_at TIMESTAMP NULL,
    CONSTRAINT fk_analysis_versions_analysis_id FOREIGN KEY (analysis_id) REFERENCES analysis_records(id),
    CONSTRAINT uq_analysis_versions_analysis_id_version UNIQUE (analysis_id, version_number)
);
