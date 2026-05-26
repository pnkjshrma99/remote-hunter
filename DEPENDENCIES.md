# New Dependencies for Production-Grade Intelligent Job Discovery System

Add these to your `backend/requirements.txt`:

## Core Quality Improvements

# String similarity matching
rapidfuzz==3.0.0

# Embeddings & semantic search
sentence-transformers==2.3.0
torch>=2.0.0

# PostgreSQL vector support
pgvector==0.1.8

# Async HTTP client
aiohttp==3.9.0
tenacity==8.2.3

# NLP & text processing
nltk>=3.8
spacy>=3.6.0

# Optional: For Selenium-based scraping if needed
selenium>=4.0.0
webdriver-manager>=3.9.0

# Monitoring & observability
prometheus-client>=0.17.0

# Database tools
alembic>=1.13.0

# Data validation
pydantic>=2.0.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0

---

## Installation Steps

```bash
cd backend

# 1. Create/activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Upgrade pip
pip install --upgrade pip

# 3. Install existing requirements
pip install -r requirements.txt

# 4. Install new dependencies
pip install \
  rapidfuzz==3.0.0 \
  sentence-transformers==2.3.0 \
  torch \
  pgvector==0.1.8 \
  aiohttp==3.9.0 \
  tenacity==8.2.3 \
  nltk>=3.8 \
  spacy>=3.6.0 \
  prometheus-client>=0.17.0 \
  alembic>=1.13.0 \
  pytest>=7.4.0 \
  pytest-asyncio>=0.21.0

# 5. Download spacy model
python -m spacy download en_core_web_sm

# 6. Download NLTK data
python -m nltk.downloader punkt averaged_perceptron_tagger

# 7. Test import
python -c "from sentence_transformers import SentenceTransformer; print('✅ All imports successful')"
```

---

## Database Setup

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Run the migration file
psql -h your_host -U your_user -d your_db < migrations/002_quality_improvements.sql
```

---

## Environment Variables

Add to `.env`:

```bash
# Vector Search
ENABLE_VECTOR_SEARCH=true
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Deduplication
DEDUP_FUZZY_THRESHOLD=0.85
DEDUP_SEMANTIC_THRESHOLD=0.92
DEDUP_BATCH_SIZE=100

# Ranking
RANKING_WEIGHTS_SOURCE_TRUST=0.20
RANKING_WEIGHTS_FRESHNESS=0.25
RANKING_WEIGHTS_QUALITY=0.20
RANKING_WEIGHTS_COMPANY=0.15
RANKING_WEIGHTS_REMOTE_AUTH=0.10
RANKING_WEIGHTS_SALARY_QUALITY=0.10

# Monitoring
ENABLE_MONITORING=true
METRICS_PORT=9090

# Logging
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true
```

---

## Optional: GPU Acceleration (Recommended)

If you have CUDA-capable GPU:

```bash
# Install CUDA version of torch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify GPU
python -c "import torch; print(f'GPU available: {torch.cuda.is_available()}')"
```

---

## Disk Space Requirements

- Initial database: ~500MB
- After ingesting 100K jobs: ~1-2GB
- Embeddings (100K jobs × 384 dims): ~150-200MB
- Vector indexes: ~50-100MB

Recommend: **At least 10GB free space** for production

---

## Memory Requirements

- Minimum: 4GB RAM
- Recommended: 8GB+ RAM
- With GPU: 2GB VRAM minimum (6GB+ for faster inference)

---

## Testing Dependencies

If developing:

```bash
pip install \
  pytest==7.4.0 \
  pytest-asyncio==0.21.0 \
  pytest-cov==4.1.0 \
  black==23.7.0 \
  pylint==2.17.5 \
  mypy==1.5.0
```

---

## Performance Optimization Notes

1. **Embedding Generation**: First-time generation is slow (~100K jobs = 30-60 min)
   - Use GPU if available (3-5x faster)
   - Can be run in background
   - Cache embeddings in pgvector for reuse

2. **Deduplication**: Can be expensive on large datasets
   - Run in batches
   - Use semantic deduplication only after fuzzy fails
   - Consider running during off-peak hours

3. **Scoring**: Relatively fast (<100ms for 1K jobs)
   - Cache company scores
   - Pre-compute source trust scores
   - Use incremental updates for new jobs only

---

## Version Compatibility

- Python: 3.9+
- PostgreSQL: 13+ (with pgvector)
- FastAPI: 0.95+
- SQLAlchemy: 2.0+

---

## Troubleshooting

**Issue**: `ModuleNotFoundError: No module named 'sentence_transformers'`
```bash
pip install sentence-transformers
```

**Issue**: `pgvector` extension not found
```sql
CREATE EXTENSION vector;
-- If fails, install: https://github.com/pgvector/pgvector
```

**Issue**: Out of memory during embedding generation
```python
# Use batch_size parameter in embedding script
embedding_manager.generate_embedding(text, batch_size=32)
```

**Issue**: Slow embedding inference
- Install GPU version of torch
- Use smaller model: `all-MiniLM-L6-v2` (current, 22MB)
- Cache embeddings

---

## Next Steps

1. **Update requirements.txt**: Add new dependencies
2. **Run migrations**: `psql < migrations/002_quality_improvements.sql`
3. **Test imports**: Run the python import test
4. **Generate embeddings**: Use provided scripts
5. **Run tests**: `pytest tests/`
6. **Deploy**: Use deployment script

---
