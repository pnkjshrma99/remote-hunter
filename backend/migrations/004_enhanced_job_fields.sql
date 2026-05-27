-- Migration: Add enhanced job fields for new scraping pipeline
-- This adds fields for normalized job schema, relevance scoring, and LLM enrichment

-- Add new normalized fields
ALTER TABLE jobs ADD COLUMN remote_type VARCHAR(32);
ALTER TABLE jobs ADD COLUMN job_type VARCHAR(32);
ALTER TABLE jobs ADD COLUMN experience_min_years INTEGER;
ALTER TABLE jobs ADD COLUMN experience_max_years INTEGER;
ALTER TABLE jobs ADD COLUMN salary_min INTEGER;
ALTER TABLE jobs ADD COLUMN salary_max INTEGER;
ALTER TABLE jobs ADD COLUMN salary_currency VARCHAR(8) DEFAULT 'USD';

-- Add JSON fields for arrays (skills, tags, responsibilities, requirements)
ALTER TABLE jobs ADD COLUMN skills JSON;
ALTER TABLE jobs ADD COLUMN tags JSON;
ALTER TABLE jobs ADD COLUMN responsibilities JSON;
ALTER TABLE jobs ADD COLUMN requirements JSON;

-- Add scoring fields
ALTER TABLE jobs ADD COLUMN relevance_score FLOAT DEFAULT 0.0;
ALTER TABLE jobs ADD COLUMN confidence_score FLOAT DEFAULT 0.0;
ALTER TABLE jobs ADD COLUMN is_likely_fake BOOLEAN DEFAULT FALSE;

-- Create indexes for new fields
CREATE INDEX IF NOT EXISTS ix_jobs_relevance_score ON jobs(relevance_score);
CREATE INDEX IF NOT EXISTS ix_jobs_experience_min_years ON jobs(experience_min_years);
CREATE INDEX IF NOT EXISTS ix_jobs_experience_max_years ON jobs(experience_max_years);
CREATE INDEX IF NOT EXISTS ix_jobs_remote_type ON jobs(remote_type);
CREATE INDEX IF NOT EXISTS ix_jobs_job_type ON jobs(job_type);
