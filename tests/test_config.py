import unittest
from urllib.parse import parse_qs, urlsplit
from carscraper.config import load_config, validate_config
from carscraper.scraping.urls import search_url


class ConfigTests(unittest.TestCase):
    def test_invalid_settings_fail_before_scraping(self):
        for config in (
            [],
            {"criteria": {}},
            {
                "criteria": {
                    "postcode": "LS1 2AD",
                    "price_from": 6500,
                    "price_to": 3000,
                },
                "cars": [{"make": "Toyota", "model": "Yaris"}],
            },
        ):
            with self.subTest(config=config), self.assertRaises(ValueError):
                validate_config(config)

    def test_config_and_encoded_url(self):
        config = load_config("search.example.json")
        query = parse_qs(
            urlsplit(search_url(config["cars"][0], config["criteria"])).query
        )
        self.assertEqual(query["postcode"], ["LS1 2AD"])
        self.assertEqual(query["price-to"], ["6500"])
