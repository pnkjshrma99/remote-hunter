#!/bin/bash
# Production Deployment Script for Remote Hunter Backend

set -e

echo "=========================================="
echo "Remote Hunter Backend Production Deployment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="/Users/apple/Documents/projects/remote-hunter/backend"
VENV_DIR="$BACKEND_DIR/.venv"
PYTHON_VERSION="python3.14"

echo -e "${GREEN}Step 1: Pre-flight checks${NC}"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Virtual environment not found. Creating...${NC}"
    cd "$BACKEND_DIR"
    $PYTHON_VERSION -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
else
    echo -e "${GREEN}Virtual environment found${NC}"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

echo -e "${GREEN}Step 2: Installing dependencies${NC}"
cd "$BACKEND_DIR"
pip install -r requirements.txt

echo -e "${GREEN}Step 3: Running database migrations${NC}"
# Check if database exists
if [ ! -f "$BACKEND_DIR/data/jobs.db" ]; then
    echo -e "${YELLOW}Database not found. Creating...${NC}"
    mkdir -p "$BACKEND_DIR/data"
fi

# Run SQLite migration
sqlite3 "$BACKEND_DIR/data/jobs.db" < "$BACKEND_DIR/migrations/003_quality_improvements_sqlite.sql"

echo -e "${GREEN}Step 4: Initializing source metadata${NC}"
python scripts/init_source_metadata.py

echo -e "${GREEN}Step 5: Running batch deduplication (optional)${NC}"
read -p "Run batch deduplication on existing jobs? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python scripts/batch_deduplicate_jobs.py --limit 1000
fi

echo -e "${GREEN}Step 6: Running batch scoring (optional)${NC}"
read -p "Run batch scoring on existing jobs? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python scripts/batch_score_jobs.py --limit 1000
fi

echo -e "${GREEN}Step 7: Testing application startup${NC}"
# Test if the app can start
timeout 10 python -c "from app.main import app; print('App imports successfully')" || {
    echo -e "${RED}Failed to import app${NC}"
    exit 1
}

echo -e "${GREEN}Step 8: Environment check${NC}"
if [ -f "$BACKEND_DIR/.env" ]; then
    echo -e "${GREEN}.env file found${NC}"
else
    echo -e "${YELLOW}.env file not found. Using defaults.${NC}"
fi

echo -e "${GREEN}Step 9: Starting production server${NC}"
# Use uvicorn with production settings
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --access-log \
    --reload

echo -e "${GREEN}Deployment complete!${NC}"
