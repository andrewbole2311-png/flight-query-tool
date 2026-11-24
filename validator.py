"""Row validation: airport list loading, single-row checks, record building."""

import datetime
import math
import re

FLIGHT_ID_RE = re.compile(r"^[A-Za-z0-9]{2,8}$")
AIRPORT_RE = re.compile(r"^[A-Z]{3}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


def parse_exact_datetime(value: str) -> datetime.datetime | None:
    if not DATETIME_RE.match(value):
        return None
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def load_airports(path: str) -> set[str]:
    """Read an airport list file and return the set of codes.

    One code per line. Strip whitespace; skip blank lines and lines
    starting with '#'.
    """
    airports = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            code = line.strip()
            if not code or code.startswith("#"):
                continue
            airports.add(code)
    return airports


def validate_row(fields: list[str], airports: set[str]) -> str | None:
    """Check one CSV row (fields as returned by csv.reader, not yet stripped).

    Return None if the row is valid, otherwise the error code of the
    FIRST failing check (checks 1-11 in the specification, in order).
    Does not check for duplicates.
    """
    if len(fields) != 6:
        return "WRONG_FIELD_COUNT"

    cleaned = [item.strip() for item in fields]
    if any(item == "" for item in cleaned):
        return "MISSING_FIELD"

    flight_id, origin, destination, dep_str, arr_str, price_str = cleaned

    if not FLIGHT_ID_RE.match(flight_id):
        return "INVALID_FLIGHT_ID"

    if not AIRPORT_RE.match(origin) or origin not in airports:
        return "INVALID_ORIGIN"

    if not AIRPORT_RE.match(destination) or destination not in airports:
        return "INVALID_DESTINATION"

    if origin == destination:
        return "SAME_ORIGIN_DESTINATION"

    dep_dt = parse_exact_datetime(dep_str)
    if dep_dt is None:
        return "INVALID_DEPARTURE"

    arr_dt = parse_exact_datetime(arr_str)
    if arr_dt is None:
        return "INVALID_ARRIVAL"

    if arr_dt <= dep_dt:
        return "ARRIVAL_NOT_AFTER_DEPARTURE"

    try:
        price = float(price_str)
    except ValueError:
        return "INVALID_PRICE"

    if not math.isfinite(price):
        return "INVALID_PRICE"

    if price <= 0:
        return "NON_POSITIVE_PRICE"

    return None


def to_record(fields: list[str]) -> dict:
    """Turn a valid row into a flight record dictionary.

    Keys: flight_id, origin, destination, departure_datetime,
    arrival_datetime (stripped strings) and price (float).
    """
    cleaned = [item.strip() for item in fields]
    return {
        "flight_id": cleaned[0],
        "origin": cleaned[1],
        "destination": cleaned[2],
        "departure_datetime": cleaned[3],
        "arrival_datetime": cleaned[4],
        "price": float(cleaned[5]),
    }