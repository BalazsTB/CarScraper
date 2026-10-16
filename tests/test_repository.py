import unittest
from contextlib import closing
from pathlib import Path
import sqlite3
from carscraper.config import load_config
from carscraper.scraping.parsing import parse_listings
from carscraper.storage.repository import save_search


class RepositoryTests(unittest.TestCase):
    def test_database_history_relationships_and_rollback(self):
        path = Path("test-searches.sqlite3")
        config = load_config("search.example.json")
        rows, _ = parse_listings(
            """<article><h2>Driver's car</h2>
            <a href="/car-details/123">View</a></article>""",
            config["cars"][0],
        )
        try:
            first = save_search(config, rows, path, "2026-10-16T10:00:00+00:00", 1, 5)
            second = save_search(config, rows, path, "2026-10-16T11:00:00+00:00", 2, 5)
            empty = save_search(config, [], path, "2026-10-16T12:00:00+00:00", 1, 5)
            self.assertEqual(len({first, second, empty}), 3)
            with self.assertRaises(sqlite3.IntegrityError):
                save_search(config, rows + rows, path, "invalid run", 1, 5)
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.execute("PRAGMA foreign_keys = ON")
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM searches").fetchone()[0], 3
                )
                results = connection.execute("""SELECT s.id, r.name, r.price FROM searches s
                    JOIN search_results r ON r.search_id = s.id ORDER BY s.id""").fetchall()
                self.assertEqual(
                    results,
                    [(first, "Driver's car", None), (second, "Driver's car", None)],
                )
                saved = connection.execute(
                    "SELECT postcode, cars_json, max_pages FROM searches WHERE id = ?",
                    (second,),
                ).fetchone()
                self.assertEqual(saved[0], config["criteria"]["postcode"])
                self.assertIn("Toyota", saved[1])
                self.assertEqual(saved[2], 2)
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO search_results (search_id, link) VALUES (?, ?)",
                        (-1, "invalid"),
                    )
                connection.execute("DELETE FROM searches WHERE id = ?", (first,))
                self.assertEqual(
                    connection.execute(
                        "SELECT search_id FROM search_results"
                    ).fetchall(),
                    [(second,)],
                )
        finally:
            path.unlink(missing_ok=True)
