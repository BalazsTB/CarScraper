"""Optional real-browser smoke check. Requires a built Blazor app and Chrome."""

import os
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import textwrap
import time
import urllib.request

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as expected

ROOT = Path(__file__).resolve().parents[1]


def main():
    jobs = ROOT / ".jobs"
    jobs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="blazor-smoke-", dir=jobs) as temporary:
        database = Path(temporary) / "test.sqlite3"
        # Only the test server's child Python worker sees this synthetic scraper.
        # Fail closed if installing the test double fails; never contact AutoTrader.
        (Path(temporary) / "sitecustomize.py").write_text(textwrap.dedent('''
            import os
            try:
                import time
                from carscraper.scraping import browser
                def fake_scrape(config, **settings):
                    time.sleep(3)
                    rows = [{"name": "Test Yaris", "link": "https://www.autotrader.co.uk/car-details/123",
                             "price": 8000, "year": 2018, "mileage": 42000, "distance": 3,
                             "location": "Leeds", "fuel": "Petrol", "transmission": "Manual"}]
                    settings["on_page"](rows, "Page 1 collected")
                    time.sleep(5)
                    return rows
                browser.scrape = fake_scrape
            except BaseException:
                os._exit(1)
        '''), encoding="utf-8")
        environment = dict(
            os.environ,
            Scraper__RepositoryRoot=str(ROOT),
            Scraper__DatabasePath=str(database),
            ASPNETCORE_ENVIRONMENT="Development",
            PYTHONPATH=os.pathsep.join((temporary, str(ROOT))),
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
                wait = WebDriverWait(browser, 30, ignored_exceptions=(StaleElementReferenceException,))
                wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, ".landing-card")) == 2)
                assert len(browser.find_elements(By.CSS_SELECTOR, ".sidebar nav a")) == 2
                assert not browser.find_elements(By.CSS_SELECTOR, "form")
                browser.save_screenshot(str(jobs / "workflow-home.png"))
                wait.until(lambda driver: driver.find_element(By.CSS_SELECTOR, '.landing-card[href="/search/new"]').click() or True)
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
                assert all(
                    field.get_attribute("value") == ""
                    for field in browser.find_elements(By.CSS_SELECTOR, "form input:not([type=checkbox]):not([type=hidden])")
                )
                browser.save_screenshot(str(jobs / "workflow-form.png"))
                make = browser.find_element(By.CSS_SELECTOR, "input[role=combobox]")
                make.click()
                wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, ".brand-options [role=option]")) == 151)
                brands = [option.text for option in browser.find_elements(By.CSS_SELECTOR, ".brand-options [role=option]")]
                assert len(brands) == 151
                assert brands == sorted(brands, key=str.casefold)
                make.send_keys("toyo")
                wait.until(lambda driver: [option.text for option in driver.find_elements(By.CSS_SELECTOR, ".brand-options [role=option]")] == ["Toyota"])
                make.send_keys(Keys.ARROW_DOWN)
                wait.until(lambda driver: driver.find_elements(By.CSS_SELECTOR, '.brand-options [aria-selected="true"]'))
                make.send_keys(Keys.ENTER)
                wait.until(lambda driver: make.get_attribute("value") == "Toyota" and make.get_attribute("aria-expanded") == "false")
                # Added rows have their own blank query and support mouse selection.
                browser.find_element(By.XPATH, "//button[contains(., 'Add a car')]").click()
                wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "input[role=combobox]")) == 2)
                second_make = browser.find_elements(By.CSS_SELECTOR, "input[role=combobox]")[1]
                assert second_make.get_attribute("value") == ""
                second_make.send_keys("RO")
                expected_brands = [brand for brand in brands if "ro" in brand.lower()]
                wait.until(lambda driver: [option.text for option in driver.find_elements(By.CSS_SELECTOR, ".brand-options [role=option]")] == expected_brands)
                browser.find_element(By.XPATH, "//*[@role='option' and text()='Rolls-Royce']").click()
                wait.until(lambda driver: second_make.get_attribute("value") == "Rolls-Royce")
                assert make.get_attribute("value") == "Toyota"
                browser.find_elements(By.CSS_SELECTOR, "button[aria-label='Remove car']")[1].click()
                for label, value in (
                    ("Postcode", "LS1 2AD"), ("Model", "Yaris"),
                    ("Pages per make/model", "1"), ("Delay between pages (seconds)", "1"),
                ):
                    browser.find_element(By.XPATH, f"//label[starts-with(normalize-space(.), '{label}')]/input").send_keys(value)
                any_age.click()
                wait.until(
                    lambda driver: (
                        not driver.find_elements(
                            By.XPATH, "//label[contains(., 'Earliest year')]/input"
                        )
                    )
                )
                browser.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
                wait.until(lambda driver: driver.current_url.endswith("/searches/1") and driver.find_elements(By.CSS_SELECTOR, ".loading-panel"))
                assert not browser.find_elements(By.CSS_SELECTOR, "table")
                browser.save_screenshot(str(jobs / "workflow-loading.png"))
                wait.until(lambda driver: driver.find_elements(By.CSS_SELECTOR, "table tbody tr"))
                assert "Test Yaris" in browser.find_element(By.TAG_NAME, "body").text
                assert not browser.find_elements(By.CSS_SELECTOR, ".loading-panel")
                browser.save_screenshot(str(jobs / "workflow-results.png"))
                with closing(sqlite3.connect(database)) as connection, connection:
                    search = connection.execute(
                        "SELECT id,status FROM searches"
                    ).fetchall()
                    assert search == [(1, "completed")], search
                    assert connection.execute(
                        "SELECT year_from,year_to FROM searches WHERE id=1"
                    ).fetchone() == (None, None)
                browser.find_element(By.CSS_SELECTOR, '.sidebar a[href="/searches"]').click()
                wait.until(lambda driver: driver.find_elements(By.CSS_SELECTOR, ".history-item"))
                assert len(browser.find_elements(By.CSS_SELECTOR, ".history-item")) == 1
                assert "Toyota Yaris" in browser.find_element(By.CSS_SELECTOR, ".history-item").text
                assert browser.find_element(By.CSS_SELECTOR, ".result-count strong").text == "1"
                assert not browser.find_elements(By.CSS_SELECTOR, "select")
                browser.save_screenshot(str(jobs / "workflow-history.png"))
                browser.find_element(By.CSS_SELECTOR, ".history-row .danger").click()
                confirmation = wait.until(expected.alert_is_present())
                assert "search #1" in confirmation.text
                confirmation.dismiss()
                with closing(sqlite3.connect(database)) as connection:
                    assert connection.execute("SELECT COUNT(*) FROM searches").fetchone()[0] == 1
                    assert connection.execute("SELECT COUNT(*) FROM search_results").fetchone()[0] == 1
                browser.find_element(By.CSS_SELECTOR, ".history-item").click()
                wait.until(lambda driver: driver.find_elements(By.CSS_SELECTOR, "table tbody tr"))
                assert browser.current_url.endswith("/searches/1")
                browser.refresh()
                wait.until(lambda driver: driver.find_elements(By.CSS_SELECTOR, "table tbody tr"))
                wait.until(expected.element_to_be_clickable((By.XPATH, "//button[text()='Search again']")))
                with closing(sqlite3.connect(database)) as connection, connection:
                    connection.execute("UPDATE searches SET cars_json='[]' WHERE id=1")
                wait.until(lambda driver: driver.find_element(By.XPATH, "//button[text()='Search again']").click() or True)
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
                assert browser.find_element(By.XPATH, "//button[text()='Retry search']").is_enabled()
                # Keep a second saved search to verify that deleting one leaves others intact.
                with closing(sqlite3.connect(database)) as connection, connection:
                    connection.execute("""INSERT INTO searches
                        (started_at, completed_at, postcode, cars_json, max_pages, delay_seconds, status)
                        VALUES ('', '', 'LS1 2AD', '[{"make":"Honda","model":"Jazz"}]', 1, 1, 'completed')""")
                    connection.execute("INSERT INTO search_results (search_id, name, link) VALUES (2, 'Test Jazz', 'https://www.autotrader.co.uk/car-details/456')")
                browser.find_element(By.CSS_SELECTOR, ".search-actions .danger").click()
                wait.until(expected.alert_is_present()).accept()
                wait.until(lambda driver: driver.current_url.endswith("/searches") and driver.find_elements(By.CSS_SELECTOR, ".history-item"))
                assert len(browser.find_elements(By.CSS_SELECTOR, ".history-item")) == 1
                assert "Honda Jazz" in browser.find_element(By.CSS_SELECTOR, ".history-item").text
                with closing(sqlite3.connect(database)) as connection:
                    assert connection.execute("SELECT id FROM searches").fetchall() == [(2,)]
                    assert connection.execute("SELECT search_id FROM search_results").fetchall() == [(2,)]
                browser.find_element(By.CSS_SELECTOR, ".history-row .danger").click()
                wait.until(expected.alert_is_present()).accept()
                wait.until(lambda driver: "No searches yet" in driver.find_element(By.TAG_NAME, "body").text)
                with closing(sqlite3.connect(database)) as connection:
                    assert connection.execute("SELECT COUNT(*) FROM searches").fetchone()[0] == 0
                    assert connection.execute("SELECT COUNT(*) FROM search_results").fetchone()[0] == 0
                assert (
                    browser.find_element(By.ID, "blazor-error-ui").is_displayed()
                    is False
                )
                browser.find_element(By.CSS_SELECTOR, '.sidebar a[href="/search/new"]').click()
                wait.until(expected.element_to_be_clickable((By.CSS_SELECTOR, "button[type=submit]")))
                assert all(
                    field.get_attribute("value") == ""
                    for field in browser.find_elements(By.CSS_SELECTOR, "form input:not([type=checkbox]):not([type=hidden])")
                )
                browser.refresh()
                wait.until(expected.element_to_be_clickable((By.CSS_SELECTOR, "button[type=submit]")))
                assert all(field.get_attribute("value") == "" for field in browser.find_elements(By.CSS_SELECTOR, "form input:not([type=checkbox]):not([type=hidden])"))
                browser.set_window_size(390, 844)
                browser.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
                browser.save_screenshot(str(jobs / "workflow-mobile.png"))
                assert browser.execute_script("return document.documentElement.scrollWidth <= window.innerWidth")
                print(
                    "Blazor browser check passed: search workflow, brand selection, history, retry failure, deletion confirmation/cancel from both views, and mobile layout. No live scraping."
                )
        finally:
            server.terminate()
            server.wait(timeout=15)


if __name__ == "__main__":
    main()
