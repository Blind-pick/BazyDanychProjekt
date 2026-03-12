import psycopg


class CinemaDatabaseCreator:

    def __init__(self, host, dbname, user, password, port=5432):
        self.host = host
        self.dbname = dbname
        self.user = user
        self.password = password
        self.port = port

        # Najpierw upewniamy się, że baza istnieje
        self._create_database_if_not_exists()

        # Dopiero teraz łączymy się z właściwą bazą
        self.conn = psycopg.connect(
            host=self.host,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            port=self.port
        )

    def _create_database_if_not_exists(self):
        """Tworzy bazę danych, jeśli nie istnieje."""
        conn = psycopg.connect(
            host=self.host,
            dbname="postgres",
            user=self.user,
            password=self.password,
            port=self.port
        )
        conn.autocommit = True

        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (self.dbname,))
            exists = cur.fetchone()

            if not exists:
                cur.execute(f"CREATE DATABASE {self.dbname};")
                print(f"Utworzono bazę danych '{self.dbname}'.")
            else:
                print(f"Baza danych '{self.dbname}' już istnieje.")

        conn.close()

    def create_tables(self):
        queries = [

            # ENUMS
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reservation_status') THEN
                    CREATE TYPE reservation_status AS ENUM ('pending', 'confirmed', 'cancelled');
                END IF;
            END$$;
            """,

            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ticket_status') THEN
                    CREATE TYPE ticket_status AS ENUM ('valid', 'cancelled', 'used');
                END IF;
            END$$;
            """,

            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status') THEN
                    CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded');
                END IF;
            END$$;
            """,

            # TABLES
            """
            CREATE TABLE IF NOT EXISTS cinemas (
                cinema_id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                city VARCHAR(255) NOT NULL
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS hall_types (
                hall_type_id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS halls (
                hall_id SERIAL PRIMARY KEY,
                cinema_id INT REFERENCES cinemas(cinema_id),
                hall_type_id INT REFERENCES hall_types(hall_type_id),
                name VARCHAR(100),
                capacity INT
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS seat_types (
                seat_type_id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS seats (
                seat_id SERIAL PRIMARY KEY,
                hall_id INT REFERENCES halls(hall_id),
                seat_type_id INT REFERENCES seat_types(seat_type_id),
                row_label VARCHAR(10),
                seat_number SMALLINT
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS movies (
                movie_id SERIAL PRIMARY KEY,
                title VARCHAR(255),
                duration_minutes SMALLINT
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS genres (
                genre_id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS movie_genres (
                movie_id INT REFERENCES movies(movie_id),
                genre_id INT REFERENCES genres(genre_id),
                PRIMARY KEY (movie_id, genre_id)
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS showtimes (
                showtime_id SERIAL PRIMARY KEY,
                movie_id INT REFERENCES movies(movie_id),
                hall_id INT REFERENCES halls(hall_id),
                start_datetime TIMESTAMP,
                base_price DECIMAL(10,2)
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE,
                username VARCHAR(100) UNIQUE
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS reservations (
                reservation_id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(user_id),
                showtime_id INT REFERENCES showtimes(showtime_id),
                status reservation_status
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS reservation_seats (
                reservation_seat_id SERIAL PRIMARY KEY,
                reservation_id INT REFERENCES reservations(reservation_id),
                seat_id INT REFERENCES seats(seat_id)
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS ticket_groups (
                ticket_group_id SERIAL PRIMARY KEY,
                group_name VARCHAR(100)
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS promotions (
                promotion_id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                discount_value DECIMAL(10,2)
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS promotion_rules (
                rule_id SERIAL PRIMARY KEY,
                promotion_id INT REFERENCES promotions(promotion_id)
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id SERIAL PRIMARY KEY,
                showtime_id INT REFERENCES showtimes(showtime_id),
                seat_id INT REFERENCES seats(seat_id),
                user_id INT REFERENCES users(user_id),
                reservation_id INT REFERENCES reservations(reservation_id),
                ticket_group_id INT REFERENCES ticket_groups(ticket_group_id),
                promotion_id INT REFERENCES promotions(promotion_id),
                final_price DECIMAL(10,2),
                status ticket_status
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS payment_methods (
                payment_method_id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS payments (
                payment_id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(user_id),
                payment_method_id INT REFERENCES payment_methods(payment_method_id),
                amount DECIMAL(10,2),
                status payment_status
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS ticket_payments (
                ticket_id INT REFERENCES tickets(ticket_id),
                payment_id INT REFERENCES payments(payment_id),
                amount DECIMAL(10,2),
                PRIMARY KEY (ticket_id, payment_id)
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS cancellation_policies (
                policy_id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE,
                refund_percent DECIMAL(5,2)
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS refunds (
                refund_id SERIAL PRIMARY KEY,
                ticket_id INT REFERENCES tickets(ticket_id),
                payment_id INT REFERENCES payments(payment_id),
                policy_id INT REFERENCES cancellation_policies(policy_id),
                refund_amount DECIMAL(10,2)
            );
            """
        ]

        with self.conn.cursor() as cur:
            for q in queries:
                cur.execute(q)

        self.conn.commit()
        print("Tabele zostały utworzone.")

    def close(self):
        self.conn.close()
