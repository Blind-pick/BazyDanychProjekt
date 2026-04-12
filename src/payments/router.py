"""Payments domain API endpoints."""
import logging
from fastapi import APIRouter, HTTPException, status, Depends

from src.config import AppConfig
from src.database import get_pool
from src.exceptions import ResourceNotFoundException, DatabaseException
from .schemas import Payment, PaymentCreate, Refund, RefundCreate
from .service import PaymentService
from .dependencies import get_valid_payment

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f"{AppConfig.API_PREFIX}/payments",
    tags=["Payments"]
)


@router.post("", response_model=Payment, status_code=status.HTTP_201_CREATED, summary="Create payment")
async def create_payment(payment_data: PaymentCreate):
    """Create a payment record."""
    pool = get_pool()
    try:
        async with pool.transaction() as ctx:
            return await PaymentService.create_payment(ctx.connection, payment_data)
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{payment_id}", response_model=Payment, summary="Get payment by ID")
async def get_payment(payment: Payment = Depends(get_valid_payment)):
    """Get payment by ID."""
    return payment


@router.post(
    "/{payment_id}/complete",
    response_model=Payment,
    summary="Mark payment as completed"
)
async def complete_payment(payment_id: int):
    """Mark a payment as completed."""
    pool = get_pool()
    try:
        async with pool.transaction() as ctx:
            return await PaymentService.mark_payment_completed(ctx.connection, payment_id)
    except ResourceNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment {payment_id} not found")
    except Exception as e:
        logger.error(f"Error completing payment: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/refunds", response_model=Refund, status_code=status.HTTP_201_CREATED, summary="Create refund")
async def create_refund(refund_data: RefundCreate):
    """Create a refund for a ticket."""
    pool = get_pool()
    try:
        async with pool.transaction() as ctx:
            return await PaymentService.create_refund(ctx.connection, refund_data)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating refund: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
