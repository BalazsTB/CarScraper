"""Extract listing fields and pagination from result HTML."""

import datetime as dt
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from carscraper.listings import COLUMNS
from carscraper.scraping.urls import BASE

CARD_SELECTOR = (
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
    cards = soup.select(CARD_SELECTOR)
    # The advert URL also identifies cards when test IDs change.
    if not cards:
        cards = soup.select("article")
    rows = []
    for card in cards:
        link = card.select_one('a[href*="/car-details/"]')
        if link is None:
            continue
        absolute = urljoin(BASE, link["href"])
        parts = urlsplit(absolute)
        if parts.netloc != "www.autotrader.co.uk" or not re.fullmatch(
            r"/car-details/\d+/?", parts.path
        ):
            continue
        text = card.get_text(" ", strip=True)
        heading = card.select_one("h2, h3")
        seller = card.select_one('[data-testid="search-listing-seller"]')
        seller_text = seller.get_text(" ", strip=True) if seller else ""
        location = re.sub(r"\s*\([\d,.]+\s*miles?\).*", "", seller_text)
        location = re.sub(r"^.*?Dealer location\s*", "", location).strip()
        year = number(r"\b((?:19|20)\d{2})\s*\(\d{2}\s*reg\)", text)
        if year is None:
            specs = card.select_one('[data-testid="search-listing-specs"]')
            year = number(r"\b((?:19|20)\d{2})\b", specs.get_text(" ") if specs else "")
        mileage = number(r"([\d,]+)\s*miles\b", text)
        age = dt.date.today().year - year if year else None
        row = dict.fromkeys(COLUMNS)
        row.update(
            name=heading.get_text(" ", strip=True)
            if heading
            else f"{car['make']} {car['model']}",
            link=BASE + parts.path,
            price=number(r"£\s*([\d,]+)", text),
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
