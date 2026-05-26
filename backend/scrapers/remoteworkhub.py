"""Remote Work Hub RSS scraper."""

from scrapers.rss_scraper import RSSScraper


class RemoteWorkHubScraper(RSSScraper):
    name = "remoteworkhub"

    def __init__(self):
        super().__init__(
            name="remoteworkhub",
            feed_url="https://remoteworkhub.com/feed/",
            default_location="Remote",
        )
