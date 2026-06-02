import logging
from fastapi import Depends, HTTPException, status

import psycopg

from src.database import get_pool
from src.exceptions import ResourceNotFoundException, DatabaseException, CinemaAPIException
from .schemas import Cinema
from .service import CinemaService

logger = logging.getLogger(__name__)


async def get_valid_cinema(cinema_id: int) -> Cinema:
    try:
        async with get_pool().acquire() as conn:
            return await CinemaService.get_cinema_by_id(conn, cinema_id)
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
