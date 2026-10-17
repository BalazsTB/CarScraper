import unittest
from pathlib import Path
from unittest.mock import patch
from carscraper.cli import main


class CliTests(unittest.TestCase):
    def test_cli_saves_database(self):
        with (
            patch(
                "sys.argv", ["autotrader_scraper.py", "--config", "search.example.json"]
            ),
            patch("carscraper.cli.scrape", return_value=[]) as scrape_mock,
            patch("carscraper.cli.save_search", return_value=42) as save_mock,
        ):
            main()
        scrape_mock.assert_called_once()
        save_mock.assert_called_once()
        self.assertEqual(save_mock.call_args.args[2], Path("cars.sqlite3"))
