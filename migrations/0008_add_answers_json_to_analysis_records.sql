-- Add answers_json column to analysis_records to store user QA during refinement
ALTER TABLE analysis_records
ADD COLUMN answers_json TEXT;
