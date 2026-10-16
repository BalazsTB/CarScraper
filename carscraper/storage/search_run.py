"""Claim saved searches and persist incremental results and run status."""

from contextlib import closing
import datetime as dt
import json

from carscraper.config import validate_config
from carscraper.listings import COLUMNS
from carscraper.storage.database import connect


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def claim_search(path, search_id):
    with closing(connect(path)) as connection, connection:
        updated = connection.execute(
            """
            UPDATE searches SET status='running', started_at=?, completed_at='',
                error_message=NULL, progress_message='Starting Chrome'
            WHERE id=? AND status='queued'
        """,
            (now(), search_id),
        )
        if updated.rowcount != 1:
            raise ValueError(f"Search {search_id} is missing or is not queued")
        connection.execute("DELETE FROM search_results WHERE search_id=?", (search_id,))
        return dict(
            connection.execute(
                "SELECT * FROM searches WHERE id=?", (search_id,)
            ).fetchone()
        )


def search_config(search):
    fields = ("postcode", "radius", "year_from", "year_to", "price_from", "price_to")
    return validate_config(
        {
            "criteria": {
                field: search[field] for field in fields if search[field] is not None
            },
            "cars": json.loads(search["cars_json"]),
        }
    )


def save_page(path, search_id, rows, message):
    with closing(connect(path)) as connection, connection:
        connection.executemany(
            """
            INSERT INTO search_results (
                search_id, name, link, price, year, mileage, miles_pa, owners,
                distance, location, engine, transmission, fuel
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(search_id, link) DO NOTHING
        """,
            [(search_id, *(row.get(column) for column in COLUMNS)) for row in rows],
        )
        connection.execute(
            "UPDATE searches SET progress_message=? WHERE id=? AND status='running'",
            (message, search_id),
        )


def finish_search(path, search_id, error=None):
    with closing(connect(path)) as connection, connection:
        connection.execute(
            """
            UPDATE searches SET status=?, completed_at=?, error_message=?, progress_message=?
            WHERE id=? AND status='running'
        """,
            (
                "failed" if error else "completed",
                now(),
                error,
                "Search failed; any collected results are partial"
                if error
                else "Search complete",
                search_id,
            ),
        )
