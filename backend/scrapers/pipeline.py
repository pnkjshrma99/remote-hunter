"""Integrated scraping pipeline.

This module provides a unified pipeline that orchestrates:
1. Scraping from multiple sources with source-side filtering
2. Normalization to standard schema
3. Relevance scoring
4. Deduplication
5. Deep description fetching (fills truncated descriptions from job pages)
6. LLM enrichment (optional)
7. Quality filtering
"""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from threading import Lock
from typing import List, Optional, Dict, Any
from datetime import datetime

from scrapers.base import BaseScraper
from scrapers.filters import RawJob
from scrapers.schemas import SearchCriteria, NormalizedJob
from scrapers.scoring import JobScorer, filter_by_relevance
from scrapers.deduplication import JobDeduplicator, deduplicate_jobs
from scrapers.llm_enrichment import LLMEnricher, enrich_jobs_with_llm
from scrapers.gemini_enricher import GeminiEnricher
from scrapers.description_fetcher import enrich_descriptions as fetch_descriptions
from scrapers.registry import get_all_scrapers
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ScrapingPipeline:
    """Integrated pipeline for job scraping with scoring, deduplication, and enrichment."""
    
    def __init__(
        self,
        enable_scoring: bool = True,
        enable_deduplication: bool = True,
        enable_description_fetch: bool = True,
        enable_llm_enrichment: bool = None,
        min_relevance_score: float = 0.5,
        llm_enrichment_threshold: float = 0.7,
        description_fetch_workers: int = 5,
        description_fetch_delay: float = 0.3,
    ):
        self.enable_scoring = enable_scoring
        self.enable_deduplication = enable_deduplication
        self.enable_description_fetch = enable_description_fetch
        self.enable_llm_enrichment = enable_llm_enrichment if enable_llm_enrichment is not None else settings.llm_enabled
        self.min_relevance_score = min_relevance_score
        self.llm_enrichment_threshold = llm_enrichment_threshold
        self.description_fetch_workers = description_fetch_workers
        self.description_fetch_delay = description_fetch_delay
        
        self.deduplicator = JobDeduplicator() if enable_deduplication else None
        self.gemini_enricher = GeminiEnricher() if enable_llm_enrichment else None
        self.llm_enricher = LLMEnricher() if self.enable_llm_enrichment and not self.gemini_enricher.enabled else None
        
        logger.info(
            f"Pipeline initialized: scoring={enable_scoring}, "
            f"dedup={enable_deduplication}, "
            f"description_fetch={enable_description_fetch}, "
            f"llm={'gemini' if self.gemini_enricher and self.gemini_enricher.enabled else 'openai' if self.llm_enricher else 'disabled'}"
        )
    
    def run(
        self,
        criteria: SearchCriteria,
        source_names: Optional[List[str]] = None,
        max_results: Optional[int] = None
    ) -> "PipelineResult":
        """Run the complete scraping pipeline.
        
        Pipeline stages:
        1. Scrape from sources with source-side filtering
        2. Normalize to standard schema
        3. Score by relevance
        4. Deduplicate
        5. Deep description fetch (fills truncated descriptions from job pages)
        6. LLM enrich (optional)
        7. Filter by relevance
        
        Args:
            criteria: Search criteria
            source_names: Optional list of source names to run
            max_results: Maximum number of results to return
            
        Returns:
            PipelineResult with jobs and metrics
        """
        start_time = datetime.utcnow()
        result = PipelineResult()
        
        try:
            # Stage 1: Scrape with source-side filtering
            logger.info("Stage 1: Scraping from sources")
            raw_jobs = self._scrape_sources(criteria, source_names)
            result.raw_jobs_count = len(raw_jobs)
            logger.info(f"Fetched {len(raw_jobs)} raw jobs")
            
            # Stage 2: Normalize to standard schema
            logger.info("Stage 2: Normalizing jobs")
            normalized_jobs = self._normalize_jobs(raw_jobs)
            result.normalized_jobs_count = len(normalized_jobs)
            logger.info(f"Normalized {len(normalized_jobs)} jobs")
            
            # Stage 3: Score by relevance (parallel)
            if self.enable_scoring:
                logger.info("Stage 3: Scoring jobs by relevance")
                scorer = JobScorer(criteria)
                
                def _score_single(job: NormalizedJob) -> NormalizedJob:
                    job.relevance_score = scorer.calculate_score(job)
                    return job
                
                score_workers = min(len(normalized_jobs), 20) if normalized_jobs else 1
                if score_workers > 1:
                    with ThreadPoolExecutor(max_workers=score_workers) as score_exec:
                        normalized_jobs = list(score_exec.map(_score_single, normalized_jobs))
                else:
                    for job in normalized_jobs:
                        job.relevance_score = scorer.calculate_score(job)
                result.scoring_complete = True
            
            # Stage 4: Deduplicate
            if self.enable_deduplication:
                logger.info("Stage 4: Deduplicating jobs")
                normalized_jobs = deduplicate_jobs(normalized_jobs)
                result.deduplication_complete = True
                result.duplicates_removed = result.normalized_jobs_count - len(normalized_jobs)
                logger.info(f"Removed {result.duplicates_removed} duplicates")
            
            # Stage 5: Deep description fetch
            if self.enable_description_fetch:
                logger.info("Stage 5: Fetching full descriptions")
                normalized_jobs = fetch_descriptions(
                    normalized_jobs,
                    max_workers=self.description_fetch_workers,
                    delay=self.description_fetch_delay,
                )
                result.description_fetch_complete = True
                result.descriptions_fetched = sum(
                    1 for j in normalized_jobs if j.description and len(j.description) >= 100
                )
                logger.info(f"Fetched descriptions for {result.descriptions_fetched} jobs")
            
            # Stage 6: LLM enrichment (optional — tries Gemini first, falls back to OpenAI)
            if self.enable_llm_enrichment:
                if self.gemini_enricher and self.gemini_enricher.enabled:
                    logger.info("Stage 6: Gemini enrichment")
                    normalized_jobs = self.gemini_enricher.enrich_batch(
                        normalized_jobs,
                        min_relevance=self.llm_enrichment_threshold
                    )
                    result.llm_enrichment_complete = True
                    result.llm_enriched_count = sum(
                        1 for j in normalized_jobs if j.confidence_score > 0
                    )
                    logger.info(f"Enriched {result.llm_enriched_count} jobs with Gemini")
                elif self.llm_enricher:
                    logger.info("Stage 6: OpenAI LLM enrichment (Gemini unavailable)")
                    normalized_jobs = self.llm_enricher.enrich_batch(
                        normalized_jobs,
                        min_relevance=self.llm_enrichment_threshold
                    )
                    result.llm_enrichment_complete = True
                    result.llm_enriched_count = sum(
                        1 for j in normalized_jobs if j.confidence_score > 0
                    )
                    logger.info(f"Enriched {result.llm_enriched_count} jobs with OpenAI")
                else:
                    logger.info("Stage 6: LLM enrichment skipped (no API key configured)")
            
            # Stage 7: Filter by relevance
            if self.enable_scoring:
                logger.info("Stage 7: Filtering by relevance")
                normalized_jobs = filter_by_relevance(
                    normalized_jobs,
                    criteria,
                    min_score=self.min_relevance_score,
                    max_results=max_results
                )
                result.filtered_jobs_count = len(normalized_jobs)
            
            result.jobs = normalized_jobs
            result.success = True
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            result.success = False
            result.error = str(e)
        
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            result.duration_seconds = round(duration, 2)
            logger.info(f"Pipeline complete: {result}")
        
        return result
    
    def _scrape_sources(
        self,
        criteria: SearchCriteria,
        source_names: Optional[List[str]] = None
    ) -> List[RawJob]:
        """Scrape jobs from sources with source-side filtering (parallel execution).
        
        Uses ThreadPoolExecutor to scrape from all sources concurrently,
        dramatically reducing total response time while respecting each
        scraper's rate limiting.
        """
        scrapers = get_all_scrapers(source_names=source_names)
        if not scrapers:
            logger.warning("No scrapers configured to run")
            return []
        
        max_workers = min(len(scrapers), settings.scraper_max_parallel)
        all_jobs: List[RawJob] = []
        seen_ids: set = set()
        lock = Lock()
        
        def _run_single_scraper(scraper: BaseScraper) -> List[RawJob]:
            """Execute a single scraper and return its jobs, handling errors."""
            try:
                jobs = scraper.run(criteria=criteria)
                logger.info(f"{scraper.name}: {len(jobs)} jobs (parallel)")
                return jobs
            except Exception as e:
                logger.error(f"{scraper.name}: Failed to scrape in parallel: {e}")
                return []
        
        logger.info(
            f"Scraping {len(scrapers)} sources in parallel "
            f"(max_workers={max_workers})"
        )
        
        executor = ThreadPoolExecutor(max_workers=max_workers)
        future_to_scraper = {
            executor.submit(_run_single_scraper, scraper): scraper
            for scraper in scrapers
        }
        
        try:
            timeout_sec = settings.pipeline_scrape_timeout
            for future in as_completed(future_to_scraper, timeout=timeout_sec):
                scraper = future_to_scraper[future]
                try:
                    jobs = future.result()
                    with lock:
                        for job in jobs:
                            if job.external_id not in seen_ids:
                                seen_ids.add(job.external_id)
                                all_jobs.append(job)
                except Exception as e:
                    logger.error(f"{scraper.name}: Unexpected parallel error: {e}")
        except TimeoutError:
            logger.warning(f"Parallel scrape timed out after {timeout_sec}s, collected %d jobs", len(all_jobs))
        finally:
            for f in future_to_scraper:
                f.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
        
        logger.info(f"Total unique jobs from parallel scrape: {len(all_jobs)}")
        return all_jobs
    
    def _normalize_jobs(self, raw_jobs: List[RawJob]) -> List[NormalizedJob]:
        """Normalize raw jobs to standard schema."""
        normalized = []
        
        for raw_job in raw_jobs:
            try:
                normalized_job = NormalizedJob.from_raw_job(raw_job)
                normalized.append(normalized_job)
            except Exception as e:
                logger.warning(f"Failed to normalize job {raw_job.external_id}: {e}")
        
        return normalized


class PipelineResult:
    """Result from scraping pipeline."""
    
    def __init__(self):
        self.success: bool = False
        self.jobs: List[NormalizedJob] = []
        self.raw_jobs_count: int = 0
        self.normalized_jobs_count: int = 0
        self.duplicates_removed: int = 0
        self.descriptions_fetched: int = 0
        self.filtered_jobs_count: int = 0
        self.llm_enriched_count: int = 0
        self.scoring_complete: bool = False
        self.deduplication_complete: bool = False
        self.description_fetch_complete: bool = False
        self.llm_enrichment_complete: bool = False
        self.duration_seconds: float = 0.0
        self.error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "jobs_count": len(self.jobs),
            "raw_jobs_count": self.raw_jobs_count,
            "normalized_jobs_count": self.normalized_jobs_count,
            "duplicates_removed": self.duplicates_removed,
            "descriptions_fetched": self.descriptions_fetched,
            "filtered_jobs_count": self.filtered_jobs_count,
            "llm_enriched_count": self.llm_enriched_count,
            "scoring_complete": self.scoring_complete,
            "deduplication_complete": self.deduplication_complete,
            "description_fetch_complete": self.description_fetch_complete,
            "llm_enrichment_complete": self.llm_enrichment_complete,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }
    
    def __str__(self) -> str:
        return (
            f"PipelineResult(success={self.success}, "
            f"jobs={len(self.jobs)}, "
            f"raw={self.raw_jobs_count}, "
            f"duplicates_removed={self.duplicates_removed}, "
            f"descriptions_fetched={self.descriptions_fetched}, "
            f"duration={self.duration_seconds}s)"
        )


def run_pipeline(
    criteria: SearchCriteria,
    source_names: Optional[List[str]] = None,
    max_results: Optional[int] = None,
    enable_scoring: bool = True,
    enable_deduplication: bool = True,
    enable_description_fetch: bool = True,
    enable_llm_enrichment: Optional[bool] = None,
) -> "PipelineResult":
    """Convenience function to run the scraping pipeline.
    
    Args:
        criteria: Search criteria
        source_names: Optional list of source names to run
        max_results: Maximum number of results to return
        enable_scoring: Enable relevance scoring
        enable_deduplication: Enable deduplication
        enable_description_fetch: Enable deep description fetching
        enable_llm_enrichment: Enable LLM enrichment (uses config if None)
    
    Returns:
        PipelineResult with jobs and metrics
    """
    pipeline = ScrapingPipeline(
        enable_scoring=enable_scoring,
        enable_deduplication=enable_deduplication,
        enable_description_fetch=enable_description_fetch,
        enable_llm_enrichment=enable_llm_enrichment,
    )
    return pipeline.run(criteria, source_names=source_names, max_results=max_results)
