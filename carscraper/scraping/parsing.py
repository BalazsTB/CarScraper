"""Extract listing fields and pagination from result HTML."""

import datetime as dt
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from carscraper.listings import COLUMNS
from carscraper.scraping.urls import BASE

CARD_SELECTOR = (
    'li[data-advertid], [data-testid^="advertCard-"], '
    '[data-testid="trader-seller-listing"], [data-testid="private-seller-listing"]'
)


def number(pattern, text, integer=True):
    match = re.search(pattern, text, re.I)
    if not match:
        return None
    value = match.group(1).replace(",", "")
    return int(value) if integer else float(value)


def parse_listings(html, car):
    soup = BeautifulSoup(html, "html.parser")
    # Accessibility copies repeat prices inside titles; SVG titles are icon labels.
    # Neither should be treated as listing data.
    for element in soup.select(
        'svg, script, style, [hidden], [class*="visuallyhidden"], '
        '[class*="visually-hidden"], .sr-only'
    ):
        element.decompose()
    cards = soup.select(CARD_SELECTOR)
    # The advert URL also identifies cards when test IDs change.
    if not cards:
        cards = soup.select("article")
    rows, seen = [], set()
    for card in cards:
        heading = card.select_one('[data-testid="search-listing-title"]')
        link = card.select_one('a[data-testid="search-listing-title"][href]')
        if link is None:
            link = card.select_one('a[href*="/car-details/"]')
        if link is None:
            continue
        absolute = urljoin(BASE, link["href"])
        parts = urlsplit(absolute)
        if parts.netloc != "www.autotrader.co.uk" or not re.fullmatch(
            r"/car-details/\d+/?", parts.path
        ):
            continue
        canonical_link = BASE + parts.path.rstrip("/")
        if canonical_link in seen:
            continue
        seen.add(canonical_link)
        text = card.get_text(" ", strip=True)
        if heading is None:
            heading = card.select_one("h2, h3")
        seller = card.select_one('[data-testid="search-listing-location"]')
        if seller is None:
            seller = card.select_one('[data-testid="search-listing-seller"]')
        seller_text = seller.get_text(" ", strip=True) if seller else ""
        location = re.sub(r"\s*\([\d,.]+\s*miles?\).*", "", seller_text, flags=re.I)
        location = re.sub(r"^.*?Dealer location\s*", "", location).strip()
        specs = card.select_one('[data-testid="search-listing-specs"]')
        registered_year = card.select_one('[data-testid="registered_year"]')
        year = number(
            r"\b((?:19|20)\d{2})\b", registered_year.get_text(" ")
        ) if registered_year else None
        if year is None:
            year = number(r"\b((?:19|20)\d{2})\s*\(\d{2}\s*reg\)", text)
        if year is None and specs:
            year = number(r"\b((?:19|20)\d{2})\b", specs.get_text(" "))
        mileage_badge = card.select_one('[data-testid="mileage"]')
        mileage_text = mileage_badge.get_text(" ") if mileage_badge else (
            specs.get_text(" ") if specs else ""
        )
        # Legacy cards can lack a specs wrapper. Never use dealer distance as mileage.
        if not mileage_text and not card.select_one('[data-testid="search-listing-title"]'):
            mileage_text = re.sub(r"\([\d,.]+\s*miles?\)", "", text, flags=re.I)
        mileage = number(r"\b([\d,]+)\s*miles\b", mileage_text)
        # The current price has no stable test ID. Match an entire amount element,
        # so advert copy such as "£20 TAX" cannot replace the asking price.
        price = None
        for amount in card.select("span, p"):
            amount_text = amount.get_text(" ", strip=True)
            if re.fullmatch(r"£\s*[\d,]+", amount_text):
                price = number(r"£\s*([\d,]+)", amount_text)
                break
        age = dt.date.today().year - year if year else None
        row = dict.fromkeys(COLUMNS)
        row.update(
            name=heading.get_text(" ", strip=True)
            if heading
            else f"{car['make']} {car['model']}",
            link=canonical_link,
            price=price,
            year=year,
            mileage=mileage,
            miles_pa=round(mileage / age)
            if mileage is not None and age and age > 0
            else None,
            owners=number(r"(\d+)\s*(?:previous\s+)?owners?\b", text),
            distance=number(r"\(([\d,.]+)\s*miles?\)", seller_text, False),
            location=location or None,
        )
        for field, pattern in {
            "engine": r"\b\d+(?:\.\d+)?\s*L\b",
            "transmission": r"\b(?:Manual|Automatic)\b",
            "fuel": r"\b(?:Petrol Plug-in Hybrid|Diesel Plug-in Hybrid|Petrol Hybrid|Diesel Hybrid|Petrol|Diesel|Electric|Hybrid)\b",
        }.items():
            match = re.search(pattern, text, re.I)
            row[field] = match.group(0) if match else None
        rows.append(row)
    return rows, soup


def has_next_page(soup):
    link = soup.select_one('[data-testid="pagination-next"], a[rel="next"]')
    return bool(
        link
        and link.get("href")
        and link.get("aria-disabled") != "true"
        and not link.has_attr("disabled")
    )
