"""Running queries against the flight database."""

from validator import parse_exact_datetime

ALLOWED_KEYS = {
    "flight_id",
    "origin",
    "destination",
    "departure_datetime",
    "arrival_datetime",
    "price",
    "min_price",
    "sort_by",
    "order",
    "limit",
}

RECORD_KEYS = {
    "flight_id",
    "origin",
    "destination",
    "departure_datetime",
    "arrival_datetime",
    "price",
}


def is_valid_number(val) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def is_valid_int(val) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def validate_query(query: dict) -> bool:
    if not isinstance(query, dict):
        return False

    for key in query:
        if key not in ALLOWED_KEYS:
            return False

    if "order" in query and "sort_by" not in query:
        return False

    for str_key in ("flight_id", "origin", "destination"):
        if str_key in query and not isinstance(query[str_key], str):
            return False

    for dt_key in ("departure_datetime", "arrival_datetime"):
        if dt_key in query:
            if not isinstance(query[dt_key], str):
                return False
            if parse_exact_datetime(query[dt_key]) is None:
                return False

    for num_key in ("price", "min_price"):
        if num_key in query and not is_valid_number(query[num_key]):
            return False

    if "sort_by" in query:
        if not isinstance(query["sort_by"], str) or query["sort_by"] not in RECORD_KEYS:
            return False

    if "order" in query:
        if query["order"] not in ("asc", "desc"):
            return False

    if "limit" in query:
        if not is_valid_int(query["limit"]) or query["limit"] < 0:
            return False

    return True


def matches_flight(flight: dict, query: dict) -> bool:
    if "flight_id" in query and flight["flight_id"] != query["flight_id"]:
        return False
    if "origin" in query and flight["origin"] != query["origin"]:
        return False
    if "destination" in query and flight["destination"] != query["destination"]:
        return False
    if "departure_datetime" in query and flight["departure_datetime"] < query["departure_datetime"]:
        return False
    if "arrival_datetime" in query and flight["arrival_datetime"] > query["arrival_datetime"]:
        return False
    if "price" in query and flight["price"] > query["price"]:
        return False
    if "min_price" in query and flight["price"] < query["min_price"]:
        return False
    return True


def run_query(db: list[dict], query: dict) -> dict:
    """Return one response entry for one query object.

    Valid query:   {"query": query, "matches": [...]}
    Invalid query: {"query": query, "error": "INVALID_QUERY", "matches": []}
    """
    if not validate_query(query):
        return {
            "query": query,
            "error": "INVALID_QUERY",
            "matches": [],
        }

    results = [flight for flight in db if matches_flight(flight, query)]

    if "sort_by" in query:
        sort_field = query["sort_by"]
        reverse_order = query.get("order", "asc") == "desc"
        results = sorted(results, key=lambda item: item[sort_field], reverse=reverse_order)

    if "limit" in query:
        results = results[: query["limit"]]

    return {
        "query": query,
        "matches": results,
    }


def run_queries(db: list[dict], queries: dict | list) -> list[dict]:
    """Accept one query object or a list of them; always return a list."""
    if isinstance(queries, dict):
        query_list = [queries]
    else:
        query_list = queries

    return [run_query(db, q) for q in query_list]