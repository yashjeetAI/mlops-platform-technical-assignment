"""Small text utilities."""
import re


def slugify(value: str) -> str:
    """Turn a name into a URL-safe slug, e.g. 'Pump Failure Predictor' -> 'pump-failure-predictor'.

    Non-alphanumeric runs collapse to a single hyphen; empty results fall back to 'model'.
    """
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "model"
