"""Tickets domain API endpoints."""
import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query

from src.config import AppConfig
from src.database import get_pool
from src.exceptions import InsufficientAvailabilityException, ResourceNotFoundException, DatabaseException
from .schemas import Ticket, TicketCreate, ShowtimeSeatAvailability
from .service import TicketService
from .dependencies import get_valid_ticket

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f"{AppConfig.API_PREFIX}/tickets",
    tags=["Tickets"]
)


@router.post(
    "",
    response_model=Ticket,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ticket"
)
async def create_ticket(ticket_data: TicketCreate):
    """Create a new ticket for a user."""
    pool = get_pool()
    try:
        async with pool.transaction() as ctx:
            return await TicketService.create_ticket(ctx.connection, ticket_data)
    except InsufficientAvailabilityException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{ticket_id}", response_model=Ticket, summary="Get ticket by ID")
async def get_ticket(ticket: Ticket = Depends(get_valid_ticket)):
    """Get ticket by ID."""
    return ticket


@router.get(
    "/showtime/{showtime_id}/seats",
    response_model=list[ShowtimeSeatAvailability],
    summary="Get seat availability for a showtime"
)
async def get_showtime_seats(showtime_id: int):
    """Get all seats for a showtime with availability status."""
    pool = get_pool()
    try:
        async with pool.acquire() as conn:
            return await TicketService.get_showtime_seat_availability(conn, showtime_id)
    except Exception as e:
        logger.error(f"Error getting showtime seats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
