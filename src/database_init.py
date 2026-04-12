"""Database creator and initializer with proper schema."""
import psycopg
import logging
from contextlib import asynccontextmanager

from src.config import DatabaseConfig

logger = logging.getLogger(__name__)


class CinemaDatabaseInitializer:
    """Initializes cinema database schema with proper constraints and indexes."""
    
    def __init__(self, host: str, dbname: str, user: str, password: str, port: int = 5432):
        """Initialize database credentials."""
        self.host = host
        self.dbname = dbname
        self.user = user
        self.password = password
        self.port = port
        self.conn = None
    
    def _create_database_if_not_exists(self) -> None:
        """Create database if it doesn't exist (connects to postgres db)."""
        try:
            admin_conn = psycopg.connect(
                host=self.host,
                dbname="postgres",
                user=self.user,
                password=self.password,
                port=self.port
            )
            admin_conn.autocommit = True
            
            with admin_conn.cursor() as cur:
                cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (self.dbname,))
                if not cur.fetchone():
                    cur.execute(f"CREATE DATABASE {self.dbname}")
                    logger.info(f"Created database '{self.dbname}'")
                else:
                    logger.info(f"Database '{self.dbname}' already exists")
            
            admin_conn.close()
        except psycopg.Error as e:
            logger.error(f"Error creating database: {e}")
            raise
    
    def connect(self) -> None:
        """Connect to the cinema database."""
        try:
            self.conn = psycopg.connect(
                host=self.host,
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                port=self.port
            )
            logger.info(f"Connected to database '{self.dbname}'")
        except psycopg.Error as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def create_schema(self) -> None:
        """Create all tables with proper constraints, indexes, and isolation levels."""
        if not self.conn:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        queries = [
            # Create ENUM types
            """DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reservation_status') THEN
                    CREATE TYPE reservation_status AS ENUM ('pending', 'confirmed', 'cancelled');
                END IF;
            END$$;""",
            
            """DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ticket_status') THEN
                    CREATE TYPE ticket_status AS ENUM ('valid', 'cancelled', 'used');
                END IF;
            END$$;""",
            
            """DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status') THEN
                    CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded');
                END IF;
            END$$;""",
            
            # Core tables
            """CREATE TABLE IF NOT EXISTS cinemas (
                cinema_id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                city VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_cinema_name_city UNIQUE (name, city)
            );
            CREATE INDEX IF NOT EXISTS idx_cinemas_city ON cinemas(city);""",
            
            """CREATE TABLE IF NOT EXISTS hall_types (
                hall_type_id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            
            """CREATE TABLE IF NOT EXISTS halls (
                hall_id SERIAL PRIMARY KEY,
                cinema_id INT NOT NULL REFERENCES cinemas(cinema_id) ON DELETE CASCADE,
                hall_type_id INT NOT NULL REFERENCES hall_types(hall_type_id),
                name VARCHAR(100) NOT NULL,
                capacity INT NOT NULL CHECK (capacity > 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_hall_name_per_cinema UNIQUE (cinema_id, name)
            );
            CREATE INDEX IF NOT EXISTS idx_halls_cinema_id ON halls(cinema_id);""",
            
            """CREATE TABLE IF NOT EXISTS seat_types (
                seat_type_id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            
            """CREATE TABLE IF NOT EXISTS seats (
                seat_id SERIAL PRIMARY KEY,
                hall_id INT NOT NULL REFERENCES halls(hall_id) ON DELETE CASCADE,
                seat_type_id INT REFERENCES seat_types(seat_type_id),
                row_label VARCHAR(10) NOT NULL,
                seat_number SMALLINT NOT NULL CHECK (seat_number > 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_seat_per_hall UNIQUE (hall_id, row_label, seat_number)
            );
            CREATE INDEX IF NOT EXISTS idx_seats_hall_id ON seats(hall_id);""",
            
            """CREATE TABLE IF NOT EXISTS movies (
                movie_id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                duration_minutes SMALLINT NOT NULL CHECK (duration_minutes > 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            
            """CREATE TABLE IF NOT EXISTS genres (
                genre_id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            
            """CREATE TABLE IF NOT EXISTS movie_genres (
                movie_id INT NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
                genre_id INT NOT NULL REFERENCES genres(genre_id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (movie_id, genre_id)
            );""",
            
            """CREATE TABLE IF NOT EXISTS showtimes (
                showtime_id SERIAL PRIMARY KEY,
                movie_id INT NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
                hall_id INT NOT NULL REFERENCES halls(hall_id) ON DELETE CASCADE,
                start_datetime TIMESTAMP NOT NULL,
                base_price NUMERIC(10,2) NOT NULL CHECK (base_price >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT future_showtime CHECK (start_datetime > CURRENT_TIMESTAMP)
            );
            CREATE INDEX IF NOT EXISTS idx_showtimes_movie_id ON showtimes(movie_id);
            CREATE INDEX IF NOT EXISTS idx_showtimes_hall_id ON showtimes(hall_id);
            CREATE INDEX IF NOT EXISTS idx_showtimes_start_datetime ON showtimes(start_datetime);""",
            
            """CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);""",
            
            """CREATE TABLE IF NOT EXISTS reservations (
                reservation_id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                showtime_id INT NOT NULL REFERENCES showtimes(showtime_id) ON DELETE CASCADE,
                status reservation_status NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT reservation_not_expired CHECK (created_at + INTERVAL '15 minutes' > CURRENT_TIMESTAMP OR status != 'pending')
            );
            CREATE INDEX IF NOT EXISTS idx_reservations_user_id ON reservations(user_id);
            CREATE INDEX IF NOT EXISTS idx_reservations_showtime_id ON reservations(showtime_id);
            CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status);""",
            
            """CREATE TABLE IF NOT EXISTS reservation_seats (
                reservation_seat_id SERIAL PRIMARY KEY,
                reservation_id INT NOT NULL REFERENCES reservations(reservation_id) ON DELETE CASCADE,
                seat_id INT NOT NULL REFERENCES seats(seat_id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_seat_per_reservation UNIQUE (reservation_id, seat_id)
            );
            CREATE INDEX IF NOT EXISTS idx_reservation_seats_reservation_id ON reservation_seats(reservation_id);""",
            
            """CREATE TABLE IF NOT EXISTS ticket_groups (
                ticket_group_id SERIAL PRIMARY KEY,
                group_name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            
            """CREATE TABLE IF NOT EXISTS promotions (
                promotion_id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                discount_value NUMERIC(10,2) NOT NULL CHECK (discount_value >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            
            """CREATE TABLE IF NOT EXISTS payment_methods (
                payment_method_id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            
            """CREATE TABLE IF NOT EXISTS tickets (
                ticket_id SERIAL PRIMARY KEY,
                showtime_id INT NOT NULL REFERENCES showtimes(showtime_id) ON DELETE CASCADE,
                seat_id INT NOT NULL REFERENCES seats(seat_id) ON DELETE CASCADE,
                user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                reservation_id INT REFERENCES reservations(reservation_id) ON DELETE SET NULL,
                ticket_group_id INT REFERENCES ticket_groups(ticket_group_id),
                promotion_id INT REFERENCES promotions(promotion_id),
                final_price NUMERIC(10,2) NOT NULL CHECK (final_price >= 0),
                status ticket_status NOT NULL DEFAULT 'valid',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_ticket_per_seat_showtime UNIQUE (showtime_id, seat_id)
            );
            CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id);
            CREATE INDEX IF NOT EXISTS idx_tickets_showtime_id ON tickets(showtime_id);
            CREATE INDEX IF NOT EXISTS idx_tickets_seat_id ON tickets(seat_id);
            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);""",
            
            """CREATE TABLE IF NOT EXISTS payments (
                payment_id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                payment_method_id INT NOT NULL REFERENCES payment_methods(payment_method_id),
                amount NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
                status payment_status NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
            CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);""",
            
            """CREATE TABLE IF NOT EXISTS ticket_payments (
                ticket_id INT NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
                payment_id INT NOT NULL REFERENCES payments(payment_id) ON DELETE CASCADE,
                amount NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ticket_id, payment_id)
            );
            CREATE INDEX IF NOT EXISTS idx_ticket_payments_payment_id ON ticket_payments(payment_id);""",
            
            """CREATE TABLE IF NOT EXISTS cancellation_policies (
                policy_id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                refund_percent NUMERIC(5,2) NOT NULL CHECK (refund_percent >= 0 AND refund_percent <= 100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            
            """CREATE TABLE IF NOT EXISTS refunds (
                refund_id SERIAL PRIMARY KEY,
                ticket_id INT NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
                payment_id INT REFERENCES payments(payment_id) ON DELETE SET NULL,
                policy_id INT NOT NULL REFERENCES cancellation_policies(policy_id),
                refund_amount NUMERIC(10,2) NOT NULL CHECK (refund_amount >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_refunds_ticket_id ON refunds(ticket_id);
            CREATE INDEX IF NOT EXISTS idx_refunds_payment_id ON refunds(payment_id);""",
        ]
        
        try:
            with self.conn.cursor() as cur:
                for query in queries:
                    cur.execute(query)
            self.conn.commit()
            logger.info("Database schema created successfully")
        except psycopg.Error as e:
            logger.error(f"Error creating schema: {e}")
            self.conn.rollback()
            raise
    
    def load_seed_data(self) -> None:
        """Load initial seed data (hall types, seat types, payment methods, policies)."""
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        seed_queries = [
            # Hall types
            """INSERT INTO hall_types (name) VALUES
                ('Standard 2D') ON CONFLICT (name) DO NOTHING;""",
            
            # Seat types
            """INSERT INTO seat_types (name) VALUES
                ('Standard'), ('VIP'), ('Wheelchair Accessible') 
                ON CONFLICT (name) DO NOTHING;""",
            
            # Payment methods
            """INSERT INTO payment_methods (name) VALUES
                ('Credit Card'), ('Debit Card'), ('PayPal'), ('Cash')
                ON CONFLICT (name) DO NOTHING;""",
            
            # Cancellation policies
            """INSERT INTO cancellation_policies (name, refund_percent) VALUES
                ('Full Refund', 100), ('50% Refund', 50), ('No Refund', 0)
                ON CONFLICT (name) DO NOTHING;""",
        ]
        
        try:
            with self.conn.cursor() as cur:
                for query in seed_queries:
                    cur.execute(query)
            self.conn.commit()
            logger.info("Seed data loaded successfully")
        except psycopg.Error as e:
            logger.error(f"Error loading seed data: {e}")
            self.conn.rollback()
            raise
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


async def initialize_database() -> None:
    """Initialize database synchronously (creates schema if needed)."""
    initializer = CinemaDatabaseInitializer(
        host=DatabaseConfig.HOST,
        dbname=DatabaseConfig.NAME,
        user=DatabaseConfig.USER,
        password=DatabaseConfig.PASSWORD,
        port=DatabaseConfig.PORT
    )
    
    try:
        initializer._create_database_if_not_exists()
        initializer.connect()
        initializer.create_schema()
        initializer.load_seed_data()
    finally:
        initializer.close()
