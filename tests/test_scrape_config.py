import unittest

import sys

sys.path.append("..")

from scrape_config import (
    load_scrape_config_yaml,
    load_scrape_config_toml,
    load_scrape_config_json,
    load_scrape_config,
)


class TestScrapeUtil(unittest.TestCase):
    def test_load_yaml_config(self):
        load_scrape_config_yaml("./tests/config/test.yaml")

    def test_load_toml_config(self):
        load_scrape_config_toml("./tests/config/test.toml")

    def test_load_json_config(self):
        load_scrape_config_json("./tests/config/test.json")

    def test_load_config(self):
        load_scrape_config("./tests/config/test.yaml")
        load_scrape_config("./tests/config/test.toml")
        load_scrape_config("./tests/config/test.json")

    def test_load_simple_config(self):
        load_scrape_config("./tests/config/simple.yaml")


if __name__ == "__main__":
    unittest.main()
