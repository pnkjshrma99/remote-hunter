"""Scraper health monitoring and reporting."""

import logging
from dataclasses import asdict
from typing import Dict, List

from scrapers.base import ScraperHealth
from scrapers.registry import get_all_scrapers

logger = logging.getLogger(__name__)


def get_scraper_health() -> Dict[str, dict]:
    """Get health status of all scrapers.
    
    Returns:
        Dictionary with scraper names and their health metrics
    """
    scrapers = get_all_scrapers()
    health_report = {}
    
    for scraper in scrapers:
        health_report[scraper.name] = asdict(scraper.health)
    
    return health_report


def get_healthy_scrapers() -> List[str]:
    """Get list of currently healthy scrapers.
    
    Returns:
        List of scraper names that are healthy
    """
    scrapers = get_all_scrapers()
    healthy = []
    
    for scraper in scrapers:
        if scraper.health.is_healthy():
            healthy.append(scraper.name)
    
    return healthy


def get_failed_scrapers() -> Dict[str, str]:
    """Get list of scrapers that have failed recently.
    
    Returns:
        Dictionary with scraper names and their last error
    """
    scrapers = get_all_scrapers()
    failed = {}
    
    for scraper in scrapers:
        if scraper.health.error_count > 0:
            failed[scraper.name] = {
                "error_count": scraper.health.error_count,
                "last_error": scraper.health.last_error,
                "last_run": scraper.health.last_run,
                "success_count": scraper.health.success_count,
            }
    
    return failed


def log_scraper_health_summary():
    """Log a summary of all scraper health status."""
    health_report = get_scraper_health()
    healthy_count = 0
    failed_count = 0
    disabled_count = 0
    
    logger.info("=" * 80)
    logger.info("SCRAPER HEALTH CHECK SUMMARY")
    logger.info("=" * 80)
    
    for name, health_data in health_report.items():
        if not health_data["enabled"]:
            logger.info("  %-20s: DISABLED", name)
            disabled_count += 1
        elif health_data["error_count"] > 0:
            logger.warning(
                "  %-20s: UNHEALTHY (errors: %d, last: %s)",
                name,
                health_data["error_count"],
                health_data["last_error"][:60] if health_data["last_error"] else "Unknown",
            )
            failed_count += 1
        else:
            logger.info(
                "  %-20s: OK (%d jobs, %d successful runs)",
                name,
                health_data["total_jobs"],
                health_data["success_count"],
            )
            healthy_count += 1
    
    logger.info("-" * 80)
    logger.info(
        "Summary: %d healthy, %d failed, %d disabled",
        healthy_count,
        failed_count,
        disabled_count,
    )
    logger.info("=" * 80)


def reset_scraper_health(scraper_name: str = None):
    """Reset health metrics for one or all scrapers.
    
    Args:
        scraper_name: Name of specific scraper to reset, or None for all
    """
    scrapers = get_all_scrapers()
    
    for scraper in scrapers:
        if scraper_name is None or scraper.name == scraper_name:
            scraper.health.error_count = 0
            scraper.health.success_count = 0
            scraper.health.last_error = None
            scraper.health.last_run = None
            logger.info("Reset health for %s", scraper.name)
