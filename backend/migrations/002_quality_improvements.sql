-- Migration: Add Quality Scoring, Deduplication, and Vector Search Infrastructure
-- Date: May 25, 2026
-- Purpose: Foundation for intelligent job discovery system

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- For similarity searches

-- ============================================================================
-- 1. DUPLICATE CLUSTER MANAGEMENT
-- ============================================================================

CREATE TABLE IF NOT EXISTS duplicate_clusters (
    id SERIAL PRIMARY KEY,
    primary_job_id INT REFERENCES jobs(id) ON DELETE CASCADE,
    cluster_hash VARCHAR(64) UNIQUE NOT NULL,
    duplicate_count INT DEFAULT 1,
    match_type VARCHAR(20) DEFAULT 'unknown', -- 'exact', 'fuzzy', 'semantic'
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS duplicate_members (
    id SERIAL PRIMARY KEY,
    cluster_id INT REFERENCES duplicate_clusters(id) ON DELETE CASCADE,
    job_id INT REFERENCES jobs(id) ON DELETE CASCADE,
    similarity_score FLOAT,
    match_type VARCHAR(20), -- 'exact', 'fuzzy', 'semantic'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cluster_id, job_id)
);

CREATE INDEX idx_duplicate_clusters_primary_job ON duplicate_clusters(primary_job_id);
CREATE INDEX idx_duplicate_clusters_hash ON duplicate_clusters(cluster_hash);
CREATE INDEX idx_duplicate_members_cluster ON duplicate_members(cluster_id);
CREATE INDEX idx_duplicate_members_job ON duplicate_members(job_id);

-- ============================================================================
-- 2. JOB SCORING COMPONENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS job_scoring (
    id SERIAL PRIMARY KEY,
    job_id INT UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    
    -- Individual component scores (0-10)
    source_trust_score FLOAT DEFAULT 5.0,
    freshness_score FLOAT DEFAULT 5.0,
    quality_score FLOAT DEFAULT 5.0,
    company_score FLOAT DEFAULT 5.0,
    remote_authenticity_score FLOAT DEFAULT 5.0,
    salary_quality_score FLOAT DEFAULT 5.0,
    
    -- Composite score (0-10)
    final_score FLOAT DEFAULT 5.0,
    
    -- Ranking & position
    ranking_position INT,
    percentile FLOAT,
    
    -- Metadata
    scoring_version INT DEFAULT 1,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_job_scoring_final_score ON job_scoring(final_score DESC);
CREATE INDEX idx_job_scoring_job_id ON job_scoring(job_id);
CREATE INDEX idx_job_scoring_updated ON job_scoring(updated_at DESC);

-- ============================================================================
-- 3. SOURCE CONFIGURATION & HEALTH METRICS
-- ============================================================================

CREATE TABLE IF NOT EXISTS source_metadata (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) UNIQUE NOT NULL,
    
    -- Trust & quality scores
    trust_score FLOAT DEFAULT 5.0 CHECK (trust_score >= 0 AND trust_score <= 10),
    spam_score FLOAT DEFAULT 0.0 CHECK (spam_score >= 0 AND spam_score <= 10),
    freshness_score FLOAT DEFAULT 5.0 CHECK (freshness_score >= 0 AND freshness_score <= 10),
    duplicate_ratio FLOAT DEFAULT 0.0 CHECK (duplicate_ratio >= 0 AND duplicate_ratio <= 1),
    
    -- Status & monitoring
    is_active BOOLEAN DEFAULT TRUE,
    last_successful_run TIMESTAMP,
    last_failed_run TIMESTAMP,
    failure_count INT DEFAULT 0 CHECK (failure_count >= 0),
    consecutive_failures INT DEFAULT 0,
    total_jobs_ingested INT DEFAULT 0,
    successful_ingestions INT DEFAULT 0,
    
    -- Configuration
    source_type VARCHAR(50), -- 'api', 'rss', 'graphql', 'web_scrape'
    api_endpoint VARCHAR(500),
    rate_limit_per_hour INT,
    retry_strategy JSONB,
    config JSONB,
    
    -- Priority & scheduling
    priority INT DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    check_interval_minutes INT DEFAULT 60,
    next_scheduled_run TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_source_metadata_active ON source_metadata(is_active);
CREATE INDEX idx_source_metadata_priority ON source_metadata(priority DESC);
CREATE INDEX idx_source_metadata_next_run ON source_metadata(next_scheduled_run);

-- ============================================================================
-- 4. COMPANY LEGITIMACY SCORING
-- ============================================================================

CREATE TABLE IF NOT EXISTS company_scores (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) UNIQUE NOT NULL,
    domain VARCHAR(255),
    
    -- Trust metrics
    trust_score FLOAT DEFAULT 5.0,
    domain_authority INT DEFAULT 0 CHECK (domain_authority >= 0 AND domain_authority <= 100),
    company_age_days INT,
    
    -- Verification signals
    linkedin_presence BOOLEAN,
    linkedin_employee_count INT,
    linkedin_url VARCHAR(500),
    website_valid BOOLEAN,
    has_careers_page BOOLEAN,
    
    -- Hiring signals
    hiring_consistency FLOAT DEFAULT 0.5,
    total_jobs_posted INT DEFAULT 0,
    active_jobs_now INT DEFAULT 0,
    avg_jobs_per_month FLOAT DEFAULT 0.0,
    
    -- Ecosystem
    is_startup BOOLEAN DEFAULT FALSE,
    is_yc_backed BOOLEAN DEFAULT FALSE,
    is_in_crunchbase BOOLEAN DEFAULT FALSE,
    
    -- Verification status
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    verification_notes TEXT,
    
    -- Fraud detection
    spam_flags INT DEFAULT 0,
    last_verification TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_company_scores_trust ON company_scores(trust_score DESC);
CREATE INDEX idx_company_scores_verified ON company_scores(is_verified);
CREATE INDEX idx_company_scores_startup ON company_scores(is_startup);
CREATE INDEX idx_company_scores_domain ON company_scores(domain);

-- ============================================================================
-- 5. JOB EMBEDDINGS FOR SEMANTIC SEARCH
-- ============================================================================

CREATE TABLE IF NOT EXISTS job_embeddings (
    id SERIAL PRIMARY KEY,
    job_id INT UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    
    -- Embedding vector (384 dimensions for all-MiniLM-L6-v2)
    embedding vector(384) NOT NULL,
    
    -- Metadata
    model_name VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2',
    embedding_version INT DEFAULT 1,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_job_embeddings_vector ON job_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_job_embeddings_job_id ON job_embeddings(job_id);

-- ============================================================================
-- 6. NORMALIZED JOB DATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS jobs_normalized (
    id SERIAL PRIMARY KEY,
    job_id INT UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    
    -- Normalized fields
    normalized_title VARCHAR(255),
    normalized_company VARCHAR(255),
    normalized_location VARCHAR(255),
    normalized_description TEXT,
    
    -- Tokenized fields for search
    title_tokens TEXT[],
    company_tokens TEXT[],
    location_tokens TEXT[],
    
    -- Extracted features
    tech_stack TEXT[],
    skills TEXT[],
    frameworks TEXT[],
    tools TEXT[],
    
    -- Classification
    seniority VARCHAR(50), -- 'junior', 'mid', 'senior', 'lead'
    role_category VARCHAR(100), -- 'backend', 'frontend', 'fullstack', 'devops', etc.
    domain VARCHAR(100), -- 'web', 'mobile', 'data', 'infrastructure', etc.
    
    -- Remote classification
    remote_type VARCHAR(50), -- 'true-remote', 'hybrid', 'location-restricted'
    timezone_required VARCHAR(100),
    timezone_flexibility VARCHAR(50), -- 'strict', 'flexible', 'timezone-agnostic'
    
    -- Compensation
    salary_min INT,
    salary_max INT,
    salary_currency VARCHAR(3),
    salary_period VARCHAR(20), -- 'annual', 'hourly'
    salary_transparency_score FLOAT, -- 0-10 based on completeness
    equity_offered BOOLEAN,
    
    -- Employment details
    employment_type VARCHAR(50), -- 'full-time', 'contract', 'freelance'
    visa_sponsored BOOLEAN,
    relocation_assistance BOOLEAN,
    
    -- Derived fields
    is_entry_level BOOLEAN,
    is_startup_job BOOLEAN,
    has_rich_description BOOLEAN,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jobs_normalized_title ON jobs_normalized(normalized_title);
CREATE INDEX idx_jobs_normalized_company ON jobs_normalized(normalized_company);
CREATE INDEX idx_jobs_normalized_seniority ON jobs_normalized(seniority);
CREATE INDEX idx_jobs_normalized_role_category ON jobs_normalized(role_category);
CREATE INDEX idx_jobs_normalized_remote ON jobs_normalized(remote_type);

-- Full-text search indexes on normalized data
CREATE INDEX idx_jobs_normalized_title_fts ON jobs_normalized USING GIN(to_tsvector('english', normalized_title));
CREATE INDEX idx_jobs_normalized_desc_fts ON jobs_normalized USING GIN(to_tsvector('english', COALESCE(normalized_description, '')));

-- ============================================================================
-- 7. INGESTION AUDIT TRAIL
-- ============================================================================

CREATE TABLE IF NOT EXISTS ingestion_audit (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,
    run_id UUID NOT NULL,
    
    -- Counts
    jobs_fetched INT DEFAULT 0,
    jobs_new INT DEFAULT 0,
    jobs_duplicated INT DEFAULT 0,
    jobs_spam INT DEFAULT 0,
    jobs_stored INT DEFAULT 0,
    
    -- Timing
    duration_seconds INT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Status
    status VARCHAR(20) CHECK (status IN ('success', 'partial', 'failed')),
    error_message TEXT,
    error_type VARCHAR(100),
    
    -- Metadata
    metadata JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ingestion_audit_source ON ingestion_audit(source_name);
CREATE INDEX idx_ingestion_audit_run_id ON ingestion_audit(run_id);
CREATE INDEX idx_ingestion_audit_status ON ingestion_audit(status);
CREATE INDEX idx_ingestion_audit_created ON ingestion_audit(created_at DESC);

-- ============================================================================
-- 8. ENHANCE EXISTING JOBS TABLE
-- ============================================================================

-- Add columns to existing jobs table
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS normalized_title VARCHAR(255);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS duplicate_group_id INT REFERENCES duplicate_clusters(id);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS final_score FLOAT DEFAULT 0.0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_trust_score FLOAT DEFAULT 5.0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS freshness_score FLOAT DEFAULT 5.0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS quality_score FLOAT DEFAULT 5.0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS remote_authenticity VARCHAR(50);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS spam_indicator FLOAT DEFAULT 0.0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS company_score FLOAT DEFAULT 5.0;

-- Indexes on jobs table
CREATE INDEX IF NOT EXISTS idx_jobs_final_score ON jobs(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_freshness ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_duplicate_group ON jobs(duplicate_group_id);
CREATE INDEX IF NOT EXISTS idx_jobs_normalized_title ON jobs(normalized_title);
CREATE INDEX IF NOT EXISTS idx_jobs_is_duplicate ON jobs(is_duplicate);

-- Full-text search on jobs
CREATE INDEX IF NOT EXISTS idx_jobs_title_fts ON jobs USING GIN(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_jobs_company_fts ON jobs USING GIN(to_tsvector('english', company));
CREATE INDEX IF NOT EXISTS idx_jobs_description_fts ON jobs USING GIN(to_tsvector('english', COALESCE(description, '')));

-- ============================================================================
-- 9. QUALITY METRICS MATERIALIZED VIEW
-- ============================================================================

CREATE OR REPLACE VIEW quality_metrics_view AS
SELECT 
    DATE(jobs.created_at) as metric_date,
    jobs.source,
    COUNT(*) as total_jobs,
    COUNT(*) FILTER (WHERE jobs.is_duplicate) as duplicate_count,
    COUNT(*) FILTER (WHERE jobs.spam_indicator > 0.5) as spam_count,
    COUNT(*) FILTER (WHERE jobs.final_score > 7.0) as high_quality_count,
    AVG(jobs.final_score) as avg_quality_score,
    AVG(EXTRACT(DAY FROM NOW() - jobs.created_at)) as avg_age_days,
    ROUND(100.0 * COUNT(*) FILTER (WHERE jobs.is_duplicate) / COUNT(*), 2) as duplicate_ratio,
    ROUND(100.0 * COUNT(*) FILTER (WHERE jobs.spam_indicator > 0.5) / COUNT(*), 2) as spam_ratio
FROM jobs
GROUP BY DATE(jobs.created_at), jobs.source
ORDER BY metric_date DESC, jobs.source;

-- ============================================================================
-- 10. VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Top-quality recent jobs (non-duplicates, high score, fresh)
CREATE OR REPLACE VIEW recent_quality_jobs AS
SELECT 
    j.*,
    smd.trust_score as source_trust,
    js.final_score as computed_score,
    CASE WHEN j.is_duplicate THEN 'Duplicate' ELSE 'Original' END as status
FROM jobs j
LEFT JOIN source_metadata smd ON j.source = smd.source_name
LEFT JOIN job_scoring js ON j.id = js.job_id
WHERE j.is_duplicate = FALSE
    AND j.spam_indicator < 0.5
    AND j.created_at > NOW() - INTERVAL '30 days'
ORDER BY j.created_at DESC;

-- Duplicate job clusters with metrics
CREATE OR REPLACE VIEW duplicate_analysis AS
SELECT 
    dc.id as cluster_id,
    dc.cluster_hash,
    COUNT(dm.id) + 1 as total_duplicates,
    MAX(js.final_score) as best_score,
    STRING_AGG(DISTINCT j.source, ', ') as source_list,
    dc.created_at
FROM duplicate_clusters dc
LEFT JOIN duplicate_members dm ON dc.id = dm.cluster_id
LEFT JOIN jobs j ON dm.job_id = j.id
LEFT JOIN job_scoring js ON j.id = js.job_id
GROUP BY dc.id, dc.cluster_hash, dc.created_at
ORDER BY total_duplicates DESC;

-- ============================================================================
-- 11. CREATE HELPER FUNCTIONS
-- ============================================================================

-- Function to calculate composite score
CREATE OR REPLACE FUNCTION calculate_final_score(
    source_trust FLOAT,
    freshness FLOAT,
    quality FLOAT,
    company FLOAT,
    remote_auth FLOAT,
    salary_quality FLOAT
) RETURNS FLOAT AS $$
BEGIN
    RETURN (
        source_trust * 0.20 +
        freshness * 0.25 +
        quality * 0.20 +
        company * 0.15 +
        remote_auth * 0.10 +
        salary_quality * 0.10
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to detect duplicate cluster hash
CREATE OR REPLACE FUNCTION generate_duplicate_hash(
    normalized_title VARCHAR,
    normalized_company VARCHAR,
    normalized_location VARCHAR
) RETURNS VARCHAR AS $$
BEGIN
    RETURN MD5(
        LOWER(CONCAT(
            COALESCE(normalized_title, ''),
            '|',
            COALESCE(normalized_company, ''),
            '|',
            COALESCE(normalized_location, '')
        ))
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- 12. INITIALIZE SOURCE METADATA
-- ============================================================================

-- Insert default source configurations
INSERT INTO source_metadata (source_name, trust_score, source_type, priority, check_interval_minutes, config)
VALUES
    -- High-priority API sources
    ('github_jobs', 9.0, 'api', 10, 30, '{"name": "GitHub Jobs"}'),
    ('devto_jobs', 9.0, 'api', 10, 30, '{"name": "Dev.to Jobs"}'),
    ('wellfound', 8.5, 'graphql', 10, 60, '{"name": "Wellfound/AngelList"}'),
    ('indie_hackers', 9.5, 'web_scrape', 10, 60, '{"name": "Indie Hackers"}'),
    ('greenhouse', 9.5, 'api', 9, 120, '{"name": "Greenhouse ATS"}'),
    ('authentic_jobs', 8.5, 'api', 9, 60, '{"name": "Authentic Jobs"}'),
    
    -- Medium-priority sources
    ('remotive', 6.5, 'api', 8, 60, '{"name": "Remotive"}'),
    ('weworkremotely', 7.5, 'api', 8, 60, '{"name": "We Work Remotely"}'),
    ('stackoverflow', 7.0, 'rss', 7, 120, '{"name": "Stack Overflow"}'),
    
    -- Legacy sources (lower priority)
    ('remoteok', 5.0, 'rss', 5, 120, '{"name": "Remote OK"}'),
    ('working_nomads', 4.5, 'rss', 4, 180, '{"name": "Working Nomads"}'),
    ('himalayas', 4.0, 'rss', 4, 180, '{"name": "Himalayas"}')
ON CONFLICT (source_name) DO NOTHING;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Run this migration with: psql -f migrations/002_quality_improvements.sql
