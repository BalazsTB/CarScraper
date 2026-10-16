"""AutoTrader search URL construction."""

from urllib.parse import urlencode

BASE = "https://www.autotrader.co.uk"


def search_url(car, criteria, page=1):
    params = {
        "advertising-location": "at_cars",
        "sort": "distance",
        "make": car["make"],
        "model": car["model"],
        "page": page,
    }
    params.update({key.replace("_", "-"): value for key, value in criteria.items()})
    return BASE + "/car-search?" + urlencode(params)
