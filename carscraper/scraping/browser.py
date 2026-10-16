"""Browser lifecycle, page waits and search traversal."""

import datetime as dt
import logging
from pathlib import Path
import time

from carscraper.scraping.parsing import has_next_page, parse_listings
from carscraper.scraping.urls import search_url

LOG = logging.getLogger(__name__)


def scrape(
    config, max_pages=10, delay=5, headless=False, debug_dir=Path("debug"), on_page=None
):
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait

    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    rows, seen = [], set()
    with webdriver.Chrome(options=options) as driver:
        driver.set_page_load_timeout(60)
        for car in config["cars"]:
            for page in range(1, max_pages + 1):
                LOG.info("Searching %s %s, page %s", car["make"], car["model"], page)
                driver.get(search_url(car, config["criteria"], page))

                def ready(browser):
                    parsed, soup = parse_listings(browser.page_source, car)
                    text = soup.get_text(" ", strip=True).lower()
                    return bool(
                        parsed
                        or any(
                            message in text
                            for message in (
                                "no cars found",
                                "no results found",
                                "we couldn't find any cars",
                                "sorry, we couldn't find any results",
                            )
                        )
                    )

                try:
                    WebDriverWait(driver, 30).until(ready)
                except TimeoutException as exc:
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                    destination = debug_dir / f"unrecognised-page-{stamp}.html"
                    destination.write_text(driver.page_source, encoding="utf-8")
                    raise RuntimeError(
                        f"Results were not recognised. Inspect {destination}; the page may "
                        "show a consent dialog, access challenge, or changed markup."
                    ) from exc
                parsed, soup = parse_listings(driver.page_source, car)
                added = 0
                for row in parsed:
                    if row["link"] not in seen:
                        rows.append(row)
                        seen.add(row["link"])
                        added += 1
                LOG.info("Found %s listings (%s new)", len(parsed), added)
                if on_page is not None:
                    on_page(
                        parsed,
                        f"{car['make']} {car['model']}, page {page}: {len(parsed)} listings",
                    )
                if not has_next_page(soup) or not added:
                    break
                if page == max_pages:
                    LOG.warning(
                        "Page limit reached for %s %s; results may be incomplete",
                        car["make"],
                        car["model"],
                    )
                time.sleep(delay)
            time.sleep(delay)
    return rows
