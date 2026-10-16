import unittest
import datetime as dt
from carscraper.scraping.parsing import has_next_page, parse_listings


class ParsingTests(unittest.TestCase):
    def test_complete_card_and_single_page(self):
        rows, soup = parse_listings(
            """
          <section data-testid="trader-seller-listing">
            <h2>Toyota Yaris</h2><a href="/car-details/12345?advertising=x">View</a>
            <p>£6,500</p><ul data-testid="search-listing-specs">
            <li>2014 (14 reg)</li><li>42,000 miles</li><li>1.3L</li>
            <li>Automatic</li><li>Petrol Hybrid</li><li>12 owners</li></ul>
            <p data-testid="search-listing-seller">Dealer location Leeds (2.5 miles)</p>
          </section>""",
            {"make": "Toyota", "model": "Yaris"},
        )
        row = rows[0]
        self.assertEqual(
            (row["price"], row["mileage"], row["owners"]), (6500, 42000, 12)
        )
        self.assertEqual((row["location"], row["distance"]), ("Leeds", 2.5))
        self.assertEqual(row["fuel"], "Petrol Hybrid")
        self.assertEqual(row["link"], "https://www.autotrader.co.uk/car-details/12345")
        self.assertFalse(has_next_page(soup))

    def test_missing_fields_and_current_year(self):
        rows, soup = parse_listings(
            f"""
          <article><a href="/car-details/123">View</a>
          <ul data-testid="search-listing-specs"><li>{dt.date.today().year}</li>
          <li>100 miles</li></ul></article>
          <a data-testid="pagination-next" href="?page=2">Next</a>""",
            {"make": "Honda", "model": "Jazz"},
        )
        self.assertIsNone(rows[0]["price"])
        self.assertIsNone(rows[0]["miles_pa"])
        self.assertTrue(has_next_page(soup))
