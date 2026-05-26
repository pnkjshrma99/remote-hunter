# Remote Hunter - Production-Grade Architecture V2

**Status**: Production Upgrade Plan  
**Date**: May 25, 2026  
**Target**: High-Quality Job Discovery System

---

## EXECUTIVE SUMMARY

Transform Remote Hunter from an RSS aggregator into a **curated intelligent job discovery engine** that:
- ✅ Prioritizes real, active, high-quality jobs
- ✅ Eliminates 40-50% of duplicates
- ✅ Reduces spam significantly
- ✅ Ranks jobs by trust, freshness, and relevance
- ✅ Scales horizontally with async ingestion
- ✅ Provides vector search and semantic matching

---

## SYSTEM ARCHITECTURE OVERVIEW

```
┌──────────────────────────────────────────────────────────────────────┐
│                   INTELLIGENT JOB DISCOVERY SYSTEM                   │
└──────────────────────────────────────────────────────────────────────┘

PHASE 1: SOURCE INGESTION
┌─────────────────────────────────────────────────────────────────┐
│ Multi-Source Ingestion Layer                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  HIGH-PRIORITY SOURCES (Real-time APIs)                        │
│  ├─ Wellfound/AngelList (GraphQL)                             │
│  ├─ GitHub Jobs (REST API)                                    │
│  ├─ Dev.to Jobs (REST API)                                    │
│  ├─ Indie Hackers (RSS + web)                                 │
│  ├─ ATS Providers:                                            │
│  │  ├─ Greenhouse                                             │
│  │  ├─ Lever                                                  │
│  │  ├─ Ashby                                                  │
│  │  └─ Workable                                               │
│  ├─ Product Hunt Hiring                                       │
│  ├─ YC Jobs                                                   │
│  └─ Authentic Jobs                                            │
│                                                                 │
│  MEDIUM-PRIORITY SOURCES (High-Quality RSS)                   │
│  ├─ We Work Remotely (API + RSS)                              │
│  ├─ Remotive (API)                                            │
│  ├─ Hashnode (GraphQL)                                        │
│  └─ Dribbble Jobs                                             │
│                                                                 │
│  VOLUME SOURCES (RSS + Fallback)                              │
│  ├─ Remote OK (RSS)                                           │
│  ├─ Working Nomads (RSS)                                      │
│  ├─ Himalayas (RSS)                                           │
│  └─ Others (fallback)                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
PHASE 2: NORMALIZATION & ENRICHMENT
┌─────────────────────────────────────────────────────────────────┐
│ Data Normalization & Enrichment Layer                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Job Normalization:                                            │
│  ├─ Title standardization (Sr Dev → Senior Developer)         │
│  ├─ Company name normalization                                │
│  ├─ Location parsing & standardization                        │
│  ├─ Salary standardization (currency, range)                  │
│  ├─ Remote type detection (true-remote, hybrid, etc.)         │
│  └─ Employment type standardization                           │
│                                                                 │
│  Data Enrichment:                                              │
│  ├─ Extract: tech stack, skills, seniority, domain           │
│  ├─ Detect: visa sponsorship, timezone, benefits             │
│  ├─ Validate: company legitimacy                             │
│  ├─ Score: remote authenticity                               │
│  └─ Generate: embeddings for semantic search                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
PHASE 3: INTELLIGENT FILTERING & DEDUPLICATION
┌─────────────────────────────────────────────────────────────────┐
│ Smart Deduplication & Quality Filtering                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Deduplication Engine:                                         │
│  ├─ Exact match: normalized title + company + location       │
│  ├─ Fuzzy match: title similarity (rapidfuzz)                │
│  ├─ Semantic match: embedding similarity (>0.95)             │
│  ├─ URL normalization & canonical detection                  │
│  ├─ ATS identifier matching                                  │
│  └─ Merge duplicate metadata                                 │
│                                                                 │
│  Quality Filtering:                                            │
│  ├─ Spam detection (excessive emojis, unrealistic pay)       │
│  ├─ Broken link detection                                    │
│  ├─ Low-information filtering                                │
│  ├─ Reposted job detection                                   │
│  ├─ Suspicious domain detection                              │
│  └─ Domain authority scoring                                 │
│                                                                 │
│  Output: Deduplicated, high-quality job candidates           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
PHASE 4: SCORING & RANKING
┌─────────────────────────────────────────────────────────────────┐
│ Multi-Dimensional Scoring & Ranking Engine                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Scoring Dimensions:                                           │
│  ├─ Source Trust Score (0-10)                                │
│  │  ├─ Direct ATS = 10 (Greenhouse, Lever)                   │
│  │  ├─ Wellfound = 9                                         │
│  │  ├─ Dev.to = 8                                            │
│  │  ├─ We Work Remotely = 7                                  │
│  │  ├─ Remotive = 5                                          │
│  │  ├─ RSS feeds = 3-4                                       │
│  │  └─ Unknown = 1                                           │
│  │                                                            │
│  ├─ Freshness Score (0-10)                                   │
│  │  ├─ <24h = 10                                             │
│  │  ├─ <3 days = 8                                           │
│  │  ├─ <7 days = 6                                           │
│  │  ├─ <14 days = 4                                          │
│  │  ├─ >30 days = 0 (hidden)                                 │
│  │  └─ Time-decay function: exp(-days/7)                     │
│  │                                                            │
│  ├─ Quality Score (0-10)                                     │
│  │  ├─ Description length & quality                          │
│  │  ├─ Salary transparency                                   │
│  │  ├─ Company info completeness                             │
│  │  ├─ Remote authenticity                                   │
│  │  └─ Apply link validity                                   │
│  │                                                            │
│  ├─ Company Score (0-10)                                     │
│  │  ├─ Domain authority (Ahrefs/Majestic)                   │
│  │  ├─ Company age                                           │
│  │  ├─ LinkedIn presence                                     │
│  │  ├─ Hiring consistency                                    │
│  │  └─ Startup ecosystem affiliation                         │
│  │                                                            │
│  ├─ Remote Authenticity (0-10)                               │
│  │  ├─ No timezone restrictions = 10                         │
│  │  ├─ Timezone-restricted = 5                               │
│  │  ├─ Hybrid disguised as remote = 2                        │
│  │  └─ Location-restricted = 0                               │
│  │                                                            │
│  └─ Salary Quality (0-10)                                    │
│     ├─ Salary range provided = 10                            │
│     ├─ Salary realistic for role = 10                        │
│     ├─ Currency included = 8                                 │
│     └─ No salary info = 4                                    │
│                                                                 │
│  FINAL RANKING SCORE:                                          │
│  ═══════════════════════════════════════════════════════════ │
│                                                               │
│  SCORE = (                                                    │
│    SOURCE_TRUST * 0.20 +                                     │
│    FRESHNESS * 0.25 +                                        │
│    QUALITY * 0.20 +                                          │
│    COMPANY_SCORE * 0.15 +                                    │
│    REMOTE_AUTH * 0.10 +                                      │
│    SALARY_QUALITY * 0.10                                     │
│  )                                                            │
│                                                               │
│  Result: 0-10 score, stored in database                      │
│  Configurable weights via environment                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
PHASE 5: PERSISTENCE & INDEXING
┌─────────────────────────────────────────────────────────────────┐
│ PostgreSQL + Vector Index Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Tables:                                                       │
│  ├─ jobs (main job listings)                                 │
│  ├─ jobs_normalized (normalized versions)                    │
│  ├─ duplicate_clusters (groups of duplicates)                │
│  ├─ job_embeddings (semantic vectors)                        │
│  ├─ source_metadata (source scores & config)                 │
│  ├─ company_scores (company legitimacy)                      │
│  ├─ job_scoring (all ranking dimensions)                     │
│  └─ scrape_runs (audit trail)                               │
│                                                                 │
│  Indexes:                                                      │
│  ├─ Full-text search on normalized fields                    │
│  ├─ pgvector indexes on embeddings                           │
│  ├─ Composite index: (company, normalized_title)             │
│  ├─ Index: created_at for time-based queries                 │
│  ├─ Index: final_score DESC for ranking                      │
│  └─ Index: external_id for uniqueness                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
PHASE 6: SEARCH & RANKING ENGINE
┌─────────────────────────────────────────────────────────────────┐
│ Hybrid Search & Re-ranking                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Search Methods:                                               │
│  ├─ Keyword search: BM25 on normalized fields                │
│  ├─ Semantic search: Vector similarity on embeddings         │
│  ├─ Hybrid search: Combine both with weights                 │
│  └─ Filter search: By location, salary, source, etc.         │
│                                                                 │
│  Ranking:                                                      │
│  ├─ Text relevance (BM25) = 0.30                             │
│  ├─ Semantic similarity = 0.20                               │
│  ├─ Final score (computed) = 0.50                            │
│  └─ Apply filters: remote, startup, verified, etc.           │
│                                                                 │
│  Output: Ranked results with trust badges & freshness        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
PHASE 7: API & FRONTEND
┌─────────────────────────────────────────────────────────────────┐
│ Enhanced API & User Interface                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  API Endpoints:                                                │
│  ├─ GET /jobs/search - hybrid search                         │
│  ├─ GET /jobs/semantic - semantic search                     │
│  ├─ GET /jobs/{id} - job details + trust info                │
│  ├─ GET /stats - quality metrics & health                    │
│  ├─ GET /trending - trending jobs                            │
│  └─ GET /health - system health                              │
│                                                                 │
│  Frontend Displays:                                            │
│  ├─ Trust badges (verified, direct ATS, startup)             │
│  ├─ Freshness indicators (posted <24h, 3d, etc.)             │
│  ├─ Quality scores (overall, salary, company)                │
│  ├─ Remote authenticity label                                │
│  ├─ Duplicate suppression (show best version)                │
│  └─ Apply success estimate                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

```

---

## IMPLEMENTATION PHASES

### PHASE 1: CORE INFRASTRUCTURE (Weeks 1-2)

**Goals**: Foundation for quality improvements

1. **Database Schema Enhancements**
   - Add normalized fields to jobs table
   - Create new tables: duplicate_clusters, job_scores, source_metadata
   - Add pgvector extension for embeddings
   - Create composite indexes

2. **Source Metadata System**
   - Define source trust scores
   - Configure source parameters (API keys, rate limits)
   - Build source adapter base class

3. **Data Quality Baseline**
   - Run baseline analysis of existing jobs
   - Measure current duplicate rate
   - Identify spam patterns

**Deliverables**:
- Database migrations
- Source configuration system
- Data quality baseline report

---

### PHASE 2: DEDUPLICATION ENGINE (Weeks 2-3)

**Goals**: Eliminate 40-50% duplicate jobs

1. **Build Deduplication System**
   - Title/company normalization
   - Fuzzy matching with rapidfuzz
   - Embedding-based similarity
   - Duplicate clustering

2. **Implement Duplicate Merging**
   - Preserve best-source version
   - Merge metadata from duplicates
   - Track duplicate sources
   - Create duplicate clusters

3. **Run Deduplication Pass**
   - Process all existing jobs
   - Create clusters
   - Measure improvement
   - Generate reports

**Deliverables**:
- Deduplication service
- Duplicate cluster management
- Quality reports

---

### PHASE 3: QUALITY SCORING (Weeks 3-4)

**Goals**: Implement multi-dimensional ranking

1. **Build Scoring Components**
   - Source trust scoring
   - Freshness decay function
   - Quality metrics
   - Company legitimacy analysis
   - Remote authenticity detection

2. **Implement Final Ranking Score**
   - Composite scoring formula
   - Configurable weights
   - Batch calculation for all jobs
   - Update database

3. **Validation & Tuning**
   - Manual validation of results
   - Adjust weights based on feedback
   - A/B test different configurations

**Deliverables**:
- Scoring service
- Ranking engine
- Configuration system
- Quality reports

---

### PHASE 4: SOURCE UPGRADES (Weeks 4-6)

**Goals**: Migrate to high-quality sources, reduce RSS dependency

1. **High-Priority APIs**
   - GitHub Jobs (simple, no auth)
   - Dev.to Jobs (simple, no auth)
   - Wellfound GraphQL (improve from AngelList)
   - Indie Hackers (web scraping + RSS)

2. **ATS Integration Framework**
   - Greenhouse jobs extraction
   - Lever jobs extraction
   - Ashby jobs extraction
   - Workable jobs extraction

3. **Additional Quality Sources**
   - Product Hunt Hiring
   - YC Jobs
   - Authentic Jobs
   - Dribbble Jobs

**Deliverables**:
- Source adapter framework
- 6-8 new/improved sources
- ATS integration architecture
- Source health monitoring

---

### PHASE 5: VECTOR SEARCH (Weeks 5-6)

**Goals**: Enable semantic search and similarity matching

1. **Embedding Generation**
   - Generate embeddings for all jobs (sentence-transformers)
   - Store in pgvector
   - Create vector indexes

2. **Semantic Search**
   - Implement similarity search
   - Build hybrid search (keyword + semantic)
   - Create recommendation system

3. **Duplicate Detection v2**
   - Use embeddings for better duplicate detection
   - Find similar jobs for recommendations
   - Identify related roles

**Deliverables**:
- Embedding generation pipeline
- Vector search implementation
- Similarity recommendation system

---

### PHASE 6: OBSERVABILITY & MONITORING (Weeks 6-7)

**Goals**: Production readiness, quality monitoring

1. **Monitoring Dashboards**
   - Source health metrics
   - Freshness tracking
   - Duplicate rates
   - Spam rates
   - Ingestion delays

2. **Alerting System**
   - Source failures
   - Quality degradation
   - Spike in duplicates
   - High spam scores

3. **Logging & Audit Trail**
   - Structured logging
   - Ingestion audit trail
   - Scoring debug logs
   - Source response logging

**Deliverables**:
- Monitoring dashboards
- Alerting rules
- Logging infrastructure
- Quality metrics API

---

### PHASE 7: DEPLOYMENT & MIGRATION (Weeks 7-8)

**Goals**: Production deployment, RSS deprecation

1. **Testing & Validation**
   - End-to-end testing
   - Load testing
   - Quality validation
   - Performance benchmarks

2. **Gradual Rollout**
   - A/B test new ranking
   - Gradual source migration
   - User feedback collection
   - Iterate on configuration

3. **Deprecation Plan**
   - Reduce RSS feed priority
   - Monitor quality during transition
   - Keep RSS as fallback
   - Complete RSS deprecation

**Deliverables**:
- Test suite
- Deployment documentation
- Migration runbook
- Rollback procedures

---

## DATABASE SCHEMA UPDATES

### New Tables

```sql
-- Duplicate cluster tracking
CREATE TABLE duplicate_clusters (
    id SERIAL PRIMARY KEY,
    primary_job_id INT REFERENCES jobs(id),
    cluster_hash VARCHAR(64) UNIQUE,
    duplicate_count INT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE duplicate_members (
    id SERIAL PRIMARY KEY,
    cluster_id INT REFERENCES duplicate_clusters(id),
    job_id INT REFERENCES jobs(id),
    similarity_score FLOAT,
    match_type VARCHAR(20), -- 'exact', 'fuzzy', 'semantic'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Job scoring components
CREATE TABLE job_scoring (
    id SERIAL PRIMARY KEY,
    job_id INT UNIQUE REFERENCES jobs(id),
    source_trust_score FLOAT,
    freshness_score FLOAT,
    quality_score FLOAT,
    company_score FLOAT,
    remote_authenticity_score FLOAT,
    salary_quality_score FLOAT,
    final_score FLOAT,
    ranking_position INT,
    calculated_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Source configuration & metrics
CREATE TABLE source_metadata (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) UNIQUE,
    trust_score FLOAT DEFAULT 5.0,
    spam_score FLOAT DEFAULT 0.0,
    freshness_score FLOAT DEFAULT 5.0,
    is_active BOOLEAN DEFAULT TRUE,
    last_successful_run TIMESTAMP,
    last_failed_run TIMESTAMP,
    failure_count INT DEFAULT 0,
    total_jobs_ingested INT DEFAULT 0,
    duplicate_ratio FLOAT DEFAULT 0.0,
    config JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Company legitimacy tracking
CREATE TABLE company_scores (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) UNIQUE,
    domain VARCHAR(255),
    trust_score FLOAT,
    domain_authority INT, -- Ahrefs score 0-100
    company_age_days INT,
    linkedin_presence BOOLEAN,
    hiring_consistency FLOAT,
    is_verified BOOLEAN,
    is_startup BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Job embeddings for semantic search
CREATE TABLE job_embeddings (
    id SERIAL PRIMARY KEY,
    job_id INT UNIQUE REFERENCES jobs(id),
    embedding vector(384), -- all-MiniLM-L6-v2 dimension
    created_at TIMESTAMP DEFAULT NOW()
);

-- Normalized job data
CREATE TABLE jobs_normalized (
    id SERIAL PRIMARY KEY,
    job_id INT UNIQUE REFERENCES jobs(id),
    normalized_title VARCHAR(255),
    normalized_company VARCHAR(255),
    normalized_location VARCHAR(255),
    title_tokens TEXT[],
    company_tokens TEXT[],
    tech_stack TEXT[],
    seniority VARCHAR(50),
    remote_type VARCHAR(50), -- 'true-remote', 'hybrid', 'restricted'
    timezone_required VARCHAR(100),
    visa_sponsored BOOLEAN,
    employment_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Ingestion audit trail
CREATE TABLE ingestion_audit (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100),
    run_id UUID,
    jobs_fetched INT,
    jobs_new INT,
    jobs_duplicated INT,
    jobs_spam INT,
    jobs_stored INT,
    duration_seconds INT,
    error_message TEXT,
    status VARCHAR(20), -- 'success', 'partial', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### Modified Jobs Table

```sql
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_jobs_final_score ON jobs(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_duplicate_group ON jobs(duplicate_group_id);
CREATE INDEX IF NOT EXISTS idx_jobs_normalized_title ON jobs(normalized_title);

-- Full-text search
CREATE INDEX IF NOT EXISTS idx_jobs_title_fts ON jobs USING GIN(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_jobs_desc_fts ON jobs USING GIN(to_tsvector('english', COALESCE(description, '')));

-- Vector index for semantic search
CREATE INDEX IF NOT EXISTS idx_job_embeddings_vector ON job_embeddings USING ivfflat (embedding vector_cosine_ops);
```

---

## KEY COMPONENTS ARCHITECTURE

### 1. Deduplication Engine

```
Raw Job Input
    ↓
Title Normalization
(Sr Dev → Senior Developer)
    ↓
Company Normalization
(Inc., LLC removal)
    ↓
Fuzzy String Matching
(rapidfuzz, ratio > 0.85)
    ↓
Embedding Similarity
(transformer model, > 0.95)
    ↓
URL Canonical Detection
    ↓
Duplicate Cluster Creation
    ↓
Best Source Selection
(preserve highest trust source)
    ↓
Metadata Merge
(combine duplicate info)
    ↓
Duplicate Marking
(is_duplicate = true)
    ↓
Store in Database
```

### 2. Scoring Engine

```
Job Input
    ↓
SOURCE TRUST COMPONENT
├─ Direct ATS = 10
├─ Wellfound = 9
├─ Dev.to = 8
├─ Remotive = 5
└─ RSS = 3
    ↓
FRESHNESS COMPONENT
├─ Time since posted
├─ Decay function: exp(-days/7)
└─ Score 0-10
    ↓
QUALITY COMPONENT
├─ Description length & quality
├─ Salary transparency
├─ Company completeness
└─ Link validity
    ↓
COMPANY COMPONENT
├─ Domain authority
├─ Company age
├─ LinkedIn presence
└─ Hiring consistency
    ↓
REMOTE AUTHENTICITY
├─ No timezone limits = 10
├─ Hybrid = 2
└─ Restricted = 0
    ↓
FINAL CALCULATION
SCORE = weighted sum of all components
    ↓
STORE & INDEX
```

### 3. Source Adapter Framework

```python
class SourceAdapter(ABC):
    """Base class for all job sources"""
    
    async def fetch_jobs(criteria) → List[RawJob]:
        """Fetch jobs from source"""
        pass
    
    def normalize_job(raw: RawJob) → Job:
        """Normalize to standard format"""
        pass
    
    def validate_job(job: Job) → bool:
        """Quality checks"""
        pass
    
    def detect_spam(job: Job) → SpamScore:
        """Spam detection"""
        pass
    
    def extract_enrichment(job: Job) → Enrichment:
        """Extract tech stack, seniority, etc."""
        pass
```

---

## CRITICAL SUCCESS FACTORS

1. **Preserve Backward Compatibility**
   - Keep existing API endpoints working
   - Don't break current workflows
   - Gradual migration from RSS

2. **Measurable Quality Improvements**
   - Track duplicate rate (target: 30-50% reduction)
   - Monitor freshness (target: 70%+ <7 days old)
   - Measure spam reduction
   - User satisfaction tracking

3. **Reliability & Monitoring**
   - Every source needs health checks
   - Automated alerts for failures
   - Graceful degradation
   - Rollback procedures

4. **Performance & Scale**
   - Async ingestion for all sources
   - Non-blocking deduplication
   - Efficient vector search
   - Redis caching layer

5. **User Trust & Transparency**
   - Visible trust badges
   - Freshness indicators
   - Source attribution
   - Quality scores displayed

---

## SUCCESS METRICS

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Duplicate Rate | ~40% | <15% | Week 2 |
| Freshness (<7d) | ~60% | 75%+ | Week 4 |
| Spam Rate | ~20% | <5% | Week 4 |
| Search Relevance | Baseline | +40% | Week 6 |
| Average Job Age | 15 days | <7 days | Week 5 |
| API Response Time | 200ms | <100ms | Week 6 |
| User Satisfaction | Unknown | 4.5/5.0 | Week 8 |

---

## NEXT STEPS

1. Review and approve architecture
2. Begin Phase 1: Database schema updates
3. Implement source trust scoring system
4. Build deduplication engine
5. Execute quality improvements
6. Integrate high-priority sources
7. Deploy to production

---
