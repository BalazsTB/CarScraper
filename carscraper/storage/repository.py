"""Persist search snapshots and query search history."""

from contextlib import closing
import datetime as dt
import json
from pathlib import Path
import sqlite3

from carscraper.listings import COLUMNS
from carscraper.paths import DATABASE

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def save_search(config, rows, path, started_at, max_pages, delay):
    """Atomically append one successful search run and its listing snapshots."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        with connection:
            criteria = config["criteria"]
            cursor = connection.execute(
                """
                INSERT INTO searches (
                    started_at, completed_at, postcode, radius, year_from, year_to,
                    price_from, price_to, cars_json, max_pages, delay_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    started_at,
                    dt.datetime.now(dt.timezone.utc).isoformat(),
                    criteria["postcode"],
                    criteria.get("radius"),
                    criteria.get("year_from"),
                    criteria.get("year_to"),
                    criteria.get("price_from"),
                    criteria.get("price_to"),
                    json.dumps(config["cars"], ensure_ascii=False),
                    max_pages,
                    delay,
                ),
            )
            search_id = cursor.lastrowid
            connection.executemany(
                """
                INSERT INTO search_results (
                    search_id, name, link, price, year, mileage, miles_pa, owners,
                    distance, location, engine, transmission, fuel
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [(search_id, *(row.get(column) for column in COLUMNS)) for row in rows],
            )
        return search_id
    finally:
        connection.close()


def history(database=DATABASE):
    if not Path(database).exists():
        return []
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        if not connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name='searches'"
        ).fetchone():
            return []
        return [
            dict(row)
            for row in connection.execute("""
            SELECT s.*, (SELECT COUNT(*) FROM search_results r WHERE r.search_id=s.id) AS result_count
            FROM searches s ORDER BY s.id DESC
        """)
        ]


def results(search_id, database=DATABASE):
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        return [
            dict(row)
            for row in connection.execute(
                """
            SELECT name, link, price, year, mileage, miles_pa, owners, distance,
                   location, engine, transmission, fuel
            FROM search_results WHERE search_id = ?
            ORDER BY distance IS NULL, distance, id
        """,
                (search_id,),
            )
        ]
