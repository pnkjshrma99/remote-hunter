"""FOSS Jobs RSS scraper."""

from scrapers.rss_scraper import RSSScraper


class FOSSJobsScraper(RSSScraper):
    name = "fossjobs"

    def __init__(self):
        super().__init__(
            name="fossjobs",
            feed_url="https://www.fossjobs.net/rss/all/",
            default_location="Remote",
        )
