import unittest
from unittest.mock import Mock, call, patch
from urllib.parse import parse_qs, urlsplit

from carscraper.scraping.browser import scrape


def listing(advert_id):
    return f'<article><h2>Test car</h2><a href="/car-details/{advert_id}">View</a></article>'


class BrowserTests(unittest.TestCase):
    def run_scrape(self, cars, pages, max_pages):
        driver = Mock()
        events = []

        def navigate(url):
            query = parse_qs(urlsplit(url).query)
            make, model, page = query["make"][0], query["model"][0], int(query["page"][0])
            self.assertEqual(query["postcode"], ["LS1 2AD"])
            events.append(("navigate", make, model, page))
            driver.page_source = pages[(make, model, page)]

        def save_page(rows, message):
            events.append(("parsed", [row["link"].rsplit("/", 1)[1] for row in rows]))

        driver.get.side_effect = navigate
        with (
            patch("selenium.webdriver.Chrome") as chrome,
            patch("carscraper.scraping.browser.time.sleep") as sleep,
        ):
            chrome.return_value.__enter__.return_value = driver
            rows = scrape(
                {"criteria": {"postcode": "LS1 2AD"}, "cars": cars},
                max_pages=max_pages,
                delay=2,
                on_page=save_page,
            )
            chrome.assert_called_once()
            chrome.return_value.__exit__.assert_called_once()
        return rows, events, sleep.call_args_list

    def test_visits_every_requested_page_and_parses_before_next_navigation(self):
        rows, events, sleeps = self.run_scrape(
            [{"make": "Toyota", "model": "Yaris"}],
            {
                ("Toyota", "Yaris", 1): listing(123),
                ("Toyota", "Yaris", 2): listing(123),
                ("Toyota", "Yaris", 3): "<p>No cars found</p>",
                ("Toyota", "Yaris", 4): listing(456),
            },
            max_pages=4,
        )
        # None of the pages has a Next link. Duplicates and empty pages still count.
        self.assertEqual(events, [
            ("navigate", "Toyota", "Yaris", 1), ("parsed", ["123"]),
            ("navigate", "Toyota", "Yaris", 2), ("parsed", ["123"]),
            ("navigate", "Toyota", "Yaris", 3), ("parsed", []),
            ("navigate", "Toyota", "Yaris", 4), ("parsed", ["456"]),
        ])
        self.assertEqual([row["link"].rsplit("/", 1)[1] for row in rows], ["123", "456"])
        self.assertEqual(sleeps, [call(2)] * 3)

    def test_page_count_applies_to_each_make_model(self):
        cars = [{"make": "Toyota", "model": "Yaris"}, {"make": "Honda", "model": "Jazz"}]
        for count in (1, 2):
            with self.subTest(count=count):
                pages = {
                    (car["make"], car["model"], page): listing(100 * index + page)
                    for index, car in enumerate(cars, 1)
                    for page in range(1, count + 1)
                }
                rows, events, sleeps = self.run_scrape(cars, pages, count)
                self.assertEqual(
                    [event[1:] for event in events if event[0] == "navigate"],
                    list(pages),
                )
                self.assertEqual(len(rows), count * len(cars))
                self.assertEqual(sleeps, [call(2)] * (count * len(cars) - 1))
