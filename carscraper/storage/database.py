"""Shared schema initialization and additive database migration."""

from contextlib import closing
from pathlib import Path
import re
import sqlite3

SCHEMA_DIRECTORY = Path(__file__).resolve().parent


def connect(path):
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            (SCHEMA_DIRECTORY / "schema.sql").read_text(encoding="utf-8")
            + "\n"
            + (SCHEMA_DIRECTORY / "car_brands.sql").read_text(encoding="utf-8")
        )
        with connection:
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(searches)")
            }
            migration = (SCHEMA_DIRECTORY / "search_lifecycle.sql").read_text(
                encoding="utf-8"
            )
            for statement in migration.split(";"):
                match = re.search(r"ADD COLUMN (\w+)", statement)
                if match and match.group(1) not in columns:
                    connection.execute(statement)
