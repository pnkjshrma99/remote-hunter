"""Virtual Vocations RSS scraper."""

from scrapers.rss_scraper import RSSScraper


class VirtualVocationsScraper(RSSScraper):
    name = "virtualvocations"

    def __init__(self):
        super().__init__(
            name="virtualvocations",
            feed_url="https://www.virtualvocations.com/jobs/rss",
            default_location="Remote",
        )
