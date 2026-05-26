"""
Initialize source metadata with trust scores and configuration.
This script populates the source_metadata table with default values for all job sources.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text
from datetime import datetime

# Default source configurations with trust scores
DEFAULT_SOURCES = {
    # High-priority API sources (Trust score: 8-10)
    'greenhouse': {
        'trust_score': 10.0,
        'source_type': 'api',
        'api_endpoint': 'https://boards.greenhouse.io',
        'description': 'Direct ATS integration - highest trust',
    },
    'lever': {
        'trust_score': 10.0,
        'source_type': 'api',
        'api_endpoint': 'https://jobs.lever.co',
        'description': 'Direct ATS integration - highest trust',
    },
    'ashby': {
        'trust_score': 10.0,
        'source_type': 'api',
        'api_endpoint': 'https://jobs.ashbyhq.com',
        'description': 'Direct ATS integration - highest trust',
    },
    'workable': {
        'trust_score': 10.0,
        'source_type': 'api',
        'api_endpoint': 'https://apply.workable.com',
        'description': 'Direct ATS integration - highest trust',
    },
    'github_jobs': {
        'trust_score': 9.0,
        'source_type': 'api',
        'api_endpoint': 'https://jobs.github.com',
        'description': 'GitHub official job board',
    },
    'wellfound': {
        'trust_score': 9.0,
        'source_type': 'graphql',
        'api_endpoint': 'https://api.wellfound.com/graphql',
        'description': 'AngelList successor - startup ecosystem',
    },
    'devto': {
        'trust_score': 8.0,
        'source_type': 'api',
        'api_endpoint': 'https://dev.to/api',
        'description': 'Dev.to community job board',
    },
    'indie_hackers': {
        'trust_score': 9.5,
        'source_type': 'web_scrape',
        'api_endpoint': 'https://indiehackers.com',
        'description': 'Indie Hackers community - founder-posted jobs',
    },
    'yc_jobs': {
        'trust_score': 9.5,
        'source_type': 'api',
        'api_endpoint': 'https://www.workatastartup.com',
        'description': 'Y Combinator job board - startup ecosystem',
    },
    
    # Medium-priority sources (Trust score: 5-7)
    'weworkremotely': {
        'trust_score': 7.0,
        'source_type': 'api',
        'api_endpoint': 'https://weworkremotely.com',
        'description': 'We Work Remotely - curated remote jobs',
    },
    'remotive': {
        'trust_score': 5.0,
        'source_type': 'api',
        'api_endpoint': 'https://remotive.com',
        'description': 'Remotive API - remote job aggregator',
    },
    'remoteok': {
        'trust_score': 4.0,
        'source_type': 'rss',
        'api_endpoint': 'https://remoteok.com',
        'description': 'RemoteOK RSS feed - volume source',
    },
    'workingnomads': {
        'trust_score': 4.0,
        'source_type': 'rss',
        'api_endpoint': 'https://workingnomads.com',
        'description': 'Working Nomads RSS feed - volume source',
    },
    'himalayas': {
        'trust_score': 4.0,
        'source_type': 'rss',
        'api_endpoint': 'https://himalayas.app',
        'description': 'Himalayas RSS feed - volume source',
    },
    'jobicy': {
        'trust_score': 5.0,
        'source_type': 'rss',
        'api_endpoint': 'https://jobicy.com',
        'description': 'Jobicy RSS feed',
    },
    'jobspresso': {
        'trust_score': 5.0,
        'source_type': 'rss',
        'api_endpoint': 'https://jobspresso.com',
        'description': 'Jobspresso RSS feed',
    },
    'justremote': {
        'trust_score': 4.0,
        'source_type': 'rss',
        'api_endpoint': 'https://justremote.co',
        'description': 'JustRemote RSS feed',
    },
    'nofluffjobs': {
        'trust_score': 5.0,
        'source_type': 'rss',
        'api_endpoint': 'https://nofluffjobs.com',
        'description': 'No Fluff Jobs RSS feed - European tech jobs',
    },
    'remoteco': {
        'trust_score': 5.0,
        'source_type': 'web_scrape',
        'api_endpoint': 'https://remote.co',
        'description': 'Remote.co web scraper',
    },
    'angellist': {
        'trust_score': 8.0,
        'source_type': 'api',
        'api_endpoint': 'https://angel.co',
        'description': 'AngelList API (legacy)',
    },
    'stackoverflow': {
        'trust_score': 7.0,
        'source_type': 'api',
        'api_endpoint': 'https://stackoverflow.com',
        'description': 'Stack Overflow Jobs API',
    },
    'arbeitsnow': {
        'trust_score': 4.0,
        'source_type': 'rss',
        'api_endpoint': 'https://arbeitsnow.com',
        'description': 'ArbeitNow RSS feed',
    },
}


def init_source_metadata():
    """Initialize source metadata table with default values."""
    db = SessionLocal()
    
    try:
        # Check if table exists and has data
        result = db.execute(text("SELECT COUNT(*) FROM source_metadata"))
        count = result.scalar()
        
        if count > 0:
            print(f"Source metadata already has {count} records. Skipping initialization.")
            print("To reinitialize, delete existing records first.")
            return
        
        print("Initializing source metadata...")
        
        for source_name, config in DEFAULT_SOURCES.items():
            db.execute(
                text("""
                INSERT INTO source_metadata 
                (source_name, trust_score, source_type, api_endpoint, is_active, created_at, updated_at)
                VALUES 
                (:source_name, :trust_score, :source_type, :api_endpoint, 1, :created_at, :updated_at)
                """),
                {
                    'source_name': source_name,
                    'trust_score': config['trust_score'],
                    'source_type': config['source_type'],
                    'api_endpoint': config['api_endpoint'],
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                }
            )
            print(f"  ✓ {source_name}: trust={config['trust_score']}, type={config['source_type']}")
        
        db.commit()
        print(f"\n✅ Successfully initialized {len(DEFAULT_SOURCES)} source metadata records")
        
        # Verify
        result = db.execute(text("SELECT COUNT(*) FROM source_metadata"))
        total = result.scalar()
        print(f"Total sources in database: {total}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error initializing source metadata: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_source_metadata()
