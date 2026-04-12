import logging
from typing import Optional, List

import psycopg
from psycopg import AsyncConnection

from src.exceptions import ResourceNotFoundException, DuplicateResourceException, DatabaseException
from src.config import Constants
from .schemas import Cinema, CinemaCreate

logger = logging.getLogger(__name__)


class CinemaService:
    @staticmethod
    async def create_cinema(
        conn: AsyncConnection,
        cinema_data: CinemaCreate
    ) -> Cinema:
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT cinema_id FROM cinemas WHERE name = %s AND city = %s",
                    (cinema_data.name, cinema_data.city)
                )
                if await cur.fetchone():
                    raise DuplicateResourceException("Cinema", "name+city", f"{cinema_data.name} in {cinema_data.city}")

                await cur.execute(
                    """INSERT INTO cinemas (name, city) 
                       VALUES (%s, %s) 
                       RETURNING cinema_id, name, city, created_at""",
                    (cinema_data.name, cinema_data.city)
                )
                row = await cur.fetchone()
                if not row:
                    raise DatabaseException("Failed to create cinema")

                return Cinema(
                    cinema_id=row[0],
                    name=row[1],
                    city=row[2],
                    created_at=row[3]
                )
        except psycopg.Error as e:
            logger.error(f"Database error creating cinema: {e}")
            raise DatabaseException(f"Failed to create cinema: {str(e)}")

    @staticmethod
    async def get_cinema_by_id(
        conn: AsyncConnection,
        cinema_id: int
    ) -> Cinema:
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT cinema_id, name, city, created_at FROM cinemas WHERE cinema_id = %s",
                    (cinema_id,)
                )
                row = await cur.fetchone()
                if not row:
                    raise ResourceNotFoundException("Cinema", cinema_id)

                return Cinema(
                    cinema_id=row[0],
                    name=row[1],
                    city=row[2],
                    created_at=row[3]
                )
        except psycopg.Error as e:
            logger.error(f"Database error fetching cinema: {e}")
            raise DatabaseException(f"Failed to fetch cinema: {str(e)}")

    @staticmethod
    async def list_cinemas(
        conn: AsyncConnection,
        skip: int = 0,
        limit: int = Constants.DEFAULT_LIMIT,
        city: Optional[str] = None
    ) -> tuple[int, List[Cinema]]:
        limit = min(limit, Constants.MAX_LIMIT)

        try:
            async with conn.cursor() as cur:
                if city:
                    await cur.execute("SELECT COUNT(*) FROM cinemas WHERE city = %s", (city,))
                else:
                    await cur.execute("SELECT COUNT(*) FROM cinemas")
                total = (await cur.fetchone())[0]

                query = "SELECT cinema_id, name, city, created_at FROM cinemas"
                params = []

                if city:
                    query += " WHERE city = %s"
                    params.append(city)

                query += " ORDER BY cinema_id OFFSET %s LIMIT %s"
                params.extend([skip, limit])

                await cur.execute(query, params)
                rows = await cur.fetchall()

                cinemas = [
                    Cinema(cinema_id=row[0], name=row[1], city=row[2], created_at=row[3])
                    for row in rows
                ]

                return total, cinemas
        except psycopg.Error as e:
            logger.error(f"Database error listing cinemas: {e}")
            raise DatabaseException(f"Failed to list cinemas: {str(e)}")
