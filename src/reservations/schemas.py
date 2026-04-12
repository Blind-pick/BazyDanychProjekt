"""Reservations domain schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ReservationBase(BaseModel):
    """Base schema for reservation."""
    user_id: int
    showtime_id: int
    seat_ids: List[int] = Field(..., min_items=1, description="List of seat IDs to reserve")


class ReservationCreate(ReservationBase):
    """Schema for creating a reservation."""
    pass


class ReservationStatusUpdate(BaseModel):
    """Schema for updating reservation status."""
    status: str = Field(..., description="New status: pending, confirmed, cancelled")


class Reservation(BaseModel):
    """Schema for reservation response."""
    reservation_id: int
    user_id: int
    showtime_id: int
    status: str
    seat_ids: List[int] = []
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
