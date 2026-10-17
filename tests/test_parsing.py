import unittest
import datetime as dt
from pathlib import Path
from bs4 import BeautifulSoup
from carscraper.scraping.parsing import has_next_page, parse_listings


class ParsingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results_html = (Path(__file__).parent / "fixtures" / "autotrader_results.html").read_text(
            encoding="utf-8"
        )

    def test_supplied_results_page_prices_and_mileages(self):
        rows, _ = parse_listings(self.results_html, {"make": "Any", "model": "Any"})
        expected = {
            "202606273668027": (11146, 35692),
            "202610157020803": (1499, 98000),
            "202610136954133": (1750, 65000),
            "202610167037202": (1250, 82000),
            "202610157027324": (2490, 96000),
            "202609306541083": (499, 183400),
            "202609296488139": (460, 58000),
            "202606253629193": (500, 101000),
            "202610016571995": (2495, 66000),
            "202610116889556": (499, 178977),
            "202610167060484": (999, 169000),
            "202610167057054": (4877, 63869),
            "202606173378875": (9935, 34213),
            "202610167064655": (2500, 116747),
            "202610177083738": (1250, 157000),
            "202605162445348": (490, 125000),
            "202610167044173": (975, 35700),
            "202610167068380": (1400, 107000),
            "202610167048653": (4195, 51870),
            "202610086799756": (4999, 53000),
            "202608145110592": (800, 143000),
            "202610126923404": (2500, 59500),
            "202609286451928": (1550, 89000),
            "202610177079422": (590, 122000),
        }
        self.assertEqual(len(rows), 24)  # 26 cards, including two repeated adverts.
        self.assertEqual(
            {row["link"].rsplit("/", 1)[1]: (row["price"], row["mileage"]) for row in rows},
            expected,
        )
        citroen = next(row for row in rows if row["name"] == "Citroen C1")
        self.assertEqual(citroen["year"], 2010)  # Not the 2027 MOT in the advert copy.
        self.assertEqual((citroen["location"], citroen["distance"]), ("Stockton On Tees", 3))
        self.assertEqual(citroen["miles_pa"], round(98000 / (dt.date.today().year - 2010)))
        golf = next(row for row in rows if row["name"] == "Volkswagen Golf")
        self.assertEqual((golf["location"], golf["distance"]), ("Stockton On Tees", 1))

    def test_missing_mileage_does_not_use_distance_or_advert_copy(self):
        soup = BeautifulSoup(self.results_html, "html.parser")
        card = soup.select_one('[data-advertid="202610157020803"]')
        card.select_one('[data-testid="mileage"]').decompose()
        card.select_one('[data-testid="search-listing-attention-grabber"]').string = "Service every 10,000 miles"
        rows, _ = parse_listings(str(card), {"make": "Citroen", "model": "C1"})
        self.assertIsNone(rows[0]["mileage"])
        self.assertIsNone(rows[0]["miles_pa"])
        self.assertEqual(rows[0]["distance"], 3)

    def test_visible_price_takes_precedence_over_hidden_title_and_tax(self):
        soup = BeautifulSoup(self.results_html, "html.parser")
        card = soup.select_one('[data-advertid="202610086799756"]')
        card.select_one('[class*="visuallyhidden"]').string = "Old price £9,999"
        rows, _ = parse_listings(str(card), {"make": "Skoda", "model": "Fabia"})
        self.assertEqual(rows[0]["name"], "Skoda Fabia")
        self.assertEqual(rows[0]["price"], 4999)  # Not the £20 tax in the advert copy.

    def test_modern_inner_card_and_invalid_advert_links(self):
        soup = BeautifulSoup(self.results_html, "html.parser")
        card = soup.select_one('[data-testid="advertCard-1"]')
        rows, _ = parse_listings(str(card), {"make": "Any", "model": "Any"})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["price"], 1499)
        for href in ("https://example.com/car-details/123", "/car-details/invalid"):
            with self.subTest(href=href):
                card.select_one('[data-testid="search-listing-title"]')["href"] = href
                rows, _ = parse_listings(str(card), {"make": "Any", "model": "Any"})
                self.assertEqual(rows, [])

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
