# Remote Hunter: Phase-by-Phase Implementation Roadmap

## Overview

This document provides a detailed, week-by-week implementation roadmap for upgrading Remote Hunter into a production-grade intelligent job discovery system.

---

## PHASE 1: Foundation (Weeks 1-2)

### Week 1: Database & Infrastructure Setup

**Deliverables:**
1. Run database migrations
2. Add pgvector support
3. Create monitoring tables
4. Initialize source metadata

**Tasks:**

1. **Database Migration** (1-2 hours)
   ```bash
   cd backend
   psql -h your_db_host -U your_user -d your_db < migrations/002_quality_improvements.sql
   ```
   - Validates: All new tables created
   - Verifies: Indexes created successfully
   - Checks: Views and functions operational

2. **Environment Configuration** (30 min)
   ```bash
   # Add to .env
   ENABLE_VECTOR_SEARCH=true
   EMBEDDING_MODEL=all-MiniLM-L6-v2
   DEDUP_FUZZY_THRESHOLD=0.85
   DEDUP_SEMANTIC_THRESHOLD=0.92
   ```

3. **Update Requirements** (30 min)
   ```bash
   pip install rapidfuzz sentence-transformers pgvector
   ```

4. **Verify Database Setup** (30 min)
   ```python
   # Quick validation script
   from app.database import engine
   from sqlalchemy import inspect
   
   inspector = inspect(engine)
   tables = inspector.get_table_names()
   
   required = ['duplicate_clusters', 'job_scoring', 'source_metadata', 'company_scores']
   for table in required:
       assert table in tables, f"Missing table: {table}"
   
   print("✅ All database tables created successfully")
   ```

**Success Criteria:**
- [ ] All new tables exist in database
- [ ] pgvector extension enabled
- [ ] Indexes created
- [ ] Views working
- [ ] Functions operational

---

### Week 2: Source Trust Scoring System

**Deliverables:**
1. Implement source metadata system
2. Initialize source trust scores
3. Create source health monitoring
4. Build source performance dashboard

**Tasks:**

1. **Initialize Source Trust Scores** (1-2 hours)
   ```python
   # File: backend/app/services/source_trust.py
   
   from app.database import SessionLocal
   from sqlalchemy import insert
   from app.models import SourceMetadata
   
   DEFAULT_SOURCES = {
       'greenhouse': {'trust': 10.0, 'type': 'api', 'priority': 10},
       'github_jobs': {'trust': 9.0, 'type': 'api', 'priority': 10},
       # ... etc
   }
   
   db = SessionLocal()
   for source_name, config in DEFAULT_SOURCES.items():
       db.execute(insert(SourceMetadata).values(
           source_name=source_name,
           trust_score=config['trust'],
           source_type=config['type'],
           priority=config['priority'],
           is_active=True
       ))
   db.commit()
   ```

2. **Create Source Health Service** (2-3 hours)
   ```python
   # File: backend/app/services/source_health.py
   
   class SourceHealthMonitor:
       def __init__(self, db):
           self.db = db
       
       async def update_source_health(self, source_name: str, result: IngestionResult):
           """Update source metrics after ingestion"""
           metadata = self.db.query(SourceMetadata).filter_by(
               source_name=source_name
           ).first()
           
           if result.status == 'success':
               metadata.last_successful_run = datetime.utcnow()
               metadata.failure_count = 0
               metadata.consecutive_failures = 0
           else:
               metadata.last_failed_run = datetime.utcnow()
               metadata.failure_count += 1
               metadata.consecutive_failures += 1
           
           # Auto-disable if too many failures
           if metadata.consecutive_failures >= 5:
               metadata.is_active = False
               logger.warning(f"Disabled source: {source_name} (too many failures)")
           
           self.db.commit()
   ```

3. **Build Source Dashboard** (2-3 hours)
   - Add API endpoint: `GET /api/v1/sources/health`
   - Returns: JSON with all source metrics
   - Includes: trust scores, last run, failure rates, job counts

4. **Unit Tests** (1-2 hours)
   ```python
   # tests/test_source_health.py
   
   async def test_source_health_update():
       monitor = SourceHealthMonitor(db)
       result = IngestionResult(
           source_name='github_jobs',
           status='success',
           jobs_fetched=100,
           # ...
       )
       await monitor.update_source_health('github_jobs', result)
       
       metadata = db.query(SourceMetadata).filter_by(
           source_name='github_jobs'
       ).first()
       
       assert metadata.failure_count == 0
       assert metadata.last_successful_run is not None
   ```

**Success Criteria:**
- [ ] Source trust scores in database
- [ ] Health monitoring service working
- [ ] Dashboard API endpoint functional
- [ ] Auto-disable on failures working
- [ ] Tests passing

---

## PHASE 2: Deduplication Engine (Weeks 2-3)

**Deliverables:**
1. Deduplication service implementation
2. Batch deduplication for existing jobs
3. Real-time deduplication on ingestion
4. Duplicate cluster reports

**Tasks:**

1. **Implement Deduplication Service** (Already provided in deduplication.py)
   - Verify all classes implemented
   - Ensure rapidfuzz installed
   - Test on sample data

2. **Batch Process Existing Jobs** (2-3 hours)
   ```python
   # File: backend/scripts/deduplicate_existing.py
   
   from services.deduplication import DeduplicationEngine
   from app.database import SessionLocal
   
   async def deduplicate_all_jobs():
       db = SessionLocal()
       engine = DeduplicationEngine(db)
       
       # Process in batches
       batch_size = 100
       total = db.query(Job).count()
       
       for offset in range(0, total, batch_size):
           jobs = db.query(Job).offset(offset).limit(batch_size).all()
           results = engine.deduplicate_batch(jobs)
           
           print(f"Processed {offset + batch_size}/{total}")
           print(f"  Duplicates: {results['duplicates_found']}")
           print(f"  Clusters: {len(results['duplicate_clusters'])}")
       
       print("Deduplication complete!")
   
   # Run with: python scripts/deduplicate_existing.py
   ```

3. **Integrate with Ingestion Pipeline** (2-3 hours)
   ```python
   # File: backend/app/services/jobs.py - update run_scrape()
   
   async def run_scrape(db, request):
       # ... existing code ...
       
       # Add deduplication step
       from services.deduplication import DeduplicationEngine
       dedup_engine = DeduplicationEngine(db)
       
       dedup_results = dedup_engine.deduplicate_batch(raw_jobs)
       
       # Update database with duplicate markers
       for job_id in dedup_results['primary_jobs']:
           job = db.query(Job).get(job_id)
           job.is_duplicate = False
       
       for cluster_id, cluster_data in dedup_results['duplicate_clusters'].items():
           for dup_job_id in cluster_data['duplicate_jobs']:
               job = db.query(Job).get(dup_job_id)
               job.is_duplicate = True
               job.duplicate_group_id = cluster_id
       
       db.commit()
   ```

4. **Create Reports** (1-2 hours)
   ```python
   # File: backend/app/api/deduplication.py
   
   @router.get("/dedup/report")
   async def get_dedup_report(db: Session = Depends(get_db)):
       total_jobs = db.query(Job).count()
       duplicate_jobs = db.query(Job).filter(Job.is_duplicate == True).count()
       unique_jobs = total_jobs - duplicate_jobs
       
       dup_ratio = (duplicate_jobs / total_jobs * 100) if total_jobs > 0 else 0
       
       return {
           'total_jobs': total_jobs,
           'unique_jobs': unique_jobs,
           'duplicate_jobs': duplicate_jobs,
           'duplicate_ratio': dup_ratio,
           'improvement_potential': f"{dup_ratio:.1f}%"
       }
   ```

**Success Criteria:**
- [ ] Deduplication engine working on sample data
- [ ] Batch script completes successfully
- [ ] Existing jobs processed (check is_duplicate field)
- [ ] Duplicate clusters created
- [ ] Report API returning correct data
- [ ] 30-50% duplicate reduction achieved

---

## PHASE 3: Quality Scoring System (Weeks 3-4)

**Deliverables:**
1. Scoring engine implementation (Already provided in ranking.py)
2. Batch scoring for all jobs
3. Ranking API endpoint
4. Quality improvement metrics

**Tasks:**

1. **Implement Ranking Engine** (Already provided)
   - Verify all scorer classes
   - Test on sample data
   - Validate weights sum to 1.0

2. **Batch Score All Jobs** (1-2 hours)
   ```python
   # File: backend/scripts/score_all_jobs.py
   
   from services.ranking import create_ranking_engine
   
   def score_all_jobs():
       engine = create_ranking_engine()
       
       db = SessionLocal()
       total = db.query(Job).filter(Job.is_duplicate == False).count()
       batch_size = 500
       
       for offset in range(0, total, batch_size):
           job_ids = [j[0] for j in db.query(Job.id).filter(
               Job.is_duplicate == False
           ).offset(offset).limit(batch_size).all()]
           
           results = engine.batch_score_jobs(job_ids, save_to_db=True)
           
           print(f"Scored {offset + batch_size}/{total}")
           print(f"  Avg score: {results.get('avg_score', 0):.2f}")
       
       print("Scoring complete!")
   
   # Run with: python scripts/score_all_jobs.py
   ```

3. **Create Ranking API** (1-2 hours)
   ```python
   # File: backend/app/api/search.py
   
   @router.get("/jobs/ranked")
   async def get_ranked_jobs(
       skip: int = 0,
       limit: int = 20,
       min_score: float = 0.0,
       db: Session = Depends(get_db)
   ):
       jobs = db.query(Job).filter(
           and_(
               Job.is_duplicate == False,
               Job.final_score >= min_score
           )
       ).order_by(Job.final_score.desc()).offset(skip).limit(limit).all()
       
       return [JobResponse.from_orm(j) for j in jobs]
   ```

4. **Validation & Tuning** (2-3 hours)
   - Manual review of top-ranked jobs
   - Verify scoring makes sense
   - Adjust weights if needed
   - Test with different queries

**Success Criteria:**
- [ ] All jobs scored in database
- [ ] final_score field populated
- [ ] Ranking API working
- [ ] Top results are clearly higher quality
- [ ] Weights feel balanced
- [ ] Metrics reported correctly

---

## PHASE 4: High-Priority Source Integrations (Weeks 4-6)

**Deliverables:**
1. GitHub Jobs adapter
2. Dev.to Jobs adapter
3. Wellfound/AngelList GraphQL implementation
4. Indie Hackers web scraper
5. Source adapter framework (Already provided)

**Tasks:**

1. **GitHub Jobs Adapter** (1-2 hours)
   ```python
   # File: backend/scrapers/github_jobs.py
   
   class GitHubJobsAdapter(SourceAdapter):
       # Implementation from adapter_framework.py
       # Add to registry
   
   # Register
   registry = get_source_registry()
   registry.register(GitHubJobsAdapter())
   ```

2. **Dev.to Jobs Adapter** (1-2 hours)
   ```python
   # File: backend/scrapers/devto_jobs.py
   
   class DevToJobsAdapter(SourceAdapter):
       # Implementation from adapter_framework.py
       # Add to registry
   ```

3. **Wellfound GraphQL Implementation** (3-4 hours)
   ```python
   # File: backend/scrapers/wellfound.py
   
   class WellfoundAdapter(SourceAdapter):
       def __init__(self):
           super().__init__(SourceConfig(
               name='wellfound',
               source_type=SourceType.GRAPHQL,
               api_endpoint='https://api.wellfound.com/graphql',
               trust_score=9.0,
               priority=10
           ))
       
       async def fetch_jobs(self, criteria: Optional[SearchCriteria] = None) -> List[RawJob]:
           query = """
           query {
               jobListings(first: 100, remote: true) {
                   edges {
                       node {
                           title
                           company { name }
                           description
                           salary
                           location
                       }
                   }
               }
           }
           """
           
           # Implement GraphQL request
           # Parse response
           # Return RawJob list
   ```

4. **Indie Hackers Scraper** (2-3 hours)
   ```python
   # File: backend/scrapers/indie_hackers.py
   
   class IndieHackersAdapter(SourceAdapter):
       def __init__(self):
           super().__init__(SourceConfig(
               name='indie_hackers',
               source_type=SourceType.WEB_SCRAPE,
               trust_score=9.5,
               priority=10
           ))
       
       async def fetch_jobs(self, criteria: Optional[SearchCriteria] = None) -> List[RawJob]:
           # Scrape indie hackers jobs board
           # Parse HTML
           # Return RawJob list
   ```

5. **Update Ingestion Pipeline** (1-2 hours)
   ```python
   # File: backend/app/services/jobs.py
   
   async def run_scrape_v2(db, request):
       # Use new adapter framework
       registry = get_source_registry()
       
       # Filter by user-selected sources
       adapters = [
           registry.get(name)
           for name in request.sources
           if registry.get(name)
       ]
       
       results = await asyncio.gather(*[
           adapter.ingest(criteria)
           for adapter in adapters
       ])
       
       # Store jobs
       for adapter_result in results:
           # Process adapter_result.jobs
           pass
   ```

**Success Criteria:**
- [ ] GitHub Jobs adapter working
- [ ] Dev.to adapter working
- [ ] Wellfound GraphQL working
- [ ] Indie Hackers scraper working
- [ ] All sources showing in registry
- [ ] Jobs from all sources ingesting successfully
- [ ] ~50K+ new jobs from new sources

---

## PHASE 5: Vector Search & Embeddings (Weeks 5-6)

**Deliverables:**
1. Embedding generation pipeline
2. Vector index creation
3. Semantic search API
4. Similarity detection

**Tasks:**

1. **Generate Embeddings** (2-3 hours)
   ```python
   # File: backend/scripts/generate_embeddings.py
   
   from services.ranking import EmbeddingManager
   from app.models import JobEmbedding
   
   async def generate_all_embeddings():
       engine = EmbeddingManager()
       db = SessionLocal()
       
       jobs = db.query(Job).filter(Job.is_duplicate == False).all()
       
       for i, job in enumerate(jobs):
           text = f"{job.title} {job.company} {job.description or ''}"
           embedding = engine.generate_embedding(text)
           
           db.add(JobEmbedding(
               job_id=job.id,
               embedding=embedding
           ))
           
           if i % 100 == 0:
               db.commit()
               print(f"Generated {i} embeddings...")
       
       db.commit()
       print("Embedding generation complete!")
   
   # Run with: python scripts/generate_embeddings.py
   ```

2. **Create Vector Index** (30 min)
   ```sql
   -- Run after embeddings are generated
   CREATE INDEX idx_job_embeddings_vector ON job_embeddings 
   USING ivfflat (embedding vector_cosine_ops) 
   WITH (lists = 100);
   ```

3. **Implement Semantic Search** (2-3 hours)
   ```python
   # File: backend/app/services/semantic_search.py
   
   class SemanticSearchService:
       def __init__(self, db):
           self.db = db
           self.embedding_manager = EmbeddingManager()
       
       async def search(self, query: str, limit: int = 20) -> List[Job]:
           # Generate query embedding
           query_embedding = self.embedding_manager.generate_embedding(query)
           
           # Find similar jobs using pgvector
           jobs = self.db.query(Job).join(JobEmbedding).order_by(
               JobEmbedding.embedding.cosine_distance(query_embedding)
           ).limit(limit).all()
           
           return jobs
   ```

4. **Hybrid Search API** (1-2 hours)
   ```python
   # File: backend/app/api/search.py
   
   @router.get("/jobs/search/hybrid")
   async def hybrid_search(
       q: str,
       semantic_weight: float = 0.5,
       text_weight: float = 0.5,
       db: Session = Depends(get_db)
   ):
       # Keyword search results
       text_results = text_search(q, db)
       
       # Semantic search results
       semantic_results = await semantic_search(q, db)
       
       # Merge and rank
       # Return top results
   ```

**Success Criteria:**
- [ ] All unique jobs have embeddings
- [ ] Vector index created successfully
- [ ] Semantic search working
- [ ] Similarity detection accurate
- [ ] Performance acceptable (<500ms)

---

## PHASE 6: Observability & Monitoring (Weeks 6-7)

**Deliverables:**
1. Monitoring dashboard
2. Alerting system
3. Quality metrics tracking
4. Health checks

**Tasks:**

1. **Create Metrics Tracking** (2-3 hours)
   ```python
   # File: backend/app/services/metrics.py
   
   class MetricsService:
       def __init__(self, db):
           self.db = db
       
       def get_quality_metrics(self) -> Dict:
           total = self.db.query(Job).count()
           duplicates = self.db.query(Job).filter(Job.is_duplicate).count()
           spam = self.db.query(Job).filter(Job.spam_indicator > 0.5).count()
           fresh = self.db.query(Job).filter(
               Job.created_at > datetime.utcnow() - timedelta(days=7)
           ).count()
           
           return {
               'total_jobs': total,
               'duplicate_count': duplicates,
               'duplicate_ratio': duplicates / total if total > 0 else 0,
               'spam_count': spam,
               'spam_ratio': spam / total if total > 0 else 0,
               'fresh_jobs': fresh,
               'freshness_ratio': fresh / total if total > 0 else 0,
               'avg_score': self.db.query(func.avg(Job.final_score)).scalar() or 0,
           }
   ```

2. **Build Monitoring API** (1-2 hours)
   ```python
   # File: backend/app/api/monitoring.py
   
   @router.get("/health/metrics")
   async def get_metrics(db: Session = Depends(get_db)):
       service = MetricsService(db)
       return service.get_quality_metrics()
   
   @router.get("/health/sources")
   async def get_source_health(db: Session = Depends(get_db)):
       sources = db.query(SourceMetadata).all()
       return [{
           'name': s.source_name,
           'trust_score': s.trust_score,
           'is_active': s.is_active,
           'last_run': s.last_successful_run,
           'failure_count': s.failure_count,
       } for s in sources]
   ```

3. **Add Alerting** (2-3 hours)
   ```python
   # File: backend/services/alerting.py
   
   class AlertingService:
       def __init__(self, db):
           self.db = db
       
       async def check_alerts(self):
           metrics = MetricsService(self.db).get_quality_metrics()
           
           # Alert if duplicate ratio too high
           if metrics['duplicate_ratio'] > 0.4:
               await self.send_alert(f"High duplicate ratio: {metrics['duplicate_ratio']:.1%}")
           
           # Alert if spam ratio high
           if metrics['spam_ratio'] > 0.15:
               await self.send_alert(f"High spam ratio: {metrics['spam_ratio']:.1%}")
           
           # Alert if freshness low
           if metrics['freshness_ratio'] < 0.5:
               await self.send_alert(f"Low freshness: {metrics['freshness_ratio']:.1%}")
   ```

**Success Criteria:**
- [ ] Metrics API working
- [ ] Source health tracking accurate
- [ ] Alerts triggering correctly
- [ ] Dashboard displaying data
- [ ] Historical metrics stored

---

## PHASE 7: Production Deployment (Weeks 7-8)

**Deliverables:**
1. Production testing
2. Performance optimization
3. Deployment scripts
4. Monitoring live

**Tasks:**

1. **Load Testing** (1-2 hours)
   ```python
   # File: backend/tests/test_load.py
   
   async def test_search_performance():
       async with aiohttp.ClientSession() as session:
           tasks = []
           for i in range(100):
               tasks.append(session.get(
                   'http://localhost:8000/api/v1/jobs/search',
                   params={'q': f'Engineer {i % 5}'}
               ))
           
           results = await asyncio.gather(*tasks)
           
           # Verify all successful
           assert all(r.status == 200 for r in results)
           
           # Measure average response time
           # Should be <500ms
   ```

2. **Create Deployment Script** (1-2 hours)
   ```bash
   #!/bin/bash
   # File: scripts/deploy.sh
   
   set -e
   
   echo "Starting deployment..."
   
   # Run migrations
   psql -h $DB_HOST -U $DB_USER -d $DB_NAME < migrations/002_quality_improvements.sql
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Generate embeddings
   python scripts/generate_embeddings.py
   
   # Score all jobs
   python scripts/score_all_jobs.py
   
   # Run tests
   pytest tests/
   
   # Restart services
   systemctl restart uvicorn
   
   echo "Deployment complete!"
   ```

3. **Final Testing** (2-3 hours)
   - Search performance
   - Ranking accuracy
   - Deduplication effectiveness
   - Source health
   - Error handling

**Success Criteria:**
- [ ] All tests passing
- [ ] Load test successful (<500ms)
- [ ] Duplicate ratio <20%
- [ ] Spam ratio <5%
- [ ] Freshness >70%
- [ ] Average score >6.0
- [ ] System stable for 24+ hours

---

## SUCCESS METRICS

After implementation, you should see:

| Metric | Before | Target | Timeline |
|--------|--------|--------|----------|
| Duplicate Rate | 40% | <15% | Week 2 |
| Freshness (<7d) | 60% | 75%+ | Week 4 |
| Spam Rate | 20% | <5% | Week 4 |
| Search Relevance | Baseline | +40% | Week 6 |
| Average Score | N/A | 6.0+ | Week 4 |
| API Response Time | 200ms | <100ms | Week 6 |
| Data Coverage | 15 sources | 20+ sources | Week 6 |

---

## QUICK START

To get started immediately:

```bash
# Week 1: Setup
cd backend
psql < migrations/002_quality_improvements.sql
pip install rapidfuzz sentence-transformers pgvector

# Week 2: Deduplication
python scripts/deduplicate_existing.py

# Week 3: Scoring
python scripts/score_all_jobs.py

# Week 5: Embeddings
python scripts/generate_embeddings.py

# Deploy
scripts/deploy.sh
```

---

## SUPPORT & RESOURCES

- Database: PostgreSQL with pgvector
- ML: sentence-transformers (all-MiniLM-L6-v2)
- String matching: rapidfuzz
- Documentation: See ARCHITECTURE_V2.md
- Tests: tests/ directory

---
