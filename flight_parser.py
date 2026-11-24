"""Flight Schedule Parser and Query Tool - command-line entry point.

Run from the project folder, for example:
    python flight_parser.py -i data/db.csv -a data/airports.txt
"""
import argparse
import datetime
import json
import logging
import os
import sys

from csv_loader import parse_files
from query import run_queries
from validator import load_airports

# TODO: fill in your details: plain ASCII, no spaces or underscores.
STUDENT_ID = "260RDB177"
FIRST_NAME = "ANDREA"
LAST_NAME = "BOLE"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate flight CSVs and query flight database.")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("-i", dest="input_file", help="Single CSV file to parse")
    source_group.add_argument("-d", dest="input_dir", help="Folder of CSV files to parse")
    source_group.add_argument("-j", dest="json_db", help="Existing JSON database to load")

    parser.add_argument("-a", dest="airports_file", help="Airport list file")
    parser.add_argument("-o", dest="output_db", help="Output path for JSON database")
    parser.add_argument("-q", dest="query_file", help="JSON file with queries")
    parser.add_argument("-r", dest="response_dir", default=".", help="Folder for query response")
    return parser


def print_error(msg: str, logger: logging.Logger | None = None) -> None:
    if logger is not None:
        logger.error(msg)
    print(f"Error: {msg}", file=sys.stderr)


def load_json_db(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("Database JSON must be a list of objects")
    return data


def load_queries_file(path: str) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data
    raise ValueError("Query JSON must be an object or a list of objects")


def main(argv: list[str] | None = None) -> int:
    """Run the whole program and return the exit code (0, 1 or 2).

    argv is the argument list without the program name.
    None means use sys.argv[1:] (argparse does this for you).
    Do not call sys.exit() inside main(); return the code instead.
    """
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    if args.json_db is not None:
        if args.output_db is not None:
            try:
                parser.error("argument -o cannot be used with -j")
            except SystemExit as exc:
                return exc.code if isinstance(exc.code, int) else 2
    else:
        if args.airports_file is None:
            try:
                parser.error("argument -a is required when using -i or -d")
            except SystemExit as exc:
                return exc.code if isinstance(exc.code, int) else 2

    db_records: list[dict] = []
    logger = None
    handler = None

    try:
        if args.json_db is not None:
            if not os.path.isfile(args.json_db):
                print_error(f"Database file not found: {args.json_db}")
                return 1
            try:
                db_records = load_json_db(args.json_db)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                print_error(f"Failed to load JSON database: {exc}")
                return 1
        else:
            output_path = args.output_db if args.output_db is not None else "db.json"
            out_folder = os.path.dirname(os.path.abspath(output_path))
            log_path = os.path.join(out_folder, "errors.log")

            try:
                logger = logging.getLogger("flight_parser")
                logger.setLevel(logging.INFO)
                handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
                handler.setFormatter(
                    logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
                )
                logger.addHandler(handler)
            except OSError as exc:
                print_error(f"Cannot open log file: {exc}")
                return 1

            if not os.path.isfile(args.airports_file):
                print_error(f"Airport file not found: {args.airports_file}", logger)
                return 1

            try:
                airports = load_airports(args.airports_file)
            except OSError as exc:
                print_error(f"Cannot read airport file: {exc}", logger)
                return 1

            csv_paths = []
            if args.input_file is not None:
                if not os.path.isfile(args.input_file):
                    print_error(f"CSV file not found: {args.input_file}", logger)
                    return 1
                csv_paths = [args.input_file]
            elif args.input_dir is not None:
                if not os.path.isdir(args.input_dir):
                    print_error(f"Folder not found: {args.input_dir}", logger)
                    return 1
                try:
                    entries = sorted(os.listdir(args.input_dir))
                except OSError as exc:
                    print_error(f"Cannot read folder: {exc}", logger)
                    return 1

                for name in entries:
                    full_path = os.path.join(args.input_dir, name)
                    if name.endswith(".csv") and os.path.isfile(full_path):
                        csv_paths.append(full_path)

                if not csv_paths:
                    print_error(f"No .csv files found in {args.input_dir}", logger)
                    return 1

            try:
                db_records, error_lines = parse_files(csv_paths, airports)
            except (OSError, UnicodeDecodeError) as exc:
                print_error(f"Error reading CSV files: {exc}", logger)
                return 1

            for err_msg in error_lines:
                logger.warning(err_msg)

            try:
                with open(output_path, "w", encoding="utf-8") as out_f:
                    json.dump(db_records, out_f, indent=2)
            except OSError as exc:
                print_error(f"Cannot write database file: {exc}", logger)
                return 1

        if args.query_file is not None:
            if not os.path.isfile(args.query_file):
                print_error(f"Query file not found: {args.query_file}", logger)
                return 1
            if not os.path.isdir(args.response_dir):
                print_error(f"Response folder not found: {args.response_dir}", logger)
                return 1

            try:
                queries_data = load_queries_file(args.query_file)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                print_error(f"Invalid query file: {exc}", logger)
                return 1

            responses = run_queries(db_records, queries_data)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            resp_filename = f"response_{STUDENT_ID}_{FIRST_NAME}_{LAST_NAME}_{timestamp}.json"
            resp_path = os.path.join(args.response_dir, resp_filename)

            try:
                with open(resp_path, "w", encoding="utf-8") as resp_f:
                    json.dump(responses, resp_f, indent=2)
            except OSError as exc:
                print_error(f"Cannot write response file: {exc}", logger)
                return 1

    finally:
        if logger is not None and handler is not None:
            logger.removeHandler(handler)
            handler.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())