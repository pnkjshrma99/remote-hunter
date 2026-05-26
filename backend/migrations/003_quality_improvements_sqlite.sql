-- Migration: Add Quality Scoring, Deduplication Infrastructure (SQLite version)
-- Date: May 25, 2026
-- Purpose: Foundation for intelligent job discovery system (SQLite compatible)
-- Note: Vector search components (pgvector) skipped for SQLite compatibility

-- ============================================================================
-- 1. DUPLICATE CLUSTER MANAGEMENT
-- ============================================================================

CREATE TABLE IF NOT EXISTS duplicate_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    primary_job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    cluster_hash TEXT UNIQUE NOT NULL,
    duplicate_count INTEGER DEFAULT 1,
    match_type TEXT DEFAULT 'unknown', -- 'exact', 'fuzzy', 'semantic'
    metadata TEXT, -- JSON stored as TEXT in SQLite
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS duplicate_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id INTEGER REFERENCES duplicate_clusters(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    similarity_score REAL,
    match_type TEXT, -- 'exact', 'fuzzy', 'semantic'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cluster_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_duplicate_clusters_primary_job ON duplicate_clusters(primary_job_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_clusters_hash ON duplicate_clusters(cluster_hash);
CREATE INDEX IF NOT EXISTS idx_duplicate_members_cluster ON duplicate_members(cluster_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_members_job ON duplicate_members(job_id);

-- ============================================================================
-- 2. JOB SCORING COMPONENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS job_scoring (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    
    -- Individual component scores (0-10)
    source_trust_score REAL DEFAULT 5.0,
    freshness_score REAL DEFAULT 5.0,
    quality_score REAL DEFAULT 5.0,
    company_score REAL DEFAULT 5.0,
    remote_authenticity_score REAL DEFAULT 5.0,
    salary_quality_score REAL DEFAULT 5.0,
    
    -- Composite score (0-10)
    final_score REAL DEFAULT 5.0,
    
    -- Ranking & position
    ranking_position INTEGER,
    percentile REAL,
    
    -- Metadata
    scoring_version INTEGER DEFAULT 1,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_job_scoring_final_score ON job_scoring(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_job_scoring_job_id ON job_scoring(job_id);
CREATE INDEX IF NOT EXISTS idx_job_scoring_updated ON job_scoring(updated_at DESC);

-- ============================================================================
-- 3. SOURCE CONFIGURATION & HEALTH METRICS
-- ============================================================================

CREATE TABLE IF NOT EXISTS source_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT UNIQUE NOT NULL,
    
    -- Trust & quality scores
    trust_score REAL DEFAULT 5.0 CHECK (trust_score >= 0 AND trust_score <= 10),
    spam_score REAL DEFAULT 0.0 CHECK (spam_score >= 0 AND spam_score <= 10),
    freshness_score REAL DEFAULT 5.0 CHECK (freshness_score >= 0 AND freshness_score <= 10),
    duplicate_ratio REAL DEFAULT 0.0 CHECK (duplicate_ratio >= 0 AND duplicate_ratio <= 1),
    
    -- Status & monitoring
    is_active INTEGER DEFAULT 1, -- Boolean as INTEGER
    last_successful_run TIMESTAMP,
    last_failed_run TIMESTAMP,
    failure_count INTEGER DEFAULT 0 CHECK (failure_count >= 0),
    consecutive_failures INTEGER DEFAULT 0,
    total_jobs_ingested INTEGER DEFAULT 0,
    successful_ingestions INTEGER DEFAULT 0,
    
    -- Configuration
    source_type TEXT, -- 'api', 'rss', 'graphql', 'web_scrape'
    api_endpoint TEXT,
    rate_limit_per_hour INTEGER,
    retry_strategy TEXT, -- JSON stored as TEXT
    config TEXT, -- JSON stored as TEXT
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_source_metadata_name ON source_metadata(source_name);
CREATE INDEX IF NOT EXISTS idx_source_metadata_active ON source_metadata(is_active);
CREATE INDEX IF NOT EXISTS idx_source_metadata_trust ON source_metadata(trust_score DESC);

-- ============================================================================
-- 4. COMPANY LEGITIMACY TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS company_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT UNIQUE,
    domain TEXT,
    trust_score REAL,
    domain_authority INTEGER, -- Ahrefs score 0-100
    company_age_days INTEGER,
    linkedin_presence INTEGER DEFAULT 0, -- Boolean as INTEGER
    hiring_consistency REAL,
    is_verified INTEGER DEFAULT 0, -- Boolean as INTEGER
    is_startup INTEGER DEFAULT 0, -- Boolean as INTEGER
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_company_scores_name ON company_scores(company_name);
CREATE INDEX IF NOT EXISTS idx_company_scores_trust ON company_scores(trust_score DESC);
CREATE INDEX IF NOT EXISTS idx_company_scores_verified ON company_scores(is_verified);

-- ============================================================================
-- 5. JOB EMBEDDINGS (Placeholder for future PostgreSQL migration)
-- ============================================================================

-- Note: Embeddings table skipped for SQLite compatibility
-- Will be added when migrating to PostgreSQL with pgvector

-- ============================================================================
-- 6. NORMALIZED JOB DATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS jobs_normalized (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    normalized_title TEXT,
    normalized_company TEXT,
    normalized_location TEXT,
    title_tokens TEXT, -- JSON array stored as TEXT
    company_tokens TEXT, -- JSON array stored as TEXT
    tech_stack TEXT, -- JSON array stored as TEXT
    seniority TEXT,
    remote_type TEXT, -- 'true-remote', 'hybrid', 'restricted'
    timezone_required TEXT,
    visa_sponsored INTEGER DEFAULT 0, -- Boolean as INTEGER
    employment_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_normalized_job_id ON jobs_normalized(job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_normalized_title ON jobs_normalized(normalized_title);
CREATE INDEX IF NOT EXISTS idx_jobs_normalized_company ON jobs_normalized(normalized_company);

-- ============================================================================
-- 7. INGESTION AUDIT TRAIL
-- ============================================================================

CREATE TABLE IF NOT EXISTS ingestion_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT,
    run_id TEXT, -- UUID stored as TEXT
    jobs_fetched INTEGER,
    jobs_new INTEGER,
    jobs_duplicated INTEGER,
    jobs_spam INTEGER,
    jobs_stored INTEGER,
    duration_seconds INTEGER,
    error_message TEXT,
    status TEXT, -- 'success', 'partial', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ingestion_audit_source ON ingestion_audit(source_name);
CREATE INDEX IF NOT EXISTS idx_ingestion_audit_status ON ingestion_audit(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_audit_started ON ingestion_audit(started_at DESC);

-- ============================================================================
-- 8. MODIFY EXISTING JOBS TABLE
-- ============================================================================

-- Note: Most columns already exist from previous migrations
-- We'll only add columns that don't exist
-- Columns already present: normalized_title, duplicate_group_id, is_duplicate, 
-- final_score, source_trust_score, freshness_score, quality_score, 
-- remote_authenticity, spam_indicator

-- Create indexes (using scraped_at instead of created_at since that's what exists)
CREATE INDEX IF NOT EXISTS idx_jobs_final_score ON jobs(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at ON jobs(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_duplicate_group ON jobs(duplicate_group_id);
CREATE INDEX IF NOT EXISTS idx_jobs_normalized_title ON jobs(normalized_title);

-- ============================================================================
-- 9. VIEWS FOR ANALYTICS
-- ============================================================================

CREATE VIEW IF NOT EXISTS v_job_quality_summary AS
SELECT 
    j.id,
    j.title,
    j.company,
    j.source,
    j.created_at,
    js.final_score,
    js.source_trust_score,
    js.freshness_score,
    js.quality_score,
    js.company_score,
    js.remote_authenticity_score,
    js.salary_quality_score,
    j.is_duplicate,
    j.spam_indicator
FROM jobs j
LEFT JOIN job_scoring js ON j.id = js.job_id
WHERE j.is_duplicate = 0;

CREATE VIEW IF NOT EXISTS v_source_health AS
SELECT 
    source_name,
    trust_score,
    is_active,
    last_successful_run,
    last_failed_run,
    failure_count,
    total_jobs_ingested,
    successful_ingestions,
    duplicate_ratio,
    CASE 
        WHEN failure_count > 5 THEN 'unhealthy'
        WHEN failure_count > 2 THEN 'degraded'
        ELSE 'healthy'
    END as health_status
FROM source_metadata;

CREATE VIEW IF NOT EXISTS v_duplicate_summary AS
SELECT 
    dc.id as cluster_id,
    dc.cluster_hash,
    dc.duplicate_count,
    dc.match_type,
    j.title,
    j.company,
    j.source,
    dc.created_at
FROM duplicate_clusters dc
JOIN jobs j ON dc.primary_job_id = j.id
ORDER BY dc.duplicate_count DESC;

-- ============================================================================
-- 10. HELPER FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_source_metadata_updated_at 
AFTER UPDATE ON source_metadata
BEGIN
    UPDATE source_metadata SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_job_scoring_updated_at 
AFTER UPDATE ON job_scoring
BEGIN
    UPDATE job_scoring SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_company_scores_updated_at 
AFTER UPDATE ON company_scores
BEGIN
    UPDATE company_scores SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_jobs_normalized_updated_at 
AFTER UPDATE ON jobs_normalized
BEGIN
    UPDATE jobs_normalized SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_duplicate_clusters_updated_at 
AFTER UPDATE ON duplicate_clusters
BEGIN
    UPDATE duplicate_clusters SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
