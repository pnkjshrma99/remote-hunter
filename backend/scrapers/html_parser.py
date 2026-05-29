"""Enhanced HTML parsing utilities for web scrapers.

Provides robust HTML parsing with BeautifulSoup, including:
- Safe text extraction
- Link extraction
- Metadata parsing
- Salary extraction
- Location parsing
"""

import re
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class HTMLParser:
    """Enhanced HTML parser with utility methods for job scraping."""

    def __init__(self, html: str, base_url: str = ""):
        """Initialize parser with HTML content.
        
        Args:
            html: HTML content to parse
            base_url: Base URL for resolving relative links
        """
        self.soup = BeautifulSoup(html, 'html.parser')
        self.base_url = base_url

    def get_text(self, selector: str, default: str = "", clean: bool = True) -> str:
        """Extract text from CSS selector.
        
        Args:
            selector: CSS selector
            default: Default value if not found
            clean: Whether to clean whitespace
            
        Returns:
            Extracted text or default
        """
        element = self.soup.select_one(selector)
        if not element:
            return default
        
        text = element.get_text(strip=True) if clean else element.get_text()
        return text or default

    def get_attribute(self, selector: str, attribute: str, default: str = "") -> str:
        """Extract attribute from CSS selector.
        
        Args:
            selector: CSS selector
            attribute: Attribute name (e.g., 'href', 'src')
            default: Default value if not found
            
        Returns:
            Attribute value or default
        """
        element = self.soup.select_one(selector)
        if not element:
            return default
        
        value = element.get(attribute, "")
        return value or default

    def get_texts(self, selector: str, clean: bool = True) -> List[str]:
        """Extract texts from all matching CSS selectors.
        
        Args:
            selector: CSS selector
            clean: Whether to clean whitespace
            
        Returns:
            List of extracted texts
        """
        elements = self.soup.select(selector)
        texts = []
        for element in elements:
            text = element.get_text(strip=True) if clean else element.get_text()
            if text:
                texts.append(text)
        return texts

    def get_links(self, selector: str = "a[href]") -> List[Dict[str, str]]:
        """Extract all links matching selector.
        
        Args:
            selector: CSS selector for links (default: all links)
            
        Returns:
            List of dicts with 'text' and 'href' keys
        """
        links = []
        for link in self.soup.select(selector):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if href:
                # Resolve relative URLs
                if self.base_url:
                    href = urljoin(self.base_url, href)
                links.append({'text': text, 'href': href})
        return links

    def get_meta(self, name: str, default: str = "") -> str:
        """Extract meta tag content by name or property.
        
        Args:
            name: Meta name or property
            default: Default value if not found
            
        Returns:
            Meta content or default
        """
        # Try by name first
        meta = self.soup.find('meta', attrs={'name': name})
        if meta:
            return meta.get('content', default)
        
        # Try by property (Open Graph, Twitter cards)
        meta = self.soup.find('meta', attrs={'property': name})
        if meta:
            return meta.get('content', default)
        
        return default

    def get_json_ld(self) -> List[Dict[str, Any]]:
        """Extract all JSON-LD structured data.
        
        Returns:
            List of parsed JSON-LD objects
        """
        import json
        
        json_lds = []
        scripts = self.soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    json_lds.extend(data)
                else:
                    json_lds.append(data)
            except (json.JSONDecodeError, AttributeError):
                continue
        return json_lds

    def extract_salary(self, text: str) -> Dict[str, Any]:
        """Extract salary information from text.
        
        Args:
            text: Text containing salary information
            
        Returns:
            Dict with salary_min, salary_max, currency, period
        """
        salary_info = {
            'salary_min': None,
            'salary_max': None,
            'currency': 'USD',
            'period': 'yearly',
            'raw': text
        }
        
        if not text:
            return salary_info
        
        # Common currency symbols
        currency_map = {
            '$': 'USD',
            '€': 'EUR',
            '£': 'GBP',
            '₹': 'INR',
            '¥': 'JPY',
            'AUD': 'AUD',
            'CAD': 'CAD',
        }
        
        # Detect currency
        for symbol, currency in currency_map.items():
            if symbol in text:
                salary_info['currency'] = currency
                break
        
        # Detect period
        text_lower = text.lower()
        if any(word in text_lower for word in ['hour', 'hr', '/hr', 'per hour']):
            salary_info['period'] = 'hourly'
        elif any(word in text_lower for word in ['month', 'mo', '/mo', 'per month']):
            salary_info['period'] = 'monthly'
        elif any(word in text_lower for word in ['year', 'yr', '/yr', 'per year', 'annually']):
            salary_info['period'] = 'yearly'
        
        # Extract numbers
        # Pattern: $50,000 - $80,000 or 50k-80k or 50000-80000
        patterns = [
            r'[\$€£₹¥]?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*[-–to]\s*[\$€£₹¥]?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
            r'(\d{1,3})k?\s*[-–to]\s*(\d{1,3})k?',
            r'(\d{5,7})\s*[-–to]\s*(\d{5,7})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                min_str = match.group(1).replace(',', '').replace('k', '000')
                max_str = match.group(2).replace(',', '').replace('k', '000')
                try:
                    salary_info['salary_min'] = int(float(min_str))
                    salary_info['salary_max'] = int(float(max_str))
                    break
                except ValueError:
                    continue
        
        # Single number case
        if not salary_info['salary_min']:
            single_match = re.search(r'[\$€£₹¥]?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*[kK]?', text)
            if single_match:
                num_str = single_match.group(1).replace(',', '').replace('k', '000')
                try:
                    salary_info['salary_min'] = int(float(num_str))
                    salary_info['salary_max'] = salary_info['salary_min']
                except ValueError:
                    pass
        
        return salary_info

    def extract_location(self, text: str) -> Dict[str, str]:
        """Extract location information from text.
        
        Args:
            text: Text containing location information
            
        Returns:
            Dict with city, country, remote_type
        """
        location_info = {
            'city': '',
            'country': '',
            'remote_type': 'unknown',
            'raw': text
        }
        
        if not text:
            return location_info
        
        text_lower = text.lower()
        
        # Detect remote type
        if any(word in text_lower for word in ['remote', 'wfh', 'work from home', 'telecommute']):
            location_info['remote_type'] = 'remote'
        elif any(word in text_lower for word in ['hybrid', 'flexible']):
            location_info['remote_type'] = 'hybrid'
        elif any(word in text_lower for word in ['onsite', 'on-site', 'office']):
            location_info['remote_type'] = 'onsite'
        
        # Common countries
        countries = ['united states', 'usa', 'us', 'united kingdom', 'uk', 'canada', 
                    'australia', 'germany', 'france', 'india', 'netherlands', 'spain']
        for country in countries:
            if country in text_lower:
                location_info['country'] = country.title()
                break
        
        # Try to extract city (simplified)
        # This is a basic implementation - could be enhanced with a proper location database
        words = text.split(',')
        if len(words) > 0:
            location_info['city'] = words[0].strip()
        
        return location_info

    def clean_text(self, text: str) -> str:
        """Clean and normalize text.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove HTML entities
        text = BeautifulSoup(text, 'html.parser').get_text()
        
        return text.strip()

    def extract_job_details(self) -> Dict[str, Any]:
        """Extract common job details from HTML.
        
        Returns:
            Dict with title, company, description, location, salary, etc.
        """
        details = {
            'title': '',
            'company': '',
            'description': '',
            'location': '',
            'salary': '',
            'posted_at': '',
            'url': '',
        }
        
        # Try JSON-LD first (most reliable)
        json_lds = self.get_json_ld()
        for json_ld in json_lds:
            if json_ld.get('@type') == 'JobPosting':
                details['title'] = json_ld.get('title', details['title'])
                details['company'] = json_ld.get('hiringOrganization', {}).get('name', details['company'])
                details['description'] = json_ld.get('description', details['description'])
                details['location'] = json_ld.get('jobLocation', {}).get('address', {}).get('addressLocality', details['location'])
                details['salary'] = json_ld.get('baseSalary', {}).get('value', {}).get('text', details['salary'])
                details['url'] = json_ld.get('url', details['url'])
                if json_ld.get('datePosted'):
                    details['posted_at'] = json_ld['datePosted']
                break
        
        # Try meta tags
        if not details['title']:
            details['title'] = self.get_meta('title') or self.get_text('h1')
        
        if not details['description']:
            details['description'] = self.get_meta('description') or self.get_text('[class*="description"], [class*="job-description"]')
        
        # Try common selectors
        if not details['company']:
            details['company'] = self.get_text('[class*="company"], [class*="employer"]')
        
        if not details['location']:
            details['location'] = self.get_text('[class*="location"], [class*="job-location"]')
        
        if not details['salary']:
            details['salary'] = self.get_text('[class*="salary"], [class*="compensation"]')
        
        return details

    def get_table_data(self, table_selector: str) -> List[Dict[str, str]]:
        """Extract data from HTML table.
        
        Args:
            table_selector: CSS selector for table
            
        Returns:
            List of dicts with column headers as keys
        """
        table = self.soup.select_one(table_selector)
        if not table:
            return []
        
        headers = []
        header_row = table.find('tr')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        rows = []
        for row in table.find_all('tr')[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            if len(cells) == len(headers):
                row_data = {headers[i]: cells[i].get_text(strip=True) for i in range(len(headers))}
                rows.append(row_data)
        
        return rows

    def find_by_regex(self, pattern: str, text_content: bool = True) -> List[str]:
        """Find elements matching regex pattern.
        
        Args:
            pattern: Regex pattern to search for
            text_content: Whether to search in text content (True) or HTML (False)
            
        Returns:
            List of matching text/HTML snippets
        """
        matches = []
        regex = re.compile(pattern, re.IGNORECASE)
        
        if text_content:
            for element in self.soup.find_all(string=True):
                if regex.search(element):
                    matches.append(element.strip())
        else:
            for element in self.soup.find_all():
                if regex.search(str(element)):
                    matches.append(str(element))
        
        return matches


def parse_html(html: str, base_url: str = "") -> HTMLParser:
    """Convenience function to create HTMLParser instance.
    
    Args:
        html: HTML content to parse
        base_url: Base URL for resolving relative links
        
    Returns:
        HTMLParser instance
    """
    return HTMLParser(html, base_url)
