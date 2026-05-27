"""New adapter types for advanced scraping.

This module contains specialized adapters for different scraping methods:
- APIAdapter: For REST APIs with source-side filtering
- GraphQLAdapter: For GraphQL-based job boards
- PlaywrightAdapter: For JavaScript-rendered pages
- CareerPageAdapter: For company career pages
"""

from .api_adapter import APIAdapter
from .graphql_adapter import GraphQLAdapter
from .playwright_adapter import PlaywrightAdapter
from .career_page_adapter import CareerPageAdapter

__all__ = [
    "APIAdapter",
    "GraphQLAdapter",
    "PlaywrightAdapter",
    "CareerPageAdapter",
]
