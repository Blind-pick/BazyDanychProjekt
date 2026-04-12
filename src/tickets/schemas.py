"""Tickets domain schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class TicketBase(BaseModel):
    """Base schema for ticket."""
    showtime_id: int
    seat_id: int
    user_id: int
    final_price: Decimal = Field(..., decimal_places=2)
    status: str = Field(default="valid", description="valid, cancelled, used")


class TicketCreate(TicketBase):
    """Schema for creating a ticket."""
    reservation_id: Optional[int] = None


class Ticket(BaseModel):
    """Schema for ticket response."""
    ticket_id: int
    showtime_id: int
    seat_id: int
    user_id: int
    final_price: Decimal
    status: str
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ShowtimeSeatAvailability(BaseModel):
    """Schema for seat availability at a showtime."""
    seat_id: int
    row_label: str
    seat_number: int
    seat_type: str
    is_available: bool
    base_price: Optional[Decimal] = None
