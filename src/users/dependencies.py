"""Users domain dependencies."""
import logging
from fastapi import Depends, HTTPException, status

from src.database import get_db_connection
from src.exceptions import ResourceNotFoundException, DatabaseException
from .schemas import User
from .service import UserService

logger = logging.getLogger(__name__)


async def get_valid_user(user_id: int) -> User:
    """Dependency: validate and get user by ID."""
    try:
        conn = await get_db_connection()
        try:
            return await UserService.get_user_by_id(conn, user_id)
        finally:
            await conn.close()
    except ResourceNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    except Exception as e:
        logger.error(f"Error in get_valid_user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
