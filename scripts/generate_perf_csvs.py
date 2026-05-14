#!/usr/bin/env python3
"""
Generates CSV files consumed by JMeter perf_test.jmx.

Two kinds of CSVs are produced:
  - *_new.csv   : data for POST requests (creating new records)
  - *_ids.csv   : IDs for GET requests (querying existing records)

Adjust the constants below to match your actual database state.
Run from project root:  python scripts/generate_perf_csvs.py
"""

import csv
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration — tune to match your DB
# ---------------------------------------------------------------------------
N_NEW_USERS       = 10_000   # rows in users_new.csv
N_NEW_CINEMAS     = 5_000    # rows in cinemas_new.csv
N_READ_ROWS       = 5_000    # rows in every *_ids.csv (JMeter recycles these)

MAX_USER_ID        = 5_000
MAX_CINEMA_ID      = 15
MAX_RESERVATION_ID = 1_918_226
MAX_TICKET_ID      = 5_755_289

OUTPUT_DIR = Path(__file__).parent.parent / "tests" / "data" / "perf"

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
CITIES = [
    "Warszawa", "Kraków", "Wrocław", "Gdańsk", "Poznań",
    "Łódź", "Katowice", "Lublin", "Rzeszów", "Szczecin",
]
CINEMA_NAMES = [
    "Helios", "Multikino", "Cinema City", "Kinepolis",
    "Muranów", "Luna", "Iluzjon", "Nowe Horyzonty", "Kino Moskwa",
]


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------
def gen_users_new() -> list[dict]:
    return [
        {
            "email":    f"perf_{i}_{random.randint(10_000, 99_999)}@loadtest.com",
            "username": f"perfuser_{i}",
        }
        for i in range(1, N_NEW_USERS + 1)
    ]


def gen_cinemas_new() -> list[dict]:
    return [
        {
            "name": f"{random.choice(CINEMA_NAMES)} {random.choice(CITIES)} {i}",
            "city": random.choice(CITIES),
        }
        for i in range(1, N_NEW_CINEMAS + 1)
    ]


def gen_ids(max_id: int, col: str) -> list[dict]:
    step = max(1, max_id // N_READ_ROWS)
    ids = list(range(1, max_id + 1, step))[:N_READ_ROWS]
    random.shuffle(ids)
    return [{col: v} for v in ids]


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------
def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {path.name:<35} {len(rows):>6} rows")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing CSVs → {OUTPUT_DIR}/\n")

    write_csv(OUTPUT_DIR / "users_new.csv",        gen_users_new(),                          ["email", "username"])
    write_csv(OUTPUT_DIR / "cinemas_new.csv",       gen_cinemas_new(),                        ["name", "city"])
    write_csv(OUTPUT_DIR / "user_ids.csv",          gen_ids(MAX_USER_ID,        "user_id"),        ["user_id"])
    write_csv(OUTPUT_DIR / "cinema_ids.csv",        gen_ids(MAX_CINEMA_ID,      "cinema_id"),      ["cinema_id"])
    write_csv(OUTPUT_DIR / "reservation_ids.csv",   gen_ids(MAX_RESERVATION_ID, "reservation_id"), ["reservation_id"])
    write_csv(OUTPUT_DIR / "ticket_ids.csv",        gen_ids(MAX_TICKET_ID,      "ticket_id"),      ["ticket_id"])

    print("\nDone. Now open JMeter and run tests/perf_test.jmx")


if __name__ == "__main__":
    main()
