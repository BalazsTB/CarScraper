"""Command-line argument handling and output orchestration."""

import argparse
import datetime as dt
import logging
from pathlib import Path
import sqlite3

from carscraper.config import load_config
from carscraper.exports.excel import export_excel
from carscraper.scraping.browser import scrape
from carscraper.scraping.urls import search_url
from carscraper.storage.repository import save_search

LOG = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Save AutoTrader UK searches to SQLite and Excel."
    )
    parser.add_argument("--config", type=Path, default=Path("search.json"))
    parser.add_argument("--output", type=Path, default=Path("cars.xlsx"))
    parser.add_argument("--database", type=Path, default=Path("cars.sqlite3"))
    parser.add_argument(
        "--max-pages", type=int, default=10, help="Maximum pages per make/model"
    )
    parser.add_argument(
        "--delay", type=float, default=5, help="Seconds between requests (minimum 1)"
    )
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and print URLs without opening Chrome",
    )
    args = parser.parse_args()
    if args.max_pages < 1 or not 1 <= args.delay <= 3600:
        parser.error(
            "max-pages must be positive and delay must be between 1 and 3600 seconds"
        )
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        config = load_config(args.config)
        if args.dry_run:
            for car in config["cars"]:
                print(search_url(car, config["criteria"]))
            return
        started_at = dt.datetime.now(dt.timezone.utc).isoformat()
        rows = scrape(config, args.max_pages, args.delay, args.headless)
        search_id = save_search(
            config, rows, args.database, started_at, args.max_pages, args.delay
        )
        LOG.info(
            "Saved search %s with %s listings to %s",
            search_id,
            len(rows),
            args.database,
        )
        export_excel(rows, args.output)
        LOG.info("Saved %s unique listings to %s", len(rows), args.output)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        parser.exit(1, f"Error: {exc}\n")
