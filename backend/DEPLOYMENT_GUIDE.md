# Remote Hunter Production Deployment Guide

## Overview

This guide covers deploying the Remote Hunter backend with all the new features from the upgrade (deduplication, ranking, monitoring, etc.).

## Prerequisites

- Python 3.9+ (currently using 3.14)
- SQLite (for local development) or PostgreSQL 13+ (for production with vector search)
- Virtual environment
- Git

## Quick Start

### 1. Install Dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Database Setup

**For SQLite (Current Setup):**
```bash
# Database will be created automatically
# Run migrations
sqlite3 data/jobs.db < migrations/003_quality_improvements_sqlite.sql
```

**For PostgreSQL (Recommended for Production):**
```bash
# Set DATABASE_URL in .env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname

# Run PostgreSQL migration
psql -h host -U user -d dbname < migrations/002_quality_improvements.sql
```

### 3. Initialize Source Metadata

```bash
python scripts/init_source_metadata.py
```

### 4. Run Batch Processing (Optional)

```bash
# Deduplicate existing jobs
python scripts/batch_deduplicate_jobs.py --limit 1000

# Score existing jobs
python scripts/batch_score_jobs.py --limit 1000
```

### 5. Start the Server

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Automated Deployment

Run the deployment script:

```bash
chmod +x scripts/deploy_production.sh
./scripts/deploy_production.sh
```

## Environment Variables

Create a `.env` file in the backend directory:

```bash
# App Configuration
APP_NAME="Remote Job Hunter"
DEBUG=false
API_PREFIX=/api/v1

# Database
DATABASE_URL=sqlite:///./data/jobs.db

# Scraping
SCRAPE_ENABLED=true
SCRAPE_INTERVAL_HOURS=5
REQUEST_DELAY_SECONDS=1.5
REQUEST_TIMEOUT_SECONDS=30

# CORS
CORS_ORIGINS=http://localhost:3000,https://remote-hunter.onrender.com

# JWT Secret
JWT_SECRET_KEY=your-secure-random-secret-key

# OAuth (Optional)
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GITHUB_OAUTH_CLIENT_ID=
GITHUB_OAUTH_CLIENT_SECRET=

# Monitoring
ENABLE_MONITORING=true
METRICS_PORT=9090
```

## Testing

### Unit Tests

```bash
pytest tests/ -v
```

### Integration Tests

```bash
# Test scraping
python -c "from scrapers.registry import run_all_scrapers; jobs = run_all_scrapers(); print(f'Found {len(jobs)} jobs')"

# Test deduplication
python scripts/batch_deduplicate_jobs.py --dry-run --limit 10

# Test scoring
python scripts/batch_score_jobs.py --dry-run --limit 10
```

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# Source health
curl http://localhost:8000/api/v1/health/sources

# Monitoring metrics
curl http://localhost:8000/api/v1/monitoring/metrics

# System status
curl http://localhost:8000/api/v1/monitoring/status
```

## Monitoring

### Prometheus Metrics

Metrics are available on port 9090:

```bash
curl http://localhost:9090/metrics
```

### Key Metrics

- `scrape_requests_total` - Total scrape requests by status
- `jobs_ingested_total` - Total jobs ingested by source
- `duplicates_detected_total` - Total duplicates detected
- `spam_jobs_total` - Total spam jobs detected
- `scrape_duration_seconds` - Scrape duration histogram
- `total_jobs_count` - Total jobs in database
- `duplicate_ratio` - Ratio of duplicate jobs
- `avg_job_score` - Average job score

### Alerts

Alerts are available via API:

```bash
# Get all alerts
curl http://localhost:8000/api/v1/monitoring/alerts

# Run health check
curl -X POST http://localhost:8000/api/v1/monitoring/health-check

# Get system status
curl http://localhost:8000/api/v1/monitoring/status
```

## Docker Deployment

### Build Docker Image

```bash
docker build -t remote-hunter-backend .
```

### Run with Docker Compose

```bash
docker-compose up -d
```

### Docker Environment

Update `docker-compose.yml` with your environment variables.

## Troubleshooting

### Import Errors

If you get import errors for new packages:

```bash
pip install rapidfuzz sentence-transformers torch pgvector aiohttp prometheus-client
```

### Database Migration Errors

If migration fails:

```bash
# For SQLite, delete and recreate database
rm data/jobs.db
sqlite3 data/jobs.db < migrations/003_quality_improvements_sqlite.sql

# For PostgreSQL, check pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
```

### Memory Issues

If you encounter memory issues during batch processing:

```bash
# Process in smaller batches
python scripts/batch_deduplicate_jobs.py --limit 100
python scripts/batch_score_jobs.py --limit 100
```

### Port Conflicts

If port 8000 is in use:

```bash
# Use a different port
uvicorn app.main:app --port 8001
```

## Production Checklist

- [ ] Set `DEBUG=false` in environment
- [ ] Use PostgreSQL instead of SQLite for production
- [ ] Set secure `JWT_SECRET_KEY`
- [ ] Configure OAuth credentials if using OAuth
- [ ] Set up monitoring and alerting
- [ ] Configure CORS origins properly
- [ ] Run database migrations
- [ ] Initialize source metadata
- [ ] Run batch deduplication on existing jobs
- [ ] Run batch scoring on existing jobs
- [ ] Test all API endpoints
- [ ] Set up log aggregation
- [ ] Configure backup strategy
- [ ] Set up SSL/TLS for HTTPS
- [ ] Configure rate limiting
- [ ] Set up health checks

## Rollback Plan

If deployment fails:

1. Stop the new deployment
2. Restore previous database backup
3. Revert to previous code version
4. Restart services

```bash
# Stop services
pkill -f uvicorn

# Restore database (PostgreSQL)
pg_restore -d dbname backup.dump

# Revert code
git checkout previous-version

# Restart
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Performance Tuning

### Database Optimization

```sql
-- For PostgreSQL
VACUUM ANALYZE jobs;
REINDEX TABLE jobs;
```

### Application Tuning

- Increase workers: `--workers 8`
- Adjust timeout: `--timeout 120`
- Enable GZIP compression
- Use connection pooling

### Caching

Consider adding Redis for:
- Session storage
- API response caching
- Rate limiting

## Security Considerations

1. Never commit `.env` files
2. Use strong JWT secrets
3. Enable HTTPS in production
4. Implement rate limiting
5. Validate all user inputs
6. Keep dependencies updated
7. Use environment-specific configurations
8. Enable audit logging

## Support

For issues or questions:
- Check logs: `tail -f logs/app.log`
- Review monitoring dashboard
- Check alert history via API
- Review database logs
