"""Payments domain dependencies."""
from fastapi import HTTPException, status

from src.database import get_db_connection
from src.exceptions import ResourceNotFoundException
from .schemas import Payment
from .service import PaymentService


async def get_valid_payment(payment_id: int) -> Payment:
    """Dependency: validate and get payment by ID."""
    try:
        conn = await get_db_connection()
        try:
            return await PaymentService.get_payment_by_id(conn, payment_id)
        finally:
            await conn.close()
    except ResourceNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment {payment_id} not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
