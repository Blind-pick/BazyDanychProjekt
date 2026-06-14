#!/usr/bin/env python3

import csv
import os
import random
from pathlib import Path

try:
    import psycopg
except ImportError:
    psycopg = None

N_NEW_USERS = int(os.getenv("N_NEW_USERS", "20000"))
N_NEW_CINEMAS = int(os.getenv("N_NEW_CINEMAS", "5000"))
N_READ_ROWS = int(os.getenv("N_READ_ROWS", "20000"))

FALLBACK = {"users": 1_000_000, "cinemas": 50, "reservations": 5_000_000,
            "tickets": 20_000_000, "showtimes": 200_000, "movies": 1_000,
            "seats": 200_000}

OUTPUT_DIR = Path(__file__).parent.parent / "tests" / "data" / "perf"

CITIES = ["Warszawa", "Krakow", "Wroclaw", "Gdansk", "Poznan",
          "Lodz", "Katowice", "Lublin", "Rzeszow", "Szczecin"]
CINEMA_NAMES = ["Helios", "Multikino", "Cinema City", "Kinepolis",
                "Muranow", "Luna", "Iluzjon", "Nowe Horyzonty", "Kino Moskwa"]


def fetch_max_ids() -> dict:
    if psycopg is None:
        print("  [uwaga] brak psycopg - uzywam wartosci awaryjnych")
        return dict(FALLBACK)
    try:
        with psycopg.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname=os.getenv("DB_NAME", "kino"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "pswd"),
        ) as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(max(user_id), 0) FROM users;
            """)
            users = cur.fetchone()[0]
            cur.execute("SELECT COALESCE(max(cinema_id), 0) FROM cinemas")
            cinemas = cur.fetchone()[0]
            cur.execute("SELECT COALESCE(max(reservation_id), 0) FROM reservations")
            reservations = cur.fetchone()[0]
            cur.execute("SELECT COALESCE(max(ticket_id), 0) FROM tickets")
            tickets = cur.fetchone()[0]
            cur.execute("SELECT COALESCE(max(showtime_id), 0) FROM showtimes")
            showtimes = cur.fetchone()[0]
            cur.execute("SELECT COALESCE(max(movie_id), 0) FROM movies")
            movies = cur.fetchone()[0]
            cur.execute("SELECT COALESCE(max(seat_id), 0) FROM seats")
            seats = cur.fetchone()[0]
        ids = {"users": users, "cinemas": cinemas,
               "reservations": reservations, "tickets": tickets,
               "showtimes": showtimes, "movies": movies, "seats": seats}
        print(f"  max id z bazy: {ids}")
        return {k: (v or FALLBACK[k]) for k, v in ids.items()}
    except Exception as e:
        print(f"  [uwaga] nie udalo sie odczytac bazy ({e}) - wartosci awaryjne")
        return dict(FALLBACK)


def gen_users_new() -> list[dict]:
    return [{"email": f"perf_{i}_{random.randint(10_000, 99_999)}@loadtest.com",
             "username": f"perfuser_{i}_{random.randint(10_000, 99_999)}"}
            for i in range(1, N_NEW_USERS + 1)]


def gen_cinemas_new() -> list[dict]:
    return [{"name": f"{random.choice(CINEMA_NAMES)} {random.choice(CITIES)} {i}",
             "city": random.choice(CITIES)}
            for i in range(1, N_NEW_CINEMAS + 1)]


def gen_random_ids(max_id: int, col: str) -> list[dict]:
    max_id = max(1, max_id)
    return [{col: random.randint(1, max_id)} for _ in range(N_READ_ROWS)]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {path.name:<25} {len(rows):>7} wierszy")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Odczyt zakresow ID z bazy...")
    ids = fetch_max_ids()
    print(f"Zapis CSV -> {OUTPUT_DIR}/\n")

    write_csv(OUTPUT_DIR / "users_new.csv", gen_users_new(), ["email", "username"])
    write_csv(OUTPUT_DIR / "cinemas_new.csv", gen_cinemas_new(), ["name", "city"])
    write_csv(OUTPUT_DIR / "user_ids.csv", gen_random_ids(ids["users"], "user_id"), ["user_id"])
    write_csv(OUTPUT_DIR / "cinema_ids.csv", gen_random_ids(ids["cinemas"], "cinema_id"), ["cinema_id"])
    write_csv(OUTPUT_DIR / "reservation_ids.csv", gen_random_ids(ids["reservations"], "reservation_id"), ["reservation_id"])
    write_csv(OUTPUT_DIR / "ticket_ids.csv", gen_random_ids(ids["tickets"], "ticket_id"), ["ticket_id"])
    write_csv(OUTPUT_DIR / "showtime_ids.csv", gen_random_ids(ids["showtimes"], "showtime_id"), ["showtime_id"])
    write_csv(OUTPUT_DIR / "movie_ids.csv", gen_random_ids(ids["movies"], "movie_id"), ["movie_id"])

    write_csv(OUTPUT_DIR / "seat_ids.csv", gen_random_ids(ids["seats"], "seat_id"), ["seat_id"])

    print("\nGotowe. Teraz mozesz odpalic tests/perf_test.jmx")


if __name__ == "__main__":
    main()
