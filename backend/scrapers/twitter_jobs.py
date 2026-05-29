"""Twitter/X.com job scraper - Scrapes job postings from Twitter.

Uses Twitter search to find job postings and opportunities.
"""

import logging
import re
from typing import List, Optional
from urllib.parse import quote

from scrapers.base import AuthRequiredError, BaseScraper
from scrapers.filters import RawJob, SearchCriteria
from scrapers.html_parser import HTMLParser

logger = logging.getLogger(__name__)

TWITTER_BASE_URL = "https://x.com"
TWITTER_SEARCH_URL = "https://x.com/search"


class TwitterJobsScraper(BaseScraper):
    """Twitter/X.com job scraper."""
    
    name = "twitter_jobs"
    
    # Common job-related hashtags and keywords
    JOB_KEYWORDS = [
        '#hiring', '#jobopening', '#jobalert', '#careers', 
        '#remotejobs', '#techjobs', '#developerjobs',
        'we are hiring', 'hiring now', 'job opening',
        'remote position', 'software engineer'
    ]
    
    def scrape(self, criteria: SearchCriteria | None = None) -> List[RawJob]:
        """Scrape jobs from X.com (formerly Twitter)."""
        jobs: List[RawJob] = []
        
        try:
            # Build search query
            query = self._build_search_query(criteria)
            url = self._build_search_url(query)
            
            resp = self.fetch(url)
            html = resp.text
            
            parser = HTMLParser(html, TWITTER_BASE_URL)
            
            # X.com tweet cards
            tweets = parser.soup.select('[data-testid="tweet"]')
            
            for tweet in tweets:
                try:
                    job = self._parse_tweet(tweet, parser)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Failed to parse X.com job: {e}")
                    continue
            
            # Deduplicate
            seen = set()
            unique_jobs = []
            for job in jobs:
                if job.external_id not in seen:
                    seen.add(job.external_id)
                    unique_jobs.append(job)
            
            logger.info(f"Twitter/X: Found {len(unique_jobs)} jobs")
            return unique_jobs
            
        except AuthRequiredError:
            logger.warning("X.com scraper blocked - requires login (API changed since rebrand)")
            return []
        except Exception as e:
            logger.error(f"Twitter/X scraping failed: {e}")
            return []
    
    def _build_search_query(self, criteria: SearchCriteria | None = None) -> str:
        """Build Twitter search query."""
        base_query = criteria.query if criteria else 'software engineer'
        
        # Add job-related keywords
        query_parts = [base_query]
        
        if criteria and criteria.remote_only:
            query_parts.append('remote')
        
        # Add hiring keywords
        query_parts.extend(['hiring', 'job'])
        
        return ' '.join(query_parts)
    
    def _build_search_url(self, query: str) -> str:
        """Build Twitter search URL."""
        encoded_query = quote(query)
        return f"{TWITTER_SEARCH_URL}?q={encoded_query}&src=typed_query"
    
    def _parse_tweet(self, tweet, parser: HTMLParser) -> Optional[RawJob]:
        """Parse job from tweet."""
        try:
            # Extract tweet text
            text_elem = tweet.select_one('[data-testid="tweetText"]')
            text = text_elem.get_text(strip=True) if text_elem else ''
            
            # Extract author/handle
            author_elem = tweet.select_one('[data-testid="User-Name"] a')
            author = author_elem.get_text(strip=True) if author_elem else ''
            
            # Extract URL
            link_elem = tweet.select_one('a[href*="status"]')
            tweet_url = link_elem.get('href', '') if link_elem else ''
            if tweet_url and not tweet_url.startswith('http'):
                tweet_url = urljoin(TWITTER_BASE_URL, tweet_url)
            
            if not text:
                return None
            
            # Check if tweet is job-related
            if not self._is_job_related(text):
                return None
            
            # Extract job title from text
            title = self._extract_job_title(text)
            
            # Extract company (use author if not found)
            company = self._extract_company(text) or author
            
            # Extract links from tweet
            links = parser.get_links('a[href]')
            job_url = ''
            for link in links:
                if any(domain in link['href'] for domain in ['linkedin.com', 'greenhouse.io', 'lever.co', 'myworkdayjobs.com']):
                    job_url = link['href']
                    break
            
            if not job_url:
                job_url = tweet_url
            
            # Extract location
            location = self._extract_location(text)
            
            # Generate external ID
            external_id = self.make_external_id(self.name, tweet_url, title)
            
            return RawJob(
                external_id=external_id,
                source=self.name,
                title=title,
                company=company,
                url=job_url,
                description=text,
                location=location,
                salary='',
                posted_at=''
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse tweet: {e}")
            return None
    
    def _is_job_related(self, text: str) -> bool:
        """Check if tweet is job-related."""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.JOB_KEYWORDS)
    
    def _extract_job_title(self, text: str) -> str:
        """Extract job title from tweet text."""
        # Look for common job title patterns
        patterns = [
            r'(?:we are|hiring for|looking for|seeking)\s+(?:a\s+)?([A-Z][a-zA-Z\s]+(?:Engineer|Developer|Manager|Designer|Analyst|Specialist))',
            r'(?:Senior|Junior|Lead|Principal)\s+(?:[A-Z][a-zA-Z]+\s+)?(?:Engineer|Developer|Manager)',
            r'(?:Software|Data|Product|Frontend|Backend|Full[- ]?Stack)\s+(?:Engineer|Developer|Manager)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback: use first few words
        words = text.split()[:5]
        return ' '.join(words)
    
    def _extract_company(self, text: str) -> Optional[str]:
        """Extract company name from tweet text."""
        # Look for @mentions
        mentions = re.findall(r'@(\w+)', text)
        if mentions:
            return mentions[0]
        
        # Look for common company patterns
        patterns = [
            r'(?:at|@)\s+([A-Z][a-zA-Z\s]+)',
            r'(?:join|work for)\s+([A-Z][a-zA-Z\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_location(self, text: str) -> str:
        """Extract location from tweet text."""
        text_lower = text.lower()
        
        # Check for remote
        if any(word in text_lower for word in ['remote', 'wfh', 'work from home']):
            return 'Remote'
        
        # Check for common locations
        locations = ['san francisco', 'new york', 'london', 'bangalore', 'mumbai', 'delhi']
        for loc in locations:
            if loc in text_lower:
                return loc.title()
        
        return 'Remote'
