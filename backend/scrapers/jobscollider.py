"""JobsCollider RSS scraper."""

from scrapers.rss_scraper import RSSScraper


class JobsColliderScraper(RSSScraper):
    name = "jobscollider"

    def __init__(self):
        super().__init__(
            name="jobscollider",
            feed_url="https://remotefirstjobs.com/rss/jobs.rss",
            default_location="Remote",
        )
