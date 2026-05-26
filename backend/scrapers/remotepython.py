"""RemotePython.com RSS scraper."""

from scrapers.rss_scraper import RSSScraper


class RemotePythonScraper(RSSScraper):
    name = "remotepython"

    def __init__(self):
        super().__init__(
            name="remotepython",
            feed_url="https://www.remotepython.com/latest/jobs/feed/",
            default_location="Remote",
        )
