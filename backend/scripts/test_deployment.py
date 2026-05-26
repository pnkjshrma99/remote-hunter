"""
Deployment Test Script

Tests the Remote Hunter backend deployment to ensure all components are working correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all required modules can be imported"""
    logger.info("Testing imports...")
    
    try:
        from app.main import app
        logger.info("✓ Main app imports successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import main app: {e}")
        return False
    
    try:
        from services.deduplication import DeduplicationEngine
        logger.info("✓ Deduplication engine imports successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import deduplication engine: {e}")
        return False
    
    try:
        from services.ranking import JobRankingEngine
        logger.info("✓ Ranking engine imports successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import ranking engine: {e}")
        return False
    
    try:
        from app.services.source_health import SourceHealthMonitor
        logger.info("✓ Source health monitor imports successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import source health monitor: {e}")
        return False
    
    try:
        from app.services.monitoring import get_monitoring_service
        logger.info("✓ Monitoring service imports successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import monitoring service: {e}")
        return False
    
    return True


def test_database():
    """Test database connectivity and schema"""
    logger.info("Testing database...")
    
    try:
        from app.database import SessionLocal, init_db
        init_db()
        
        db = SessionLocal()
        
        # Test basic query
        from sqlalchemy import text
        result = db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            logger.info("✓ Database connectivity OK")
        else:
            logger.error("✗ Database query failed")
            return False
        
        # Check for new tables
        tables_to_check = [
            'duplicate_clusters',
            'duplicate_members',
            'job_scoring',
            'source_metadata',
            'company_scores',
            'jobs_normalized',
            'ingestion_audit'
        ]
        
        for table in tables_to_check:
            result = db.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"))
            if result.fetchone():
                logger.info(f"✓ Table {table} exists")
            else:
                logger.warning(f"⚠ Table {table} not found (may be OK if using PostgreSQL)")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        return False


def test_source_metadata():
    """Test source metadata initialization"""
    logger.info("Testing source metadata...")
    
    try:
        from app.database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        result = db.execute(text("SELECT COUNT(*) FROM source_metadata"))
        count = result.scalar()
        
        if count > 0:
            logger.info(f"✓ Source metadata initialized with {count} sources")
        else:
            logger.warning("⚠ Source metadata not initialized. Run init_source_metadata.py")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ Source metadata test failed: {e}")
        return False


def test_scrapers():
    """Test scraper registry"""
    logger.info("Testing scraper registry...")
    
    try:
        from scrapers.registry import SCRAPER_REGISTRY
        
        if len(SCRAPER_REGISTRY) > 0:
            logger.info(f"✓ Scraper registry has {len(SCRAPER_REGISTRY)} scrapers")
            for name in SCRAPER_REGISTRY.keys():
                logger.info(f"  - {name}")
        else:
            logger.error("✗ No scrapers registered")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Scraper registry test failed: {e}")
        return False


def test_monitoring():
    """Test monitoring service"""
    logger.info("Testing monitoring service...")
    
    try:
        from app.services.monitoring import get_monitoring_service
        
        monitoring = get_monitoring_service()
        monitoring.update_job_metrics()
        
        metrics = monitoring.get_metrics_summary()
        logger.info(f"✓ Monitoring service working")
        logger.info(f"  Total jobs: {metrics.get('total_jobs', 0)}")
        logger.info(f"  Active sources: {metrics.get('active_sources', 0)}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Monitoring service test failed: {e}")
        return False


def run_all_tests():
    """Run all deployment tests"""
    logger.info("=" * 60)
    logger.info("Remote Hunter Deployment Test Suite")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.utcnow().isoformat()}")
    logger.info("")
    
    results = {
        'imports': test_imports(),
        'database': test_database(),
        'source_metadata': test_source_metadata(),
        'scrapers': test_scrapers(),
        'monitoring': test_monitoring(),
    }
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    logger.info("")
    if all_passed:
        logger.info("✓ All tests passed! Deployment is ready.")
        return 0
    else:
        logger.error("✗ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
