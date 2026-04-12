"""Payments domain service layer."""
import logging
from typing import List
from decimal import Decimal

import psycopg

from src.exceptions import ResourceNotFoundException, DatabaseException, InvalidStateException
from .schemas import Payment, PaymentCreate, Refund, RefundCreate, PaymentMethod

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for payment operations."""
    
    @staticmethod
    async def create_payment(conn, payment_data: PaymentCreate) -> Payment:
        """Create a payment record."""
        try:
            async with conn.cursor() as cur:
                # Create payment
                await cur.execute(
                    """INSERT INTO payments (user_id, payment_method_id, amount, status)
                       VALUES (%s, %s, %s, %s)
                       RETURNING payment_id, user_id, payment_method_id, amount, status, created_at""",
                    (
                        payment_data.user_id,
                        payment_data.payment_method_id,
                        payment_data.amount,
                        payment_data.status
                    )
                )
                row = await cur.fetchone()
                if not row:
                    raise DatabaseException("Failed to create payment")
                
                payment_id = row[0]
                
                # Associate with tickets
                for ticket_id in payment_data.ticket_ids:
                    await cur.execute(
                        """INSERT INTO ticket_payments (ticket_id, payment_id, amount)
                           VALUES (%s, %s, %s)""",
                        (ticket_id, payment_id, payment_data.amount)
                    )
                
                return Payment(
                    payment_id=row[0],
                    user_id=row[1],
                    payment_method_id=row[2],
                    amount=row[3],
                    status=row[4],
                    created_at=row[5]
                )
        except psycopg.Error as e:
            logger.error(f"Database error creating payment: {e}")
            raise DatabaseException(f"Failed to create payment: {str(e)}")
    
    @staticmethod
    async def get_payment_by_id(conn, payment_id: int) -> Payment:
        """Get payment by ID."""
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT payment_id, user_id, payment_method_id, amount, status, created_at
                       FROM payments WHERE payment_id = %s""",
                    (payment_id,)
                )
                row = await cur.fetchone()
                if not row:
                    raise ResourceNotFoundException("Payment", payment_id)
                
                return Payment(
                    payment_id=row[0],
                    user_id=row[1],
                    payment_method_id=row[2],
                    amount=row[3],
                    status=row[4],
                    created_at=row[5]
                )
        except psycopg.Error as e:
            logger.error(f"Error fetching payment: {e}")
            raise DatabaseException(f"Failed to fetch payment: {str(e)}")
    
    @staticmethod
    async def mark_payment_completed(conn, payment_id: int) -> Payment:
        """Mark payment as completed."""
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE payments SET status = 'completed' WHERE payment_id = %s",
                    (payment_id,)
                )
                return await PaymentService.get_payment_by_id(conn, payment_id)
        except psycopg.Error as e:
            logger.error(f"Error updating payment: {e}")
            raise DatabaseException(f"Failed to update payment: {str(e)}")
    
    @staticmethod
    async def create_refund(conn, refund_data: RefundCreate) -> Refund:
        """Create a refund for a ticket."""
        try:
            async with conn.cursor() as cur:
                # Get ticket and payment info
                await cur.execute(
                    """SELECT t.user_id, t.final_price, t.status, tp.payment_id
                       FROM tickets t
                       LEFT JOIN ticket_payments tp ON t.ticket_id = tp.ticket_id
                       WHERE t.ticket_id = %s""",
                    (refund_data.ticket_id,)
                )
                row = await cur.fetchone()
                if not row:
                    raise ResourceNotFoundException("Ticket", refund_data.ticket_id)
                
                payment_id = row[3]
                ticket_final_price = Decimal(str(row[1]))
                
                # Get refund policy
                await cur.execute(
                    "SELECT refund_percent FROM cancellation_policies WHERE policy_id = %s",
                    (refund_data.policy_id,)
                )
                policy_row = await cur.fetchone()
                if not policy_row:
                    raise ResourceNotFoundException("Policy", refund_data.policy_id)
                
                refund_percent = Decimal(str(policy_row[0]))
                refund_amount = (ticket_final_price * refund_percent) / 100
                
                # Create refund
                await cur.execute(
                    """INSERT INTO refunds (ticket_id, payment_id, policy_id, refund_amount)
                       VALUES (%s, %s, %s, %s)
                       RETURNING refund_id, ticket_id, payment_id, policy_id, refund_amount, created_at""",
                    (refund_data.ticket_id, payment_id, refund_data.policy_id, refund_amount)
                )
                refund_row = await cur.fetchone()
                if not refund_row:
                    raise DatabaseException("Failed to create refund")
                
                # Mark ticket as cancelled
                await cur.execute(
                    "UPDATE tickets SET status = 'cancelled' WHERE ticket_id = %s",
                    (refund_data.ticket_id,)
                )
                
                # Mark payment as refunded
                if payment_id:
                    await cur.execute(
                        "UPDATE payments SET status = 'refunded' WHERE payment_id = %s",
                        (payment_id,)
                    )
                
                return Refund(
                    refund_id=refund_row[0],
                    ticket_id=refund_row[1],
                    payment_id=refund_row[2] or 0,
                    policy_id=refund_row[3],
                    refund_amount=refund_row[4],
                    created_at=refund_row[5]
                )
        except (ResourceNotFoundException, DatabaseException):
            raise
        except psycopg.Error as e:
            logger.error(f"Error creating refund: {e}")
            raise DatabaseException(f"Failed to create refund: {str(e)}")
