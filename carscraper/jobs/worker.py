"""Run a queued search by its SQLite primary key."""

import argparse
import logging
from pathlib import Path
from carscraper.paths import DATABASE, ROOT
from carscraper.scraping.browser import scrape
from carscraper.storage.database import initialize_database
from carscraper.storage.search_run import (
    claim_search,
    finish_search,
    save_page,
    search_config,
)


def run(search_id, database=DATABASE):
    initialize_database(database)
    search = claim_search(database, search_id)
    try:
        config = search_config(search)
        if (
            not 1 <= search["max_pages"] <= 100
            or not 1 <= search["delay_seconds"] <= 3600
        ):
            raise ValueError("Invalid saved page limit or request delay")
        rows = scrape(
            config,
            max_pages=search["max_pages"],
            delay=search["delay_seconds"],
            headless=bool(search["headless"]),
            debug_dir=ROOT / "debug",
            on_page=lambda rows, message: save_page(database, search_id, rows, message),
        )
        save_page(database, search_id, rows, "Finishing search")
        finish_search(database, search_id)
    except Exception as exc:
        finish_search(database, search_id, str(exc))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search-id", required=True, type=int)
    parser.add_argument("--database", type=Path, default=DATABASE)
    args = parser.parse_args()
    if args.search_id < 1:
        parser.error("search-id must be positive")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run(args.search_id, args.database)


if __name__ == "__main__":
    main()
