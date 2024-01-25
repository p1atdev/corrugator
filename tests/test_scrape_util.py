import unittest

import sys

sys.path.append("..")

import utils
from scrape_util import DanbooruScraper, get_posts
from scrape_config import SearchResultFilterConfig
from default_tags import EXCLUSION_TAGS_FILE, SENSITIVE_TAGS_FILE, VIOLENCE_TAGS_FILE


class TestScrapeUtil(unittest.TestCase):
    def test_scraper_get_posts(self):
        scraper = DanbooruScraper()

        posts = scraper.get_posts("1girl", page=1, limit_per_page=20)

        self.assertEqual(len(posts), 20)

    def test_get_posts(self):
        scraper = DanbooruScraper()

        exclude_tags = (
            utils.load_file_lines(SENSITIVE_TAGS_FILE)
            + utils.load_file_lines(VIOLENCE_TAGS_FILE)
            + utils.load_file_lines(EXCLUSION_TAGS_FILE)
        )

        posts = get_posts(
            scraper,
            "2girls",
            search_result_filter=None,
            fallback_search_result_filter=SearchResultFilterConfig(
                exclude_any=exclude_tags
            ),
            total_limit=1000,
        )

        self.assertEqual(len(posts), 1000)

        for post in posts:
            self.assertFalse(
                any(
                    tag in utils.load_file_lines(SENSITIVE_TAGS_FILE)
                    for tag in post.general_tags
                )
            )
            self.assertFalse(
                any(
                    tag in utils.load_file_lines(VIOLENCE_TAGS_FILE)
                    for tag in post.general_tags
                )
            )
            self.assertFalse(
                any(
                    tag in utils.load_file_lines(EXCLUSION_TAGS_FILE)
                    for tag in post.meta_tags
                )
            )


if __name__ == "__main__":
    unittest.main()
