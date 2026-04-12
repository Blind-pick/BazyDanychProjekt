"""Reservations domain dependencies."""
import logging
from fastapi import HTTPException, status

from src.database import get_db_connection
from src.exceptions import ResourceNotFoundException, DatabaseException
from .schemas import Reservation
from .service import ReservationService

logger = logging.getLogger(__name__)


async def get_valid_reservation(reservation_id: int) -> Reservation:
    """Dependency: validate and get reservation by ID."""
    try:
        conn = await get_db_connection()
        try:
            return await ReservationService.get_reservation_by_id(conn, reservation_id)
        finally:
            await conn.close()
    except ResourceNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reservation {reservation_id} not found")
    except Exception as e:
        logger.error(f"Error in get_valid_reservation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
