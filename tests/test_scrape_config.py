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
        load_scrape_config_yaml("./example/test.yaml")

    def test_load_toml_config(self):
        load_scrape_config_toml("./example/test.toml")

    def test_load_json_config(self):
        load_scrape_config_json("./example/test.json")

    def test_load_config(self):
        load_scrape_config("./example/test.yaml")
        load_scrape_config("./example/test.toml")
        load_scrape_config("./example/test.json")

    def test_load_simple_config(self):
        load_scrape_config("./example/simple.yaml")


if __name__ == "__main__":
    unittest.main()
