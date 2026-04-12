"""Script to load sample data into cinema database."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import psycopg

from src.config import DatabaseConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def load_sample_data():
    """Load comprehensive sample data for testing."""
    conn = await psycopg.AsyncConnection.connect(DatabaseConfig.get_connection_string())
    
    try:
        async with conn.cursor() as cur:
            logger.info("Loading sample data...")
            
            # Insert cinema
            await cur.execute(
                "INSERT INTO cinemas (name, city) VALUES (%s, %s) RETURNING cinema_id",
                ("Cinema City Warszawa", "Warszawa")
            )
            cinema_id = (await cur.fetchone())[0]
            logger.info(f"Created cinema: {cinema_id}")
            
            # Insert hall type and hall
            await cur.execute(
                "SELECT hall_type_id FROM hall_types WHERE name = 'Standard 2D' LIMIT 1"
            )
            hall_type_id = (await cur.fetchone())[0]
            
            await cur.execute(
                "INSERT INTO halls (cinema_id, hall_type_id, name, capacity) VALUES (%s, %s, %s, %s) RETURNING hall_id",
                (cinema_id, hall_type_id, "Sala 1", 80)
            )
            hall_id = (await cur.fetchone())[0]
            logger.info(f"Created hall: {hall_id}")
            
            # Create seats (8 rows x 10 seats = 80)
            await cur.execute("SELECT seat_type_id FROM seat_types WHERE name = 'Standard' LIMIT 1")
            seat_type_id = (await cur.fetchone())[0]
            
            row_labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
            seat_count = 0
            for row in row_labels:
                for seat_num in range(1, 11):
                    await cur.execute(
                        "INSERT INTO seats (hall_id, seat_type_id, row_label, seat_number) VALUES (%s, %s, %s, %s)",
                        (hall_id, seat_type_id, row, seat_num)
                    )
                    seat_count += 1
            logger.info(f"Created {seat_count} seats")
            
            # Create movies
            movies = [
                ("Oppenheimer", 180),
                ("Killers of the Flower Moon", 206),
                ("Barbie", 114),
            ]
            movie_ids = []
            
            for title, duration in movies:
                await cur.execute(
                    "INSERT INTO movies (title, duration_minutes) VALUES (%s, %s) RETURNING movie_id",
                    (title, duration)
                )
                movie_ids.append((await cur.fetchone())[0])
            logger.info(f"Created {len(movie_ids)} movies")
            
            # Create showtimes
            now = datetime.now(timezone.utc)
            showtime_ids = []
            times = [
                now + timedelta(hours=1),
                now + timedelta(hours=4),
                now + timedelta(hours=8),
                now + timedelta(days=1, hours=2),
            ]
            
            for movie_id in movie_ids:
                for showtime in times:
                    await cur.execute(
                        "INSERT INTO showtimes (movie_id, hall_id, start_datetime, base_price) VALUES (%s, %s, %s, %s) RETURNING showtime_id",
                        (movie_id, hall_id, showtime, 29.99)
                    )
                    showtime_ids.append((await cur.fetchone())[0])
            logger.info(f"Created {len(showtime_ids)} showtimes")
            
            # Create test users
            await cur.execute(
                "INSERT INTO users (email, username) VALUES (%s, %s) RETURNING user_id",
                ("testuser1@example.com", "testuser1")
            )
            user_id = (await cur.fetchone())[0]
            logger.info(f"Created user: {user_id}")
            
            # Create a sample reservation
            await cur.execute(
                "INSERT INTO reservations (user_id, showtime_id, status) VALUES (%s, %s, 'pending') RETURNING reservation_id",
                (user_id, showtime_ids[0])
            )
            reservation_id = (await cur.fetchone())[0]
            
            # Get some seats for the reservation
            await cur.execute(
                "SELECT seat_id FROM seats WHERE hall_id = %s LIMIT 3",
                (hall_id,)
            )
            seat_ids = [row[0] for row in await cur.fetchall()]
            
            for seat_id in seat_ids:
                await cur.execute(
                    "INSERT INTO reservation_seats (reservation_id, seat_id) VALUES (%s, %s)",
                    (reservation_id, seat_id)
                )
            logger.info(f"Created reservation {reservation_id} with {len(seat_ids)} seats")
            
            await conn.commit()
            logger.info("Sample data loaded successfully!")
    
    except Exception as e:
        logger.error(f"Error loading sample data: {e}")
        await conn.rollback()
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(load_sample_data())
