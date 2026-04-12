"""Reservations domain service layer."""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional

import psycopg

from src.config import AppConfig
from src.exceptions import (
    ResourceNotFoundException,
    InsufficientAvailabilityException,
    InvalidStateException,
    DatabaseException,
    ConflictException
)
from .schemas import Reservation, ReservationCreate

logger = logging.getLogger(__name__)


class ReservationService:
    """Service for reservation operations."""
    
    @staticmethod
    async def cancel_expired_reservations(conn) -> int:
        """Cancel expired pending reservations. Returns count of cancelled."""
        timeout_threshold = datetime.now(timezone.utc) - timedelta(
            minutes=AppConfig.RESERVATION_TIMEOUT_MINUTES
        )
        
        async with conn.cursor() as cur:
            await cur.execute(
                """UPDATE reservations 
                   SET status = 'cancelled' 
                   WHERE status = 'pending' AND created_at < %s
                   RETURNING reservation_id""",
                (timeout_threshold,)
            )
            return len(await cur.fetchall())
    
    @staticmethod
    async def check_seat_availability(
        conn,
        showtime_id: int,
        seat_ids: List[int]
    ) -> Tuple[bool, List[int]]:
        """Check if seats are available for showtime.
        
        Returns (all_available, unavailable_seat_ids)
        """
        if not seat_ids:
            raise ValueError("No seats specified")
        
        try:
            async with conn.cursor() as cur:
                placeholders = ",".join(["%s"] * len(seat_ids))
                await cur.execute(
                    f"""SELECT seat_id FROM seats s
                        WHERE s.seat_id IN ({placeholders})
                        AND EXISTS (
                            SELECT 1 FROM tickets t
                            WHERE t.showtime_id = %s AND t.seat_id = s.seat_id
                            AND t.status != 'cancelled'
                        )""",
                    seat_ids + [showtime_id]
                )
                unavailable = [row[0] for row in await cur.fetchall()]
                return len(unavailable) == 0, unavailable
        except psycopg.Error as e:
            logger.error(f"Error checking seat availability: {e}")
            raise DatabaseException(f"Failed to check seat availability: {str(e)}")
    
    @staticmethod
    async def create_reservation(
        conn,
        reservation_data: ReservationCreate
    ) -> Reservation:
        """Create a new reservation. Returns Reservation object.
        
        Raises:
        - InsufficientAvailabilityException if seats not available
        - ResourceNotFoundException if showtime or seats not found
        """
        try:
            async with conn.cursor() as cur:
                # Verify showtime exists
                await cur.execute("SELECT showtime_id FROM showtimes WHERE showtime_id = %s", (reservation_data.showtime_id,))
                if not await cur.fetchone():
                    raise ResourceNotFoundException("Showtime", reservation_data.showtime_id)
                
                # Verify all seats exist
                placeholders = ",".join(["%s"] * len(reservation_data.seat_ids))
                await cur.execute(
                    f"SELECT COUNT(*) FROM seats WHERE seat_id IN ({placeholders})",
                    reservation_data.seat_ids
                )
                if (await cur.fetchone())[0] != len(reservation_data.seat_ids):
                    raise ResourceNotFoundException("One or more seats", "specified")
                
                # Check seat availability (for this showtime, non-cancelled tickets)
                available, unavailable = await ReservationService.check_seat_availability(
                    conn,
                    reservation_data.showtime_id,
                    reservation_data.seat_ids
                )
                
                if not available:
                    raise InsufficientAvailabilityException(
                        f"Seats {unavailable} not available for this showtime"
                    )
                
                # Create reservation
                await cur.execute(
                    """INSERT INTO reservations (user_id, showtime_id, status)
                       VALUES (%s, %s, 'pending')
                       RETURNING reservation_id, user_id, showtime_id, status, created_at""",
                    (reservation_data.user_id, reservation_data.showtime_id)
                )
                row = await cur.fetchone()
                reservation_id = row[0]
                
                # Add seats to reservation
                for seat_id in reservation_data.seat_ids:
                    await cur.execute(
                        "INSERT INTO reservation_seats (reservation_id, seat_id) VALUES (%s, %s)",
                        (reservation_id, seat_id)
                    )
                
                return Reservation(
                    reservation_id=row[0],
                    user_id=row[1],
                    showtime_id=row[2],
                    status=row[3],
                    seat_ids=reservation_data.seat_ids,
                    created_at=row[4]
                )
        except (InsufficientAvailabilityException, ResourceNotFoundException):
            raise
        except psycopg.Error as e:
            logger.error(f"Database error creating reservation: {e}")
            raise DatabaseException(f"Failed to create reservation: {str(e)}")
    
    @staticmethod
    async def get_reservation_by_id(conn, reservation_id: int) -> Reservation:
        """Get reservation by ID with seat_ids."""
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT reservation_id, user_id, showtime_id, status, created_at FROM reservations WHERE reservation_id = %s",
                    (reservation_id,)
                )
                row = await cur.fetchone()
                if not row:
                    raise ResourceNotFoundException("Reservation", reservation_id)
                
                # Get seat IDs
                await cur.execute(
                    "SELECT seat_id FROM reservation_seats WHERE reservation_id = %s",
                    (reservation_id,)
                )
                seat_ids = [r[0] for r in await cur.fetchall()]
                
                return Reservation(
                    reservation_id=row[0],
                    user_id=row[1],
                    showtime_id=row[2],
                    status=row[3],
                    seat_ids=seat_ids,
                    created_at=row[4]
                )
        except psycopg.Error as e:
            logger.error(f"Error fetching reservation: {e}")
            raise DatabaseException(f"Failed to fetch reservation: {str(e)}")
    
    @staticmethod
    async def update_reservation_status(
        conn,
        reservation_id: int,
        new_status: str
    ) -> Reservation:
        """Update reservation status. Validates state transitions."""
        valid_statuses = {"pending", "confirmed", "cancelled"}
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}")
        
        try:
            async with conn.cursor() as cur:
                # Get current reservation
                await cur.execute(
                    "SELECT status FROM reservations WHERE reservation_id = %s",
                    (reservation_id,)
                )
                row = await cur.fetchone()
                if not row:
                    raise ResourceNotFoundException("Reservation", reservation_id)
                
                current_status = row[0]
                
                # Validate state transition
                if current_status == "cancelled":
                    raise InvalidStateException("Cannot update cancelled reservation")
                
                # Update status
                await cur.execute(
                    "UPDATE reservations SET status = %s WHERE reservation_id = %s",
                    (new_status, reservation_id)
                )
                
                # Return updated reservation
                return await ReservationService.get_reservation_by_id(conn, reservation_id)
        except (InvalidStateException, ResourceNotFoundException):
            raise
        except psycopg.Error as e:
            logger.error(f"Error updating reservation: {e}")
            raise DatabaseException(f"Failed to update reservation: {str(e)}")
