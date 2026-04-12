"""Tickets domain service layer."""
import logging
from typing import List, Dict, Any
from decimal import Decimal

import psycopg

from src.exceptions import ResourceNotFoundException, DatabaseException, InsufficientAvailabilityException
from .schemas import Ticket, TicketCreate, ShowtimeSeatAvailability

logger = logging.getLogger(__name__)


class TicketService:
    """Service for ticket operations."""
    
    @staticmethod
    async def create_ticket(conn, ticket_data: TicketCreate) -> Ticket:
        """Create a ticket for a user at a showtime/seat."""
        try:
            async with conn.cursor() as cur:
                # Verify seat is available (no valid/used ticket for this showtime)
                await cur.execute(
                    """SELECT ticket_id FROM tickets 
                       WHERE showtime_id = %s AND seat_id = %s 
                       AND status IN ('valid', 'used')""",
                    (ticket_data.showtime_id, ticket_data.seat_id)
                )
                if await cur.fetchone():
                    raise InsufficientAvailabilityException(
                        f"Seat {ticket_data.seat_id} already has a valid ticket for this showtime"
                    )
                
                # Create ticket
                await cur.execute(
                    """INSERT INTO tickets (showtime_id, seat_id, user_id, final_price, status, reservation_id)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       RETURNING ticket_id, showtime_id, seat_id, user_id, final_price, status, created_at""",
                    (
                        ticket_data.showtime_id,
                        ticket_data.seat_id,
                        ticket_data.user_id,
                        ticket_data.final_price,
                        ticket_data.status,
                        ticket_data.reservation_id
                    )
                )
                row = await cur.fetchone()
                if not row:
                    raise DatabaseException("Failed to create ticket")
                
                return Ticket(
                    ticket_id=row[0],
                    showtime_id=row[1],
                    seat_id=row[2],
                    user_id=row[3],
                    final_price=row[4],
                    status=row[5],
                    created_at=row[6]
                )
        except (InsufficientAvailabilityException, DatabaseException):
            raise
        except psycopg.Error as e:
            logger.error(f"Database error creating ticket: {e}")
            raise DatabaseException(f"Failed to create ticket: {str(e)}")
    
    @staticmethod
    async def get_showtime_seat_availability(
        conn,
        showtime_id: int
    ) -> List[ShowtimeSeatAvailability]:
        """Get all seats for a showtime with availability and pricing."""
        try:
            async with conn.cursor() as cur:
                query = """
                    SELECT 
                        s.seat_id,
                        s.row_label,
                        s.seat_number,
                        st.name as seat_type,
                        CASE WHEN t.ticket_id IS NULL AND r.reservation_id IS NULL THEN true ELSE false END as is_available,
                        sh.base_price
                    FROM showtimes sh
                    JOIN halls h ON sh.hall_id = h.hall_id
                    JOIN seats s ON s.hall_id = h.hall_id
                    LEFT JOIN seat_types st ON s.seat_type_id = st.seat_type_id
                    LEFT JOIN tickets t ON t.showtime_id = sh.showtime_id AND t.seat_id = s.seat_id AND t.status IN ('valid', 'used')
                    LEFT JOIN reservations r ON r.showtime_id = sh.showtime_id AND r.status = 'pending'
                    LEFT JOIN reservation_seats rs ON r.reservation_id = rs.reservation_id AND rs.seat_id = s.seat_id
                    WHERE sh.showtime_id = %s
                    ORDER BY s.row_label, s.seat_number
                """
                
                await cur.execute(query, (showtime_id,))
                rows = await cur.fetchall()
                
                return [
                    ShowtimeSeatAvailability(
                        seat_id=row[0],
                        row_label=row[1],
                        seat_number=row[2],
                        seat_type=row[3] or "standard",
                        is_available=row[4],
                        base_price=Decimal(str(row[5])) if row[5] else None
                    )
                    for row in rows
                ]
        except psycopg.Error as e:
            logger.error(f"Error getting seat availability: {e}")
            raise DatabaseException(f"Failed to get seat availability: {str(e)}")
    
    @staticmethod
    async def get_ticket_by_id(conn, ticket_id: int) -> Ticket:
        """Get ticket by ID."""
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT ticket_id, showtime_id, seat_id, user_id, final_price, status, created_at
                       FROM tickets WHERE ticket_id = %s""",
                    (ticket_id,)
                )
                row = await cur.fetchone()
                if not row:
                    raise ResourceNotFoundException("Ticket", ticket_id)
                
                return Ticket(
                    ticket_id=row[0],
                    showtime_id=row[1],
                    seat_id=row[2],
                    user_id=row[3],
                    final_price=row[4],
                    status=row[5],
                    created_at=row[6]
                )
        except psycopg.Error as e:
            logger.error(f"Error fetching ticket: {e}")
            raise DatabaseException(f"Failed to fetch ticket: {str(e)}")
