import logging
from typing import Optional

import psycopg

from src.exceptions import ResourceNotFoundException, DuplicateResourceException, DatabaseException, ValidationException
from .schemas import User, UserCreate

logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    async def create_user(conn, user_data: UserCreate) -> User:
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT user_id FROM users WHERE email = %s OR username = %s",
                    (user_data.email, user_data.username)
                )
                if await cur.fetchone():
                    raise DuplicateResourceException("User", "email or username", user_data.email)

                await cur.execute(
                    """INSERT INTO users (email, username) 
                       VALUES (%s, %s) 
                       RETURNING user_id, email, username, created_at""",
                    (user_data.email, user_data.username)
                )
                row = await cur.fetchone()
                if not row:
                    raise DatabaseException("Failed to create user")

                return User(user_id=row[0], email=row[1], username=row[2], created_at=row[3])
        except psycopg.Error as e:
            logger.error(f"Database error creating user: {e}")
            if "unique constraint" in str(e).lower():
                raise DuplicateResourceException("User", "email or username", user_data.email)
            raise DatabaseException(f"Failed to create user: {str(e)}")

    @staticmethod
    async def get_user_by_id(conn, user_id: int) -> User:
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT user_id, email, username, created_at FROM users WHERE user_id = %s",
                    (user_id,)
                )
                row = await cur.fetchone()
                if not row:
                    raise ResourceNotFoundException("User", user_id)

                return User(user_id=row[0], email=row[1], username=row[2], created_at=row[3])
        except psycopg.Error as e:
            logger.error(f"Database error fetching user: {e}")
            raise DatabaseException(f"Failed to fetch user: {str(e)}")

    @staticmethod
    async def get_user_by_email(conn, email: str) -> Optional[User]:
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT user_id, email, username, created_at FROM users WHERE email = %s",
                    (email,)
                )
                row = await cur.fetchone()
                if not row:
                    return None

                return User(user_id=row[0], email=row[1], username=row[2], created_at=row[3])
        except psycopg.Error as e:
            logger.error(f"Database error: {e}")
            raise DatabaseException(f"Failed to fetch user: {str(e)}")
