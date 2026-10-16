"""Optional real-browser smoke check. Requires a built Blazor app and Chrome."""

import os
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import urllib.request

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as expected

ROOT = Path(__file__).resolve().parents[1]


def main():
    jobs = ROOT / ".jobs"
    jobs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="blazor-smoke-", dir=jobs) as temporary:
        database = Path(temporary) / "test.sqlite3"
        environment = dict(
            os.environ,
            Scraper__RepositoryRoot=str(ROOT),
            Scraper__DatabasePath=str(database),
            ASPNETCORE_ENVIRONMENT="Development",
        )
        project = ROOT / "frontend" / "CarScraper.Web"
        log_path = Path(temporary) / "server.log"
        with log_path.open("w", encoding="utf-8") as log:
            server = subprocess.Popen(
                [
                    "dotnet",
                    str(project / "bin/Debug/net10.0/CarScraper.Web.dll"),
                    "--contentRoot",
                    str(project),
                    "--urls",
                    "http://localhost:5248",
                ],
                cwd=ROOT,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        try:
            for attempt in range(60):
                try:
                    with urllib.request.urlopen(
                        "http://localhost:5248", timeout=1
                    ) as response:
                        assert response.status == 200
                    break
                except OSError:
                    if server.poll() is not None:
                        raise RuntimeError(log_path.read_text())
                    time.sleep(0.5)
            else:
                raise RuntimeError("Blazor server did not start")
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1600,1100")
            with webdriver.Chrome(options=options) as browser:
                browser.get("http://localhost:5248")
                wait = WebDriverWait(browser, 30)
                wait.until(
                    lambda driver: driver.find_elements(By.CSS_SELECTOR, "form input")
                )
                # The form enables saving only after its interactive circuit connects.
                wait.until(
                    expected.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button[type=submit]")
                    )
                )
                any_age = browser.find_element(
                    By.XPATH, "//label[contains(., 'Any age')]/input"
                )
                any_age.click()
                wait.until(
                    lambda driver: (
                        not driver.find_elements(
                            By.XPATH, "//label[contains(., 'Earliest year')]/input"
                        )
                    )
                )
                browser.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
                wait.until(
                    lambda driver: (
                        "Search #1 saved"
                        in driver.find_element(By.TAG_NAME, "body").text
                    )
                )
                with closing(sqlite3.connect(database)) as connection, connection:
                    search = connection.execute(
                        "SELECT id,status FROM searches"
                    ).fetchall()
                    assert search == [(1, "draft")], search
                    assert connection.execute(
                        "SELECT year_from,year_to FROM searches WHERE id=1"
                    ).fetchone() == (None, None)
                    # Fail validation before Selenium opens AutoTrader in the worker.
                    connection.execute("UPDATE searches SET cars_json='[]' WHERE id=1")
                start = next(
                    button
                    for button in browser.find_elements(By.TAG_NAME, "button")
                    if button.text == "Search"
                )
                start.click()
                wait.until(
                    lambda driver: (
                        "at least one make/model pair"
                        in driver.find_element(By.TAG_NAME, "body").text
                    )
                )
                with closing(sqlite3.connect(database)) as connection, connection:
                    assert connection.execute(
                        "SELECT id,status FROM searches"
                    ).fetchall() == [(1, "failed")]
                    assert (
                        connection.execute(
                            "SELECT COUNT(*) FROM search_results"
                        ).fetchone()[0]
                        == 0
                    )
                assert (
                    browser.find_element(By.ID, "blazor-error-ui").is_displayed()
                    is False
                )
                print(
                    "Blazor browser check passed: save draft, start saved ID, poll failure without live scraping."
                )
        finally:
            server.terminate()
            server.wait(timeout=15)


if __name__ == "__main__":
    main()
