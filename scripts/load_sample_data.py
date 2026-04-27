import asyncio
import logging
import random
import sys
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import tuple_row

# Założenie: Twoja klasa konfiguracyjna
from src.config import DatabaseConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Stałe konfiguracyjne
NUM_CINEMAS = 10
HALLS_PER_CINEMA = 6
NUM_USERS = 5000
DAYS_OF_DATA = 365
SHOWTIMES_PER_DAY = 5


async def execute_values(cur, query, template, args_list, fetch=False):
    """Pomocnicza funkcja do masowego wstawiania danych z automatycznym podziałem na paczki (chunking)."""
    if not args_list:
        return []

    # Liczymy ile parametrów (%s) przypada na jeden wiersz
    params_per_row = template.count("%s")

    # Obliczamy maksymalną liczbę wierszy w paczce (z marginesem bezpieczeństwa do 60 000)
    max_rows_per_batch = 60000 // params_per_row

    all_results = []

    for i in range(0, len(args_list), max_rows_per_batch):
        batch = args_list[i:i + max_rows_per_batch]
        records_list_template = ','.join([template] * len(batch))
        insert_query = query.format(records_list_template)

        flat_args = [item for sublist in batch for item in sublist]

        await cur.execute(insert_query, flat_args)
        if fetch:
            all_results.extend(await cur.fetchall())

    return all_results


async def load_sample_data():
    conn_string = DatabaseConfig.get_connection_string()
    # Używamy autocommit w celach batchowania lub zarządzamy transakcjami ręcznie.
    # Ustawiamy row_factory na tuple dla uproszczenia
    conn = await psycopg.AsyncConnection.connect(conn_string, row_factory=tuple_row)

    try:
        async with conn.cursor() as cur:
            logger.info("Rozpoczynam generowanie dużej paczki danych...")

            # 1. TYPY SAL I MIEJSC (pobieramy z bazy, zakładamy że istnieją po inicjalizacji)
            await cur.execute("SELECT hall_type_id FROM hall_types LIMIT 1")
            hall_type_id = (await cur.fetchone())[0]

            await cur.execute("SELECT seat_type_id FROM seat_types LIMIT 1")
            seat_type_id = (await cur.fetchone())[0]

            # 2. FILMY
            logger.info("Generowanie filmów...")
            movies_data = [(f"Movie Title {i}", random.randint(90, 180)) for i in range(1, 51)]
            movies_ids = await execute_values(
                cur,
                "INSERT INTO movies (title, duration_minutes) VALUES {} RETURNING movie_id",
                "(%s, %s)",
                movies_data,
                fetch=True
            )
            movie_ids = [m[0] for m in movies_ids]

            # 3. KINA I SALE
            logger.info("Generowanie kin, sal i miejsc...")
            cities = ["Warszawa", "Kraków", "Wrocław", "Poznań", "Gdańsk"]
            cinemas_data = [(f"Cinema City {i}", random.choice(cities)) for i in range(1, NUM_CINEMAS + 1)]

            cinema_records = await execute_values(
                cur,
                "INSERT INTO cinemas (name, city) VALUES {} RETURNING cinema_id",
                "(%s, %s)",
                cinemas_data,
                fetch=True
            )
            cinema_ids = [c[0] for c in cinema_records]

            hall_ids = []
            for c_id in cinema_ids:
                halls_data = [(c_id, hall_type_id, f"Sala {h}", 150) for h in range(1, HALLS_PER_CINEMA + 1)]
                h_records = await execute_values(
                    cur,
                    "INSERT INTO halls (cinema_id, hall_type_id, name, capacity) VALUES {} RETURNING hall_id",
                    "(%s, %s, %s, %s)",
                    halls_data,
                    fetch=True
                )
                hall_ids.extend([h[0] for h in h_records])

            # 4. MIEJSCA
            seats_data = []
            rows = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
            for h_id in hall_ids:
                for row_idx, r_label in enumerate(rows):
                    for s_num in range(1, 16):  # 15 miejsc w rzędzie = 150 na salę
                        seats_data.append((h_id, seat_type_id, r_label, s_num))

            # Wstawiamy miejsca w paczkach po 5000, aby nie zablokować bazy
            for i in range(0, len(seats_data), 5000):
                await execute_values(cur, "INSERT INTO seats (hall_id, seat_type_id, row_label, seat_number) VALUES {}",
                                     "(%s, %s, %s, %s)", seats_data[i:i + 5000])

            # 5. UŻYTKOWNICY
            logger.info("Generowanie użytkowników...")
            users_data = [(f"user{i}@example.com", f"user{i}") for i in range(1, NUM_USERS + 1)]
            user_records = await execute_values(
                cur,
                "INSERT INTO users (email, username) VALUES {} RETURNING user_id",
                "(%s, %s)",
                users_data,
                fetch=True
            )
            user_ids = [u[0] for u in user_records]

            # 6. SEANSE, REZERWACJE I BILETY (Główna pętla generująca miliony wierszy)
            logger.info("Generowanie seansów i biletów (to zajmie chwilę)...")

            # Pobieramy wszystkie id miejsc zgrupowane po salach, żeby szybko losować
            await cur.execute("SELECT hall_id, seat_id FROM seats")
            all_seats = await cur.fetchall()
            seats_by_hall = {}
            for h_id, s_id in all_seats:
                seats_by_hall.setdefault(h_id, []).append(s_id)

            start_date = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

            for day in range(DAYS_OF_DATA):
                current_date = start_date + timedelta(days=day)

                showtimes_data = []
                # Generujemy seanse dla każdej sali
                for h_id in hall_ids:
                    for show_num in range(SHOWTIMES_PER_DAY):
                        movie_id = random.choice(movie_ids)
                        show_time = current_date + timedelta(hours=show_num * 3)
                        showtimes_data.append((movie_id, h_id, show_time, 25.00))

                # Wstawiamy seanse na dany dzień
                showtimes_records = await execute_values(
                    cur,
                    "INSERT INTO showtimes (movie_id, hall_id, start_datetime, base_price) VALUES {} RETURNING showtime_id, hall_id",
                    "(%s, %s, %s, %s)",
                    showtimes_data,
                    fetch=True
                )

                reservations_data = []

                # Przygotowujemy pulę wolnych miejsc dla każdego seansu (mieszamy je raz)
                available_seats_for_st = {}
                for st_id, h_id in showtimes_records:
                    seats = list(seats_by_hall[h_id])
                    random.shuffle(seats)
                    available_seats_for_st[st_id] = seats

                # Przygotowujemy rezerwacje dla wygenerowanych seansów
                for st_id, h_id in showtimes_records:
                    num_reservations = random.randint(10, 25)
                    for _ in range(num_reservations):
                        u_id = random.choice(user_ids)
                        reservations_data.append((u_id, st_id, 'confirmed'))

                # Wstawiamy rezerwacje
                res_records = await execute_values(
                    cur,
                    "INSERT INTO reservations (user_id, showtime_id, status) VALUES {} RETURNING reservation_id",
                    "(%s, %s, %s)",
                    reservations_data,
                    fetch=True
                )

                res_seats_data = []
                tickets_data = []

                # Przypisujemy miejsca do rezerwacji
                for idx, (res_id,) in enumerate(res_records):
                    st_id = reservations_data[idx][1]
                    u_id = reservations_data[idx][0]

                    num_tickets = random.randint(2, 4)

                    # Ściągamy miejsca z puli dostępnych dla TEGO seansu
                    for _ in range(num_tickets):
                        if available_seats_for_st[st_id]:  # Upewniamy się, że sala nie jest pełna
                            s_id = available_seats_for_st[st_id].pop()
                            res_seats_data.append((res_id, s_id))
                            tickets_data.append((st_id, s_id, u_id, res_id, 25.00, 'valid'))

                # Wstawiamy reservation_seats
                await execute_values(cur, "INSERT INTO reservation_seats (reservation_id, seat_id) VALUES {}",
                                     "(%s, %s)", res_seats_data)

                # Wstawiamy tickets
                await execute_values(cur,
                                     "INSERT INTO tickets (showtime_id, seat_id, user_id, reservation_id, final_price, status) VALUES {}",
                                     "(%s, %s, %s, %s, %s, %s)", tickets_data)

                # Commitujemy codziennie, aby nie trzymać ogromnej transakcji w pamięci
                await conn.commit()

                if (day + 1) % 30 == 0:
                    logger.info(f"Wygenerowano dane dla {day + 1} dni...")

            logger.info("Zakończono ładowanie danych testowych sukcesem!")

    except Exception as e:
        logger.error(f"Błąd podczas ładowania danych: {e}")
        await conn.rollback()
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    # Wymuszenie SelectorEventLoop na systemach Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(load_sample_data())