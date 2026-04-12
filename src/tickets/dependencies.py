"""Tickets domain dependencies."""
from fastapi import HTTPException, status

from src.database import get_db_connection
from src.exceptions import ResourceNotFoundException, DatabaseException
from .schemas import Ticket
from .service import TicketService


async def get_valid_ticket(ticket_id: int) -> Ticket:
    """Dependency: validate and get ticket by ID."""
    try:
        conn = await get_db_connection()
        try:
            return await TicketService.get_ticket_by_id(conn, ticket_id)
        finally:
            await conn.close()
    except ResourceNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket {ticket_id} not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
