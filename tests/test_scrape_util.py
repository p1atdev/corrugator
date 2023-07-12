import unittest

import sys

sys.path.append("..")

from scrape_util import DanbooruScraper, get_posts
from tags import (
    SENSITIVE_TAGS,
    VIOLENCE_TAGS,
    DEFAULT_EXLUSION_META_TAGS,
)


class TestScrapeUtil(unittest.TestCase):
    def test_scraper_get_posts(self):
        scraper = DanbooruScraper()

        posts = scraper.get_posts("1girl", page=1, limit_per_page=20)

        self.assertEqual(len(posts), 20)

    def test_get_posts(self):
        scraper = DanbooruScraper()

        posts = get_posts(
            scraper,
            "2girls",
            exclusion_general_tags=SENSITIVE_TAGS + VIOLENCE_TAGS,
            total_limit=1000,
        )

        self.assertEqual(len(posts), 1000)

        for post in posts:
            self.assertFalse(any(tag in SENSITIVE_TAGS for tag in post.general_tags))
            self.assertFalse(any(tag in VIOLENCE_TAGS for tag in post.general_tags))
            self.assertFalse(
                any(tag in DEFAULT_EXLUSION_META_TAGS for tag in post.meta_tags)
            )


if __name__ == "__main__":
    unittest.main()
