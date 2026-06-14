import os
import sys
import time
import logging

import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


N_CINEMAS = env_int("N_CINEMAS", 50)
HALLS_PER_CINEMA = env_int("HALLS_PER_CINEMA", 20)
SEATS_PER_HALL = env_int("SEATS_PER_HALL", 200)
SEATS_PER_ROW = env_int("SEATS_PER_ROW", 20)
N_MOVIES = env_int("N_MOVIES", 1000)
N_GENRES = env_int("N_GENRES", 15)
N_USERS = env_int("N_USERS", 1_000_000)
N_SHOWTIMES = env_int("N_SHOWTIMES", 200_000)
N_RESERVATIONS = env_int("N_RESERVATIONS", 5_000_000)
N_PAYMENTS = env_int("N_PAYMENTS", 3_000_000)
TICKET_FILL = env_float("TICKET_FILL", 0.5)

N_HALLS = N_CINEMAS * HALLS_PER_CINEMA


def connect() -> psycopg.Connection:
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=env_int("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "kino"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "pswd"),
        autocommit=False,
    )


def step(cur, label: str, sql: str) -> None:
    t0 = time.perf_counter()
    cur.execute(sql)
    dt = time.perf_counter() - t0
    logger.info(f"  [{dt:7.1f}s] {label} ({cur.rowcount if cur.rowcount >= 0 else '?'} wierszy)")


BULK_TABLES = ["tickets", "reservations", "payments", "showtimes", "seats", "users"]


def capture_and_drop_indexes(cur):
    cur.execute("""
        SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE contype = 'f' AND conrelid = ANY(%s::regclass[])
    """, (BULK_TABLES,))
    fks = cur.fetchall()

    cur.execute("""
        SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE contype = 'u' AND conrelid = ANY(%s::regclass[])
    """, (BULK_TABLES,))
    uniques = cur.fetchall()

    cur.execute("""
        SELECT c.relname, pg_get_indexdef(i.indexrelid)
        FROM pg_index i
        JOIN pg_class c ON c.oid = i.indexrelid
        JOIN pg_class t ON t.oid = i.indrelid
        WHERE t.relname = ANY(%s)
          AND NOT i.indisprimary
          AND i.indexrelid NOT IN (SELECT conindid FROM pg_constraint WHERE conindid <> 0)
    """, (BULK_TABLES,))
    indexes = cur.fetchall()

    for tbl, conname, _ in fks:
        cur.execute(f'ALTER TABLE {tbl} DROP CONSTRAINT IF EXISTS "{conname}"')
    for tbl, conname, _ in uniques:
        cur.execute(f'ALTER TABLE {tbl} DROP CONSTRAINT IF EXISTS "{conname}"')
    for idxname, _ in indexes:
        cur.execute(f'DROP INDEX IF EXISTS "{idxname}"')

    logger.info(f"  zrzucono {len(indexes)} indeksow, {len(uniques)} unikalnych, {len(fks)} FK")
    return fks, uniques, indexes


def recreate_indexes(cur, fks, uniques, indexes):
    for idxname, idxdef in indexes:
        step(cur, f"index {idxname}", idxdef)
    for tbl, conname, condef in uniques:
        step(cur, f"unique {conname}", f'ALTER TABLE {tbl} ADD CONSTRAINT "{conname}" {condef}')
    for tbl, conname, condef in fks:
        step(cur, f"fk {conname}", f'ALTER TABLE {tbl} ADD CONSTRAINT "{conname}" {condef}')


def main() -> None:
    if SEATS_PER_HALL % SEATS_PER_ROW != 0 or SEATS_PER_HALL // SEATS_PER_ROW > 26:
        logger.warning("SEATS_PER_HALL / SEATS_PER_ROW powinno byc calkowite i <= 26 (etykiety rzedow A-Z).")

    est_tickets = int(N_SHOWTIMES * SEATS_PER_HALL * TICKET_FILL)
    logger.info("=" * 70)
    logger.info(" MASOWE LADOWANIE DANYCH")
    logger.info(f"  kina={N_CINEMAS} sale={N_HALLS} miejsca={N_HALLS * SEATS_PER_HALL:,}")
    logger.info(f"  uzytkownicy={N_USERS:,} seanse={N_SHOWTIMES:,}")
    logger.info(f"  rezerwacje={N_RESERVATIONS:,} platnosci={N_PAYMENTS:,}")
    logger.info(f"  szac. bilety ~ {est_tickets:,}")
    logger.info("=" * 70)

    conn = connect()
    t_start = time.perf_counter()
    try:
        with conn.cursor() as cur:
            cur.execute("SET synchronous_commit TO off")
            cur.execute("SET maintenance_work_mem TO '2GB'")
            cur.execute("SET work_mem TO '512MB'")
            cur.execute("SET max_parallel_workers_per_gather TO 8")
            cur.execute("SET max_parallel_maintenance_workers TO 7")

            logger.info("Czyszczenie tabel (TRUNCATE ... RESTART IDENTITY CASCADE)...")
            step(cur, "truncate", """
                TRUNCATE cinemas, halls, seats, movies, genres, movie_genres,
                         users, showtimes, reservations, reservation_seats,
                         tickets, payments, ticket_payments, refunds
                RESTART IDENTITY CASCADE
            """)

            logger.info("Zrzucanie indeksow i FK na czas ladowania...")
            saved_fks, saved_uniques, saved_indexes = capture_and_drop_indexes(cur)

            step(cur, "movies", f"""
                INSERT INTO movies (title, duration_minutes)
                SELECT 'Movie Title ' || g, 80 + (g % 100)
                FROM generate_series(1, {N_MOVIES}) g
            """)

            step(cur, "genres", f"""
                INSERT INTO genres (name)
                SELECT 'Genre ' || g FROM generate_series(1, {N_GENRES}) g
            """)

            step(cur, "movie_genres", f"""
                INSERT INTO movie_genres (movie_id, genre_id)
                SELECT m, 1 + floor(random() * {N_GENRES})::int
                FROM generate_series(1, {N_MOVIES}) m
                ON CONFLICT DO NOTHING
            """)

            step(cur, "cinemas", f"""
                INSERT INTO cinemas (name, city)
                SELECT 'Cinema City ' || g,
                       (ARRAY['Warszawa','Krakow','Wroclaw','Poznan','Gdansk'])[1 + (g % 5)]
                FROM generate_series(1, {N_CINEMAS}) g
            """)

            step(cur, "halls", f"""
                INSERT INTO halls (cinema_id, hall_type_id, name, capacity)
                SELECT c, (SELECT min(hall_type_id) FROM hall_types),
                       'Sala ' || h, {SEATS_PER_HALL}
                FROM generate_series(1, {N_CINEMAS}) c,
                     generate_series(1, {HALLS_PER_CINEMA}) h
            """)

            step(cur, "seats", f"""
                INSERT INTO seats (hall_id, seat_type_id, row_label, seat_number)
                SELECT h.hall_id,
                       (ARRAY(SELECT seat_type_id FROM seat_types ORDER BY seat_type_id))
                           [1 + floor(random() * (SELECT count(*) FROM seat_types))::int],
                       chr(65 + (n / {SEATS_PER_ROW})::int),
                       1 + (n % {SEATS_PER_ROW})
                FROM halls h
                CROSS JOIN generate_series(0, {SEATS_PER_HALL} - 1) n
            """)


            step(cur, "users", f"""
                INSERT INTO users (email, username)
                SELECT 'user' || g || '@loadtest.com', 'user' || g
                FROM generate_series(1, {N_USERS}) g
            """)

            step(cur, "showtimes", f"""
                INSERT INTO showtimes (movie_id, hall_id, start_datetime, base_price)
                SELECT 1 + floor(random() * {N_MOVIES})::int,
                       1 + floor(random() * {N_HALLS})::int,
                       now() + ((1 + floor(random() * 365)) || ' days')::interval
                            + ((floor(random() * 12) * 60) || ' minutes')::interval,
                       20.00 + (g % 30)
                FROM generate_series(1, {N_SHOWTIMES}) g
            """)

            step(cur, "reservations", f"""
                INSERT INTO reservations (user_id, showtime_id, status)
                SELECT 1 + floor(random() * {N_USERS})::int,
                       1 + floor(random() * {N_SHOWTIMES})::int,
                       'confirmed'
                FROM generate_series(1, {N_RESERVATIONS}) g
            """)

            step(cur, "tickets", f"""
                INSERT INTO tickets (showtime_id, seat_id, user_id, final_price, status)
                SELECT s.showtime_id, se.seat_id,
                       1 + floor(random() * {N_USERS})::int,
                       25.00, 'valid'
                FROM showtimes s
                JOIN seats se ON se.hall_id = s.hall_id
                WHERE random() < {TICKET_FILL}
            """)

            step(cur, "payments", f"""
                INSERT INTO payments (user_id, payment_method_id, amount, status)
                SELECT 1 + floor(random() * {N_USERS})::int,
                       (ARRAY(SELECT payment_method_id FROM payment_methods ORDER BY payment_method_id))
                           [1 + floor(random() * (SELECT count(*) FROM payment_methods))::int],
                       round((10 + random() * 200)::numeric, 2),
                       'completed'
                FROM generate_series(1, {N_PAYMENTS}) g
            """)

            logger.info("Odtwarzanie indeksow, unikalnych i FK (z walidacja zbiorcza)...")
            recreate_indexes(cur, saved_fks, saved_uniques, saved_indexes)

        conn.commit()

        conn.autocommit = True
        with conn.cursor() as cur:
            logger.info("ANALYZE (statystyki dla plannera)...")
            step(cur, "analyze", "ANALYZE")

            logger.info("-" * 70)
            cur.execute("""
                SELECT relname, n_live_tup
                FROM pg_stat_user_tables
                WHERE n_live_tup > 0
                ORDER BY n_live_tup DESC
            """)
            for relname, n in cur.fetchall():
                logger.info(f"  {relname:<20} {n:>14,}")

        logger.info("-" * 70)
        logger.info(f"GOTOWE w {time.perf_counter() - t_start:.1f}s")
    except Exception as e:
        logger.error(f"Blad podczas ladowania: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
