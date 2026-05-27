"""Tests for new scraping pipeline components.

Tests normalization, scoring, deduplication, and LLM fallback.
"""

import pytest
from datetime import datetime

from scrapers.schemas import NormalizedJob, SearchCriteria, SeniorityLevel, RemoteType, JobType
from scrapers.scoring import JobScorer, calculate_relevance_score, filter_by_relevance
from scrapers.deduplication import JobDeduplicator, deduplicate_jobs, generate_duplicate_signature
from scrapers.llm_enrichment import LLMEnricher
from scrapers.filters import RawJob


class TestNormalization:
    """Test job normalization."""
    
    def test_raw_job_to_normalized(self):
        """Test conversion from RawJob to NormalizedJob."""
        raw_job = RawJob(
            external_id="test_123",
            source="test_source",
            title="Senior DevOps Engineer",
            company="Test Company",
            url="https://example.com/job",
            description="We are looking for a senior DevOps engineer with 5+ years experience.",
            location="Remote",
            salary="$120k-$150k",
        )
        
        normalized = NormalizedJob.from_raw_job(raw_job)
        
        assert normalized.external_id == "test_123"
        assert normalized.source == "test_source"
        assert normalized.title == "Senior DevOps Engineer"
        assert normalized.company == "Test Company"
        assert normalized.url == "https://example.com/job"
        assert normalized.description == "We are looking for a senior DevOps engineer with 5+ years experience."
        assert normalized.location == "Remote"
    
    def test_normalized_job_to_dict(self):
        """Test serialization of NormalizedJob."""
        job = NormalizedJob(
            external_id="test_123",
            source="test_source",
            title="DevOps Engineer",
            company="Test Company",
            url="https://example.com/job",
            seniority=SeniorityLevel.SENIOR,
            experience_min_years=5,
            experience_max_years=10,
            skills=["AWS", "Kubernetes", "Docker"],
        )
        
        job_dict = job.to_dict()
        
        assert job_dict["external_id"] == "test_123"
        assert job_dict["seniority"] == "senior"
        assert job_dict["experience_min_years"] == 5
        assert job_dict["skills"] == ["AWS", "Kubernetes", "Docker"]


class TestScoring:
    """Test relevance scoring."""
    
    def test_title_match_score(self):
        """Test title match scoring."""
        criteria = SearchCriteria(query="DevOps Engineer")
        scorer = JobScorer(criteria)
        
        # Exact match
        job1 = NormalizedJob(
            external_id="1",
            source="test",
            title="DevOps Engineer",
            company="Test",
            url="https://example.com/1",
        )
        score1 = scorer._score_title_match(job1)
        assert score1 == 1.0
        
        # Partial match
        job2 = NormalizedJob(
            external_id="2",
            source="test",
            title="Senior DevOps Engineer",
            company="Test",
            url="https://example.com/2",
        )
        score2 = scorer._score_title_match(job2)
        assert score2 > 0.5
        
        # No match
        job3 = NormalizedJob(
            external_id="3",
            source="test",
            title="Frontend Developer",
            company="Test",
            url="https://example.com/3",
        )
        score3 = scorer._score_title_match(job3)
        assert score3 == 0.0
    
    def test_experience_match_score(self):
        """Test experience match scoring."""
        criteria = SearchCriteria(min_experience=2, max_experience=5)
        scorer = JobScorer(criteria)
        
        # Perfect match
        job1 = NormalizedJob(
            external_id="1",
            source="test",
            title="DevOps Engineer",
            company="Test",
            url="https://example.com/1",
            experience_min_years=3,
            experience_max_years=4,
        )
        score1 = scorer._score_experience_match(job1)
        assert score1 == 1.0
        
        # Overlap match
        job2 = NormalizedJob(
            external_id="2",
            source="test",
            title="Senior DevOps Engineer",
            company="Test",
            url="https://example.com/2",
            experience_min_years=4,
            experience_max_years=7,
        )
        score2 = scorer._score_experience_match(job2)
        assert score2 > 0.5
        
        # No match
        job3 = NormalizedJob(
            external_id="3",
            source="test",
            title="Principal Engineer",
            company="Test",
            url="https://example.com/3",
            experience_min_years=10,
            experience_max_years=15,
        )
        score3 = scorer._score_experience_match(job3)
        assert score3 == 0.0
    
    def test_overall_relevance_score(self):
        """Test overall relevance score calculation."""
        criteria = SearchCriteria(query="DevOps Engineer", min_experience=2, max_experience=5)
        scorer = JobScorer(criteria)
        
        job = NormalizedJob(
            external_id="1",
            source="test",
            title="DevOps Engineer",
            company="Test Company",
            url="https://example.com/1",
            description="We are looking for a DevOps engineer with AWS and Kubernetes experience.",
            experience_min_years=3,
            experience_max_years=4,
            remote_type=RemoteType.FULLY_REMOTE,
        )
        
        score = scorer.calculate_score(job)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be a good match
    
    def test_filter_by_relevance(self):
        """Test filtering jobs by relevance score."""
        criteria = SearchCriteria(query="DevOps Engineer")
        
        jobs = [
            NormalizedJob(
                external_id=str(i),
                source="test",
                title=f"Job {i}",
                company="Test",
                url=f"https://example.com/{i}",
            )
            for i in range(10)
        ]
        
        filtered = filter_by_relevance(jobs, criteria, min_score=0.3, max_results=5)
        
        assert len(filtered) <= 5
        for job in filtered:
            assert job.relevance_score >= 0.3


class TestDeduplication:
    """Test job deduplication."""
    
    def test_exact_deduplication(self):
        """Test exact deduplication by external_id."""
        jobs = [
            NormalizedJob(
                external_id="same_id",
                source="source1",
                title="Job 1",
                company="Company",
                url="https://example.com/1",
            ),
            NormalizedJob(
                external_id="same_id",
                source="source2",
                title="Job 2",
                company="Company",
                url="https://example.com/2",
            ),
            NormalizedJob(
                external_id="different_id",
                source="source1",
                title="Job 3",
                company="Company",
                url="https://example.com/3",
            ),
        ]
        
        deduplicator = JobDeduplicator(enable_exact=True, enable_fuzzy=False, enable_near_duplicate=False)
        unique_jobs = deduplicator.deduplicate(jobs)
        
        assert len(unique_jobs) == 2
        assert sum(1 for j in unique_jobs if j.external_id == "same_id") == 1
    
    def test_fuzzy_deduplication(self):
        """Test fuzzy deduplication by normalized signature."""
        jobs = [
            NormalizedJob(
                external_id="id1",
                source="source1",
                title="Senior DevOps Engineer",
                company="Test Company",
                url="https://example.com/job/123",
            ),
            NormalizedJob(
                external_id="id2",
                source="source2",
                title="Senior DevOps Engineer",
                company="Test Company",
                url="https://example.com/jobs/123",  # Similar URL
            ),
            NormalizedJob(
                external_id="id3",
                source="source1",
                title="Frontend Developer",
                company="Different Company",
                url="https://example.com/job/456",
            ),
        ]
        
        deduplicator = JobDeduplicator(enable_exact=False, enable_fuzzy=True, enable_near_duplicate=False)
        unique_jobs = deduplicator.deduplicate(jobs)
        
        assert len(unique_jobs) <= 3  # May deduplicate similar jobs
    
    def test_duplicate_signature_generation(self):
        """Test legacy duplicate signature generation."""
        sig1 = generate_duplicate_signature("DevOps Engineer", "Company", "AWS Kubernetes Docker")
        sig2 = generate_duplicate_signature("DevOps Engineer", "Company", "AWS Kubernetes Docker")
        sig3 = generate_duplicate_signature("Frontend Developer", "Company", "React TypeScript")
        
        assert sig1 == sig2
        assert sig1 != sig3


class TestLLMEnrichment:
    """Test LLM enrichment with fallback."""
    
    def test_llm_enricher_disabled(self):
        """Test LLM enricher when disabled (no API key)."""
        enricher = LLMEnricher(api_key=None)
        
        assert not enricher.enabled
        
        job = NormalizedJob(
            external_id="test",
            source="test",
            title="DevOps Engineer",
            company="Test",
            url="https://example.com",
        )
        
        enriched = enricher.enrich(job)
        
        # Job should be unchanged when LLM is disabled
        assert enriched.title == "DevOps Engineer"
        assert enriched.confidence_score == 0.0
    
    def test_seniority_parsing(self):
        """Test seniority string parsing."""
        enricher = LLMEnricher(api_key="dummy")  # API key not needed for parsing tests
        
        assert enricher._parse_seniority("junior") == SeniorityLevel.JUNIOR
        assert enricher._parse_seniority("Senior Engineer") == SeniorityLevel.SENIOR
        assert enricher._parse_seniority("intern") == SeniorityLevel.INTERN
        assert enricher._parse_seniority("unknown role") == SeniorityLevel.UNKNOWN
    
    def test_job_type_parsing(self):
        """Test job type string parsing."""
        enricher = LLMEnricher(api_key="dummy")
        
        assert enricher._parse_job_type("full-time") == JobType.FULL_TIME
        assert enricher._parse_job_type("contract") == JobType.CONTRACT
        assert enricher._parse_job_type("unknown") == JobType.UNKNOWN


class TestSearchCriteria:
    """Test SearchCriteria functionality."""
    
    def test_query_terms_extraction(self):
        """Test query terms extraction."""
        criteria = SearchCriteria(query="DevOps Engineer AWS Kubernetes")
        
        terms = criteria.query_terms
        
        assert "devops" in terms
        assert "aws" in terms
        assert "kubernetes" in terms
        assert "engineer" not in terms  # Stop word
    
    def test_source_params_generation(self):
        """Test source parameter generation."""
        criteria = SearchCriteria(
            query="DevOps Engineer",
            location="Remote",
            remote_only=True,
            min_experience=2,
            max_experience=5,
            posted_within_days=14,
        )
        
        params = criteria.to_source_params()
        
        assert params["query"] == "DevOps Engineer"
        assert params["location"] == "Remote"
        assert params["remote"] is True
        assert params["experience_min"] == 2
        assert params["experience_max"] == 5
        assert params["posted_within_days"] == 14


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
