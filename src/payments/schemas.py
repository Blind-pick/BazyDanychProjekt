"""Payments domain schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class PaymentMethodBase(BaseModel):
    """Base schema for payment method."""
    name: str = Field(..., min_length=1, max_length=100, description="Payment method name")


class PaymentMethod(PaymentMethodBase):
    """Schema for payment method response."""
    payment_method_id: int
    
    class Config:
        from_attributes = True


class PaymentBase(BaseModel):
    """Base schema for payment."""
    user_id: int
    payment_method_id: int
    amount: Decimal = Field(..., decimal_places=2)
    status: str = Field(default="pending", description="pending, completed, failed, refunded")


class PaymentCreate(PaymentBase):
    """Schema for creating a payment."""
    ticket_ids: List[int] = Field(default_factory=list, description="Associated ticket IDs")


class Payment(BaseModel):
    """Schema for payment response."""
    payment_id: int
    user_id: int
    payment_method_id: int
    amount: Decimal
    status: str
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class RefundCreate(BaseModel):
    """Schema for creating a refund."""
    ticket_id: int
    policy_id: int = Field(..., description="Cancellation policy ID")


class Refund(BaseModel):
    """Schema for refund response."""
    refund_id: int
    ticket_id: int
    payment_id: int
    policy_id: int
    refund_amount: Decimal
    created_at: Optional[datetime] = None
