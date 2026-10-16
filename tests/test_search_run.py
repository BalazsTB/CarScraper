from contextlib import closing
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from carscraper.config import load_config
from carscraper.jobs.worker import run
from carscraper.paths import ROOT
from carscraper.storage.database import connect, initialize_database
from carscraper.storage.repository import save_search
from carscraper.storage.search_run import claim_search


class SearchRunTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / ".jobs" / ("test-" + uuid4().hex)
        self.directory.mkdir(parents=True)
        self.database = self.directory / "test.sqlite3"
        self.config = load_config(ROOT / "search.example.json")
        initialize_database(self.database)

    def tearDown(self):
        for file in self.directory.iterdir():
            file.unlink()
        self.directory.rmdir()

    def create_search(self, status="queued"):
        with closing(connect(self.database)) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO searches (started_at, completed_at, postcode, cars_json,
                    max_pages, delay_seconds, status, headless)
                VALUES ('', '', 'LS1 2AD', ?, 2, 1, ?, 1)
            """,
                (json.dumps(self.config["cars"]), status),
            )
            return cursor.lastrowid

    def read(self, search_id):
        with closing(connect(self.database)) as connection:
            return dict(
                connection.execute(
                    "SELECT * FROM searches WHERE id=?", (search_id,)
                ).fetchone()
            )

    def test_existing_search_gets_incremental_results_without_new_search(self):
        search_id = self.create_search()
        row = {
            "name": "Toyota Yaris",
            "link": "https://www.autotrader.co.uk/car-details/123",
        }

        def fake_scrape(config, **settings):
            self.assertEqual(config["criteria"]["postcode"], "LS1 2AD")
            self.assertEqual(settings["max_pages"], 2)
            self.assertTrue(settings["headless"])
            settings["on_page"]([row], "Page one")
            with closing(connect(self.database)) as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM search_results WHERE search_id=?",
                        (search_id,),
                    ).fetchone()[0],
                    1,
                )
            self.assertEqual(self.read(search_id)["status"], "running")
            return [row]

        with patch("carscraper.jobs.worker.scrape", side_effect=fake_scrape):
            run(search_id, self.database)
        self.assertEqual(self.read(search_id)["status"], "completed")
        with closing(connect(self.database)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM searches").fetchone()[0], 1
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM search_results").fetchone()[0],
                1,
            )

    def test_failure_preserves_partial_results_and_reports_error(self):
        search_id = self.create_search()

        def fake_scrape(config, **settings):
            settings["on_page"](
                [{"link": "https://www.autotrader.co.uk/car-details/123"}], "Page one"
            )
            raise RuntimeError("Browser failed")

        with patch("carscraper.jobs.worker.scrape", side_effect=fake_scrape):
            with self.assertRaisesRegex(RuntimeError, "Browser failed"):
                run(search_id, self.database)
        self.assertEqual(self.read(search_id)["status"], "failed")
        self.assertEqual(self.read(search_id)["error_message"], "Browser failed")
        with closing(connect(self.database)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM search_results").fetchone()[0],
                1,
            )

    def test_duplicate_worker_and_unscheduled_search_are_rejected(self):
        search_id = self.create_search()
        claim_search(self.database, search_id)
        with self.assertRaises(ValueError):
            claim_search(self.database, search_id)
        draft = self.create_search("draft")
        with patch("carscraper.jobs.worker.scrape") as scrape:
            with self.assertRaises(ValueError):
                run(draft, self.database)
            scrape.assert_not_called()

    def test_additive_migration_preserves_legacy_searches(self):
        legacy = self.directory / "legacy.sqlite3"
        search_id = save_search(
            self.config, [], legacy, "2026-10-16T12:00:00+00:00", 1, 5
        )
        initialize_database(legacy)
        initialize_database(legacy)
        with closing(connect(legacy)) as connection:
            search = connection.execute(
                "SELECT * FROM searches WHERE id=?", (search_id,)
            ).fetchone()
            self.assertEqual(search["status"], "completed")
            self.assertEqual(search["postcode"], self.config["criteria"]["postcode"])
