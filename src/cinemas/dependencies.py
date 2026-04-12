"""Cinemas domain dependencies."""
import logging
from fastapi import Depends, HTTPException, status

import psycopg

from src.database import get_db_connection
from src.exceptions import ResourceNotFoundException, DatabaseException, CinemaAPIException
from .schemas import Cinema
from .service import CinemaService

logger = logging.getLogger(__name__)


async def get_valid_cinema(cinema_id: int) -> Cinema:
    """Dependency: validate and get cinema by ID.
    
    Raises HTTPException 404 if not found.
    Raises HTTPException 500 if database error.
    """
    try:
        conn = await get_db_connection()
        try:
            return await CinemaService.get_cinema_by_id(conn, cinema_id)
        finally:
            await conn.close()
    except ResourceNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cinema with id {cinema_id} not found"
        )
    except DatabaseException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_valid_cinema: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
