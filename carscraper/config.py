"""Search configuration loading and validation."""

import json
from pathlib import Path


def load_config(path):
    """Read a JSON search file and return validated settings."""
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_config(config)


def validate_config(config):
    """Validate search settings independently of their input source."""
    if not isinstance(config, dict):
        raise ValueError("Search settings must be a JSON object")
    criteria = config.get("criteria", {})
    if not isinstance(criteria, dict) or not str(criteria.get("postcode", "")).strip():
        raise ValueError("criteria.postcode is required")
    allowed = {"postcode", "radius", "year_from", "year_to", "price_from", "price_to"}
    if set(criteria) - allowed:
        raise ValueError(f"Unknown criteria: {sorted(set(criteria) - allowed)}")
    for field in allowed - {"postcode"}:
        if field in criteria:
            value = criteria[field]
            if isinstance(value, bool) or not str(value).isdigit():
                raise ValueError(f"criteria.{field} must be a non-negative integer")
            criteria[field] = int(value)
    for field in ("year", "price"):
        lower, upper = criteria.get(field + "_from"), criteria.get(field + "_to")
        if lower is not None and upper is not None and lower > upper:
            raise ValueError(f"{field}_from must not exceed {field}_to")
    cars = config.get("cars")
    if not isinstance(cars, list) or not cars:
        raise ValueError("cars must contain at least one make/model pair")
    for car in cars:
        if not isinstance(car, dict) or any(
            not isinstance(car.get(key), str) or not car[key].strip()
            for key in ("make", "model")
        ):
            raise ValueError("Each car needs a non-empty make and model")
    return config
