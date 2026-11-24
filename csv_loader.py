"""Reading CSV files into flight records and error messages."""

import csv
import os

from validator import to_record, validate_row


def parse_files(paths: list[str], airports: set[str]) -> tuple[list[dict], list[str]]:
    """Process the CSV files in the order given.

    Return (records, errors):
      records - valid flight records, in input order
      errors  - one message per invalid row, in input order, formatted as
                "<file name>:<line number>: <ERROR_CODE> | <free text>"
                (base file name only, no timestamp or level, no newline)

    Also performs the DUPLICATE_FLIGHT check across all the files.
    Does not write any files and does not log anything itself.
    """
    records = []
    errors = []
    seen_flights = set()

    for file_path in paths:
        base_name = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            for line_num, raw_line in enumerate(f, start=1):
                if line_num == 1:
                    continue

                stripped = raw_line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                fields = next(csv.reader([raw_line]))
                err_code = validate_row(fields, airports)

                if err_code is not None:
                    clean_raw = raw_line.rstrip("\r\n")
                    errors.append(f"{base_name}:{line_num}: {err_code} | {clean_raw}")
                    continue

                record = to_record(fields)
                flight_key = (record["flight_id"], record["departure_datetime"])

                if flight_key in seen_flights:
                    clean_raw = raw_line.rstrip("\r\n")
                    errors.append(f"{base_name}:{line_num}: DUPLICATE_FLIGHT | {clean_raw}")
                    continue

                seen_flights.add(flight_key)
                records.append(record)

    return records, errors