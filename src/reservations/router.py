"""Reservations domain API endpoints."""
import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query

from src.config import AppConfig
from src.database import get_pool
from src.exceptions import (
    InsufficientAvailabilityException,
    ResourceNotFoundException,
    InvalidStateException,
    DatabaseException
)
from .schemas import Reservation, ReservationCreate, ReservationStatusUpdate
from .service import ReservationService
from .dependencies import get_valid_reservation

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f"{AppConfig.API_PREFIX}/reservations",
    tags=["Reservations"]
)


@router.post(
    "",
    response_model=Reservation,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new reservation"
)
async def create_reservation(reservation_data: ReservationCreate):
    """Create a new reservation for seats at a showtime."""
    pool = get_pool()
    try:
        async with pool.transaction() as ctx:
            # Cancel expired reservations first
            await ReservationService.cancel_expired_reservations(ctx.connection)
            
            # Create new reservation
            return await ReservationService.create_reservation(ctx.connection, reservation_data)
    except InsufficientAvailabilityException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating reservation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create reservation")


@router.get("/{reservation_id}", response_model=Reservation, summary="Get reservation by ID")
async def get_reservation(reservation: Reservation = Depends(get_valid_reservation)):
    """Get reservation by ID."""
    return reservation


@router.patch(
    "/{reservation_id}/status",
    response_model=Reservation,
    summary="Update reservation status"
)
async def update_reservation_status(
    reservation_id: int,
    status_update: ReservationStatusUpdate
):
    """Update reservation status (confirm or cancel)."""
    pool = get_pool()
    try:
        async with pool.transaction() as ctx:
            return await ReservationService.update_reservation_status(
                ctx.connection,
                reservation_id,
                status_update.status
            )
    except ResourceNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reservation {reservation_id} not found")
    except InvalidStateException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating reservation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Cancel reservation")
async def cancel_reservation(reservation_id: int):
    """Cancel a reservation (marks as cancelled)."""
    pool = get_pool()
    try:
        async with pool.transaction() as ctx:
            await ReservationService.update_reservation_status(ctx.connection, reservation_id, "cancelled")
    except ResourceNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reservation {reservation_id} not found")
    except Exception as e:
        logger.error(f"Error cancelling reservation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
